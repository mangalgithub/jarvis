const { ingestSmsExpense, getSmsExpenses } = require("../services/agent.service");

async function postSmsExpense(req, res, next) {
  try {
    const { sms_body, sender, received_at } = req.body;
    const authHeader = req.headers.authorization;

    if (!sms_body) {
      return res.status(400).json({ error: "sms_body is required" });
    }

    const result = await ingestSmsExpense({
      smsBody: sms_body,
      sender,
      receivedAt: received_at,
      authHeader,
    });

    return res.json(result);
  } catch (error) {
    return next(error);
  }
}

async function getSmsExpensesController(req, res, next) {
  try {
    const { limit } = req.query;
    const authHeader = req.headers.authorization;

    const result = await getSmsExpenses({
      limit: limit ? parseInt(limit, 10) : 30,
      authHeader,
    });

    return res.json(result);
  } catch (error) {
    return next(error);
  }
}

module.exports = {
  postSmsExpense,
  getSmsExpensesController,
};
