"""
SMS Parser for Indian payment messages.

Supports: Google Pay (GPay), PhonePe, Paytm, Bank of India,
          HDFC, SBI, ICICI, Axis, Kotak credit/debit cards,
          and generic UPI/bank debit SMS formats.
"""

import re
from datetime import datetime, timezone
from typing import Optional


# ─── Known bank/payment sender IDs ───────────────────────────────────────────
KNOWN_PAYMENT_SENDERS = {
    # Google Pay
    "AD-GPAY", "BW-GPAY", "VM-GPAY", "VD-GPAY", "JD-GPAY",
    # PhonePe
    "AD-PHONEPE", "VM-PHONEPE", "BW-PHONEPE", "VD-PPAY",
    # Paytm
    "AD-PAYTM", "VM-PAYTM", "VD-PAYTM", "BW-PAYTM",
    # Bank of India
    "AD-BOIINB", "VM-BOIINB", "BW-BOIINB", "VD-BOIINB", "JD-BOIINB",
    # HDFC
    "AD-HDFCBK", "VM-HDFCBK", "BW-HDFCBK",
    # SBI
    "AD-SBIINB", "VM-SBIINB", "BW-SBIINB",
    # ICICI
    "AD-ICICIB", "VM-ICICIB",
    # Axis
    "AD-AXISBK", "VM-AXISBK",
    # Kotak
    "AD-KOTAKB", "VM-KOTAKB",
    # Generic UPI
    "AD-UPIBNK", "VM-UPIBNK",
    # Amazon Pay
    "AD-AMAZON", "VM-AMAZON",
}


def is_payment_sms(sender: str, body: str) -> bool:
    """Return True if the SMS looks like a payment/debit notification."""
    sender_upper = (sender or "").upper().strip()
    if sender_upper in KNOWN_PAYMENT_SENDERS:
        return True

    # Keyword heuristic for unknown sender IDs
    keywords = [
        "debited", "debit", "paid", "payment", "spent", "purchase",
        "transaction", "upi", "neft", "imps", "credited",
    ]
    body_lower = body.lower()
    return any(kw in body_lower for kw in keywords)


# ─── Amount extraction patterns ───────────────────────────────────────────────
_AMOUNT_PATTERNS = [
    # Rs.1,200.00  Rs 500  INR 3500  ₹1200
    r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)",
    # 1200 INR  1200.00 INR
    r"([\d,]+(?:\.\d{1,2})?)\s*(?:INR|Rs\.?|₹)",
]


def _extract_amount(text: str) -> Optional[float]:
    for pattern in _AMOUNT_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            raw = match.group(1).replace(",", "")
            try:
                return float(raw)
            except ValueError:
                continue
    return None


# ─── Merchant extraction patterns ─────────────────────────────────────────────
_MERCHANT_PATTERNS = [
    # "paid to <merchant>" / "payment to <merchant>"
    r"(?:paid|payment)\s+to\s+([A-Za-z0-9 &\-'_.]+?)(?:\s+via|\s+Ref|\s*\.|\s*,|$)",
    # "at <merchant>" — common in credit card SMS
    r"\bat\s+([A-Z][A-Za-z0-9 &\-'_.]{2,30})(?:\s+on|\s*\.|\s*,|$)",
    # "to <merchant> via GPay/PhonePe"
    r"\bto\s+([A-Za-z0-9 &\-'_.]{3,30})\s+via\s+(?:GPay|Google Pay|PhonePe|Paytm|UPI)",
    # "Merchant: <name>"
    r"Merchant:\s*([A-Za-z0-9 &\-'_.]+?)(?:\s*\.|\s*,|$)",
    # "UPI: Rs 250 paid to Swiggy"
    r"UPI.*?paid to\s+([A-Za-z0-9 &\-'_.]+?)(?:\s*\.|\s*,|Ref|$)",
    # "debited for ... at <merchant>"
    r"debited.*?at\s+([A-Z][A-Za-z0-9 &\-'_.]{2,30})(?:\s+on|\s*\.|\s*,|$)",
]


def _extract_merchant(text: str) -> Optional[str]:
    for pattern in _MERCHANT_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            merchant = match.group(1).strip().rstrip(".,")
            if len(merchant) >= 2:
                return merchant.title()
    return None


# ─── Payment method detection ─────────────────────────────────────────────────
def _detect_payment_method(body: str, sender: str) -> str:
    body_lower = body.lower()
    sender_upper = (sender or "").upper()

    if any(x in body_lower for x in ["gpay", "google pay"]) or "GPAY" in sender_upper:
        return "GPay"
    if "phonepe" in body_lower or "PHONEPE" in sender_upper:
        return "PhonePe"
    if "paytm" in body_lower or "PAYTM" in sender_upper:
        return "Paytm"
    if "credit card" in body_lower or "cc " in body_lower:
        return "Credit Card"
    if "debit card" in body_lower or "dc " in body_lower:
        return "Debit Card"
    if any(x in body_lower for x in ["upi", "neft", "imps", "rtgs"]):
        return "UPI"
    return "Bank Transfer"


# ─── Reference ID extraction ──────────────────────────────────────────────────
def _extract_reference(text: str) -> Optional[str]:
    patterns = [
        r"Ref(?:erence)?(?:\s*No\.?|:)?\s*([A-Z0-9]{6,20})",
        r"Ref\.?\s*#\s*([A-Z0-9]{6,20})",
        r"TxnId[:\s]+([A-Z0-9]{8,20})",
        r"UPI Ref[:\s]+([0-9]{10,15})",
        r"Transaction ID[:\s]+([A-Z0-9]{8,20})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


# ─── Account last-4 extraction ────────────────────────────────────────────────
def _extract_account_last4(text: str) -> Optional[str]:
    patterns = [
        r"A/c\s+(?:XX+|x+)?(\d{4})",
        r"account\s+ending\s+(\d{4})",
        r"card\s+ending\s+(\d{4})",
        r"a/c\s+(\d{4})\b",
        r"XX(\d{4})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


# ─── Transaction type detection ───────────────────────────────────────────────
def _detect_transaction_type(body: str) -> str:
    body_lower = body.lower()
    if any(x in body_lower for x in ["debited", "debit", "paid", "payment", "spent", "purchase"]):
        return "debit"
    if any(x in body_lower for x in ["credited", "credit", "received", "refund"]):
        return "credit"
    return "debit"  # default assumption for payment SMS


# ─── Bank name detection ──────────────────────────────────────────────────────
def _detect_bank(body: str, sender: str) -> str:
    bank_map = {
        "GPAY": "Google Pay",
        "GOOGLE PAY": "Google Pay",
        "PHONEPE": "PhonePe",
        "PAYTM": "Paytm",
        "BOIINB": "Bank of India",
        "BANK OF INDIA": "Bank of India",
        "HDFCBK": "HDFC Bank",
        "HDFC": "HDFC Bank",
        "SBIINB": "State Bank of India",
        "SBI": "State Bank of India",
        "ICICIB": "ICICI Bank",
        "ICICI": "ICICI Bank",
        "AXISBK": "Axis Bank",
        "AXIS": "Axis Bank",
        "KOTAKB": "Kotak Bank",
        "KOTAK": "Kotak Bank",
        "AMAZON": "Amazon Pay",
    }
    combined = (body + " " + (sender or "")).upper()
    for key, name in bank_map.items():
        if key in combined:
            return name
    return "Bank"


# ─── Main parse function ──────────────────────────────────────────────────────

def parse_payment_sms(
    body: str,
    sender: str = "",
    received_at: Optional[datetime] = None,
) -> Optional[dict]:
    """
    Parse a payment SMS and return a structured expense dict, or None
    if the SMS is not recognized as a payment message.

    Returns:
        {
            "amount": float,
            "merchant": str | None,
            "bank": str,
            "account_last4": str | None,
            "transaction_type": "debit" | "credit",
            "payment_method": str,
            "reference_id": str | None,
            "timestamp": str (ISO 8601),
            "raw_sms": str,
        }
    """
    if not body:
        return None

    if not is_payment_sms(sender, body):
        return None

    amount = _extract_amount(body)
    if amount is None or amount <= 0:
        return None

    tx_type = _detect_transaction_type(body)
    # Only track debits (outgoing payments) for expense tracking
    # Credits can still be returned so callers can choose to filter
    merchant = _extract_merchant(body)
    bank = _detect_bank(body, sender)
    payment_method = _detect_payment_method(body, sender)
    reference_id = _extract_reference(body)
    account_last4 = _extract_account_last4(body)
    timestamp = received_at or datetime.now(timezone.utc)

    return {
        "amount": amount,
        "merchant": merchant,
        "bank": bank,
        "account_last4": account_last4,
        "transaction_type": tx_type,
        "payment_method": payment_method,
        "reference_id": reference_id,
        "timestamp": timestamp.isoformat(),
        "raw_sms": body,
    }


# ─── Test helper (run directly to verify patterns) ────────────────────────────
if __name__ == "__main__":
    samples = [
        ("AD-GPAY", "Rs.500.00 paid to Zomato via Google Pay. Ref: 403812098312"),
        ("VM-PHONEPE", "INR 1200.00 paid via PhonePe to Amazon India. UPI Ref 2839012938"),
        ("VD-PAYTM", "You have paid Rs 250 to Swiggy via Paytm. Txn ID PT12345678"),
        ("AD-BOIINB", "Your A/c XX1234 debited by Rs.3500 on 10/09. Bal Rs 12000"),
        ("BW-HDFCBK", "HDFC Bank: Rs.2000.00 used on Credit Card ending 4567 at FLIPKART on 10-09-2026"),
        ("VM-SBIINB", "Dear Customer, Rs 800.00 debited from A/c XXXXXX9012 at BOOKMYSHOW. Avl Bal: Rs.5000"),
        ("AD-AXISBK", "Axis Bank: INR 450 debited from account ending 3344. Merchant: Uber India"),
        ("BW-GPAY", "Rs 100 paid to Rahul Sharma via Google Pay"),
    ]

    for sender, body in samples:
        result = parse_payment_sms(body, sender)
        if result:
            print(f"✅ {sender}: ₹{result['amount']} | {result['merchant']} | {result['bank']} | {result['transaction_type']}")
        else:
            print(f"❌ {sender}: NOT RECOGNIZED")
