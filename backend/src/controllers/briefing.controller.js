const { getBriefingFromAgent } = require("../services/agent.service");

async function getBriefing(req, res, next) {
  try {
    const { userId = "default-user", forceRefresh } = req.query;
    const authHeader = req.headers.authorization;
    const briefing = await getBriefingFromAgent({
      userId,
      authHeader,
      forceRefresh: forceRefresh === "true" || forceRefresh === true,
    });
    return res.json(briefing);
  } catch (error) {
    return next(error);
  }
}

module.exports = { getBriefing };
