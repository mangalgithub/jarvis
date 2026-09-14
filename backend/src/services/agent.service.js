const AGENT_SERVICE_URL = process.env.AGENT_SERVICE_URL || "http://localhost:8000";

async function sendMessageToAgent({ message, image, userId, authHeader }) {
  const headers = { "Content-Type": "application/json" };
  if (authHeader) headers["Authorization"] = authHeader;

  const response = await fetch(`${AGENT_SERVICE_URL}/agent/chat`, {
    method: "POST",
    headers,
    body: JSON.stringify({ message, image, user_id: userId }),
  });

  if (!response.ok) {
    const err = new Error(`Agent service failed with status ${response.status}`);
    err.status = response.status;
    throw err;
  }

  return response.json();
}

async function getDashboardFromAgent({ userId, dateRange, category, authHeader }) {
  const searchParams = new URLSearchParams();
  searchParams.set("user_id", userId || "default-user");

  if (dateRange) {
    searchParams.set("date_range", dateRange);
  }

  if (category && category !== "All") {
    searchParams.set("category", category);
  }

  const headers = {};
  if (authHeader) headers["Authorization"] = authHeader;

  const response = await fetch(`${AGENT_SERVICE_URL}/agent/dashboard?${searchParams}`, {
    headers
  });

  if (!response.ok) {
    const err = new Error(`Agent dashboard failed with status ${response.status}`);
    err.status = response.status;
    throw err;
  }

  return response.json();
}

async function ingestSmsExpense({ smsBody, sender, receivedAt, authHeader }) {
  const headers = { "Content-Type": "application/json" };
  if (authHeader) headers["Authorization"] = authHeader;

  const response = await fetch(`${AGENT_SERVICE_URL}/agent/expenses/sms`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      sms_body: smsBody,
      sender: sender || "",
      received_at: receivedAt || null,
    }),
  });

  if (!response.ok) {
    const err = new Error(`Agent SMS ingestion failed with status ${response.status}`);
    err.status = response.status;
    throw err;
  }

  return response.json();
}

async function getSmsExpenses({ limit, authHeader }) {
  const headers = {};
  if (authHeader) headers["Authorization"] = authHeader;

  const response = await fetch(`${AGENT_SERVICE_URL}/agent/expenses/sms?limit=${limit || 30}`, {
    headers,
  });

  if (!response.ok) {
    const err = new Error(`Agent get SMS expenses failed with status ${response.status}`);
    err.status = response.status;
    throw err;
  }

  return response.json();
}

async function getBriefingFromAgent({ userId, authHeader, forceRefresh = false }) {
  const headers = {};
  if (authHeader) headers["Authorization"] = authHeader;

  const url = `${AGENT_SERVICE_URL}/agent/briefing${forceRefresh ? "?force_refresh=true" : ""}`;
  const response = await fetch(url, {
    headers,
  });

  if (!response.ok) {
    const err = new Error(`Agent briefing failed with status ${response.status}`);
    err.status = response.status;
    throw err;
  }

  return response.json();
}

async function deduplicateExpensesInAgent({ authHeader }) {
  const headers = {};
  if (authHeader) headers["Authorization"] = authHeader;

  const response = await fetch(`${AGENT_SERVICE_URL}/agent/expenses/deduplicate`, {
    method: "POST",
    headers,
  });

  if (!response.ok) {
    const err = new Error(`Agent deduplication failed with status ${response.status}`);
    err.status = response.status;
    throw err;
  }

  return response.json();
}

module.exports = {
  sendMessageToAgent,
  getDashboardFromAgent,
  ingestSmsExpense,
  getSmsExpenses,
  getBriefingFromAgent,
  deduplicateExpensesInAgent,
};

