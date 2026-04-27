import { apiRequest } from "./api";

export function sendChatMessage(message) {
  return apiRequest("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}
