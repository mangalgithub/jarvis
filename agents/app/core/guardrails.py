"""
Jarvis Guardrails — multi-layer security for input/output pipeline.

Layers:
  1. sanitize_input()        — strip dangerous chars, truncate
  2. detect_prompt_injection() — catch jailbreak / instruction-override attempts
  3. validate_image_input()  — ensure base64 payload is a real image
  4. filter_output()         — redact leakage and oversized replies
"""

import base64
import logging
import re

import httpx

from app.core.config import settings

_log = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

MAX_MESSAGE_LENGTH = 2000
MAX_REPLY_LENGTH = 8000

# ── Layer 1: Input Sanitization ───────────────────────────────────────────────

# Control characters except newline (\n=10) and tab (\t=9)
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")

def sanitize_input(message: str) -> str:
    """
    Clean raw user input before it reaches intent detection or any LLM call.
    - Remove null bytes and non-printable control characters
    - Collapse excessive whitespace / blank lines
    - Hard-truncate to MAX_MESSAGE_LENGTH
    """
    # Strip null bytes and control characters
    message = _CONTROL_CHAR_RE.sub("", message)
    # Collapse 3+ consecutive newlines → 2
    message = re.sub(r"\n{3,}", "\n\n", message)
    # Collapse runs of spaces/tabs
    message = re.sub(r"[ \t]{2,}", " ", message)
    message = message.strip()
    if len(message) > MAX_MESSAGE_LENGTH:
        _log.warning("Input truncated from %d to %d chars", len(message), MAX_MESSAGE_LENGTH)
        message = message[:MAX_MESSAGE_LENGTH]
    return message


# ── Layer 2: Prompt Injection Detection ──────────────────────────────────────

_INJECTION_PATTERNS: list[re.Pattern] = [
    # Classic override phrases
    re.compile(
        r"ignore\s+(all\s+)?(previous|prior|above|your)\s+(instructions?|prompt|rules?|guidelines?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"disregard\s+(all\s+)?(previous|prior|above|your)\s+(instructions?|prompt|rules?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"forget\s+(everything|all)\s+(you\s+were\s+told|above|before|your\s+instructions?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"forget\s+(all\s+)?(the\s+)?(previous|prior|above|old|your|earlier)\s+(instructions?|rules?|prompt|guidelines?|context)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(override|overwrite|replace|reset|clear|erase|delete)\s+(all\s+)?(previous|prior|your|the)?\s*(instructions?|rules?|prompt|guidelines?|constraints?|system)",
        re.IGNORECASE,
    ),
    re.compile(
        r"from\s+now\s+on\s+(you\s+(will|must|should|are\s+to)|ignore|forget|disregard)",
        re.IGNORECASE,
    ),
    re.compile(r"new\s+instructions?\s*[:=\-]", re.IGNORECASE),
    # Persona hijacking
    re.compile(
        r"\b(you\s+are\s+now|pretend\s+(you\s+are|to\s+be)|act\s+as|roleplay\s+as|imagine\s+you\s+are)\s+"
        r"(DAN|evil|unrestricted|jailbroken|unfiltered|without\s+restrictions?|a\s+different\s+(ai|bot|assistant))",
        re.IGNORECASE,
    ),
    re.compile(r"\bDAN\s+mode\b", re.IGNORECASE),
    re.compile(r"\bjailbreak\b", re.IGNORECASE),
    # System prompt exfiltration
    re.compile(
        r"(repeat|print|output|reveal|show|tell\s+me|what\s+is)\s+.{0,30}"
        r"(system\s+prompt|instructions?|your\s+prompt|what\s+you\s+were\s+told)",
        re.IGNORECASE,
    ),
    # Token / special marker injection
    re.compile(r"<\|im_start\|>|<\|endoftext\|>|<\|im_end\|>", re.IGNORECASE),
    re.compile(r"\[SYSTEM\]|\[INST\]|\[\/INST\]", re.IGNORECASE),
    # New-session trickery
    re.compile(
        r"new\s+(session|conversation|context|persona|mode)\s*[:=\-]",
        re.IGNORECASE,
    ),
    # Override via code-block tricks
    re.compile(r"```\s*system", re.IGNORECASE),
    # Identity probing trickery
    re.compile(
        r"(who\s+are\s+you\s+really|who\s+actually\s+made\s+you|are\s+you\s+(really\s+)?jarvis)",
        re.IGNORECASE,
    ),
    # Credential / API key / secret exfiltration attempts
    re.compile(
        r"(send|give|share|show|reveal|display|print|output|return|tell\s+me|what\s+is|provide)\s+.{0,50}"
        r"(api[\s_-]*key|secret[\s_-]*key|auth[\s_-]*token|access[\s_-]*token|password|credential|private[\s_-]*key)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(api[\s_-]*key|secret[\s_-]*key|auth[\s_-]*token)\b.{0,40}(used|stored|set|configured|is\b|=)",
        re.IGNORECASE,
    ),
]

_SAFE_REFUSAL = (
    "I'm not able to process that request. "
    "If you need help with finance, health, news, or stocks — just ask!"
)


def guardrail_regex_check(message: str) -> bool:
    """
    Stage 1 — fast regex pre-filter (synchronous, zero-latency).
    Return True if the message is an obvious injection/jailbreak attempt.
    """
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(message):
            _log.warning(
                "[Guardrail:Regex] Injection detected: pattern=%s msg_preview=%r",
                pattern.pattern[:40],
                message[:80],
            )
            return True
    return False


# Backward-compat alias (old orchestrator import still works)
def detect_prompt_injection(message: str) -> bool:
    return guardrail_regex_check(message)


async def classify_with_prompt_guard(message: str) -> tuple[bool, str]:
    """
    Stage 2 — Llama Prompt Guard 2 on Groq (cloud, no hardware required).

    Llama Prompt Guard 2 is a purpose-built 86M BERT-based classifier trained
    specifically to detect prompt injection and jailbreak attempts.  It returns
    a single token: 'BENIGN' or 'INJECTION'.

    Returns:
        (is_safe: bool, verdict: str)
        is_safe=False means the request should be blocked.
        On any network/parse error the function returns (False, 'guardrail_error')
        so that failures are always fail-safe.
    """
    if not settings.groq_api_key:
        _log.error("[Guardrail:PromptGuard] GROQ_API_KEY not set — blocking (fail-safe)")
        return False, "no_api_key"

    payload = {
        "model": settings.guardrail_model,
        "messages": [{"role": "user", "content": message}],
        "max_tokens": 10,
        "temperature": 0,
    }
    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.post(
                settings.groq_api_url,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
        verdict_str = response.json()["choices"][0]["message"]["content"].strip()
        
        try:
            injection_probability = float(verdict_str)
            # A threshold of 0.5 is standard. >0.5 means likely an injection.
            is_safe = injection_probability < 0.5
        except ValueError:
            # Fallback if the model behaves unexpectedly and returns text
            is_safe = "BENIGN" in verdict_str.upper() or "SAFE" in verdict_str.upper()
            
        _log.info(
            "[Guardrail:PromptGuard] score=%s is_safe=%s msg_preview=%r",
            verdict_str,
            is_safe,
            message[:80],
        )
        if not is_safe:
            _log.warning(
                "[Guardrail:PromptGuard] INJECTION detected msg_preview=%r",
                message[:80],
            )
        return is_safe, verdict_str

    except httpx.TimeoutException:
        _log.error("[Guardrail:PromptGuard] Timeout — blocking (fail-safe)")
        return False, "guardrail_timeout"
    except Exception as exc:  # noqa: BLE001
        _log.error("[Guardrail:PromptGuard] Unexpected error %s — blocking (fail-safe)", exc)
        return False, "guardrail_error"


async def run_guardrails(message: str) -> tuple[bool, str]:
    """
    Single async entry point for the full guardrail pipeline.

    Stage 1 — Regex pre-filter  (0 ms, catches obvious patterns)
    Stage 2 — Llama Prompt Guard 2 on Groq  (~70 ms, catches nuanced attacks)

    Returns:
        (is_safe: bool, block_reason: str)
        Call this instead of detect_prompt_injection().
    """
    # Stage 1: fast synchronous regex check
    if guardrail_regex_check(message):
        return False, "regex"

    # Stage 2: cloud LLM classifier (uses existing Groq key, no hardware needed)
    return await classify_with_prompt_guard(message)


def get_safe_refusal() -> str:
    return _SAFE_REFUSAL


# ── Layer 3: Image Validation ─────────────────────────────────────────────────

# JPEG: FF D8 FF  |  PNG: 89 50 4E 47  |  WEBP: RIFF....WEBP  |  GIF: GIF8
_VALID_IMAGE_SIGNATURES = [
    b"\xff\xd8\xff",          # JPEG
    b"\x89PNG",               # PNG
    b"RIFF",                  # WEBP (starts with RIFF)
    b"GIF8",                  # GIF
]
_MAX_IMAGE_B64_LEN = 10 * 1024 * 1024  # ~7.5 MB decoded → reject base64 > 10MB


def validate_image_input(b64_string: str) -> bool:
    """
    Return True if *b64_string* decodes to a supported image format.
    Rejects non-image binary data sent to the vision endpoint.
    """
    if not b64_string:
        return False
    if len(b64_string) > _MAX_IMAGE_B64_LEN:
        _log.warning("Image rejected: base64 length %d exceeds limit", len(b64_string))
        return False
    # Strip data-URL prefix if present: "data:image/jpeg;base64,..."
    if "," in b64_string[:64]:
        b64_string = b64_string.split(",", 1)[1]
    try:
        raw = base64.b64decode(b64_string[:64], validate=False)
    except Exception:
        _log.warning("Image rejected: invalid base64")
        return False

    for sig in _VALID_IMAGE_SIGNATURES:
        if raw[: len(sig)] == sig:
            return True

    _log.warning("Image rejected: unrecognised file signature %r", raw[:8])
    return False


# ── Layer 4: Output Filtering ─────────────────────────────────────────────────

# Patterns that suggest the LLM leaked internal config
_LEAKAGE_PATTERNS: list[re.Pattern] = [
    re.compile(r"You are Jarvis[,\.].{0,60}personal\s+AI", re.IGNORECASE),
    re.compile(r"IMPORTANT:\s*You must NEVER reveal", re.IGNORECASE),
    re.compile(r"\bGroq API key\b", re.IGNORECASE),
    re.compile(r"\bMONGO(?:DB)?_URI\b", re.IGNORECASE),
    re.compile(r"\bREDIS_URL\b", re.IGNORECASE),
]

# Looks like a secret token / API key
_SECRET_RE = re.compile(
    r"\b(sk-[A-Za-z0-9]{20,}|gsk_[A-Za-z0-9]{20,}|Bearer\s+[A-Za-z0-9\-._~+/]{20,})\b"
)

_GENERIC_ERROR = "I encountered an issue generating a response. Please try again."

# ── Layer 5: Rate Limiting ────────────────────────────────────────────────────

import time
from app.core.redis import get_redis

_RATE_LIMIT_MEM: dict[str, list[float]] = {}

async def check_rate_limit(path: str, identity: str, limit: int, window: int = 60) -> bool:
    """
    Returns True if allowed, False if rate-limited.
    Uses Redis if available, falls back to in-memory window.
    """
    key = f"rate_limit:{path}:{identity}"
    redis = await get_redis()
    
    if redis:
        current = await redis.get(key)
        if current and int(current) >= limit:
            return False
        pipe = redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, window)
        await pipe.execute()
        return True
    else:
        now = time.time()
        if key not in _RATE_LIMIT_MEM:
            _RATE_LIMIT_MEM[key] = []
        # Filter old
        _RATE_LIMIT_MEM[key] = [t for t in _RATE_LIMIT_MEM[key] if now - t < window]
        if len(_RATE_LIMIT_MEM[key]) >= limit:
            return False
        _RATE_LIMIT_MEM[key].append(now)
        return True

def filter_output(reply: str) -> str:
    """
    Scan and clean the LLM reply before returning it to the client.
    - Redact obvious secret/token patterns
    - Replace replies that contain system-prompt leakage with a generic error
    - Truncate runaway replies
    """
    # Check for system-prompt leakage
    for pattern in _LEAKAGE_PATTERNS:
        if pattern.search(reply):
            _log.error("Output filter: system-prompt leakage detected, replacing reply")
            return _GENERIC_ERROR

    # Redact secrets
    redacted, count = _SECRET_RE.subn("[REDACTED]", reply)
    if count:
        _log.warning("Output filter: redacted %d secret-like token(s)", count)
        reply = redacted

    # Truncate oversized replies
    if len(reply) > MAX_REPLY_LENGTH:
        _log.warning("Output truncated from %d to %d chars", len(reply), MAX_REPLY_LENGTH)
        reply = reply[:MAX_REPLY_LENGTH] + "\n\n*(response truncated)*"

    return reply
