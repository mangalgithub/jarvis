const AGENT_SERVICE_URL = process.env.AGENT_SERVICE_URL || "http://localhost:8000";

async function sendMessageToAgent({ message, userId }) {
  const response = await fetch(`${AGENT_SERVICE_URL}/agent/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message, user_id: userId }),
  });

  if (!response.ok) {
    throw new Error(`Agent service failed with status ${response.status}`);
  }

  return response.json();
}

module.exports = { sendMessageToAgent };
