const { sendMessageToAgent } = require("../services/agent.service");

async function handleChat(req, res, next) {
  try {
    const { message, image, userId = "default-user" } = req.body;

    if (!message) {
      return res.status(400).json({ error: "message is required" });
    }

    const authHeader = req.headers.authorization;
    const response = await sendMessageToAgent({ message, image, userId, authHeader });
    return res.json(response);
  } catch (error) {
    return next(error);
  }
}

module.exports = { handleChat };
