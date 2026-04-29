const { getDashboardFromAgent } = require("../services/agent.service");

async function getDashboard(req, res) {
  const { userId = "default-user" } = req.query;
  const dashboard = await getDashboardFromAgent({ userId });
  res.json(dashboard);
}

module.exports = { getDashboard };
