const { getDashboardFromAgent } = require("../services/agent.service");

async function getDashboard(req, res) {
  const { userId = "default-user", dateRange, category } = req.query;
  const dashboard = await getDashboardFromAgent({ userId, dateRange, category });
  res.json(dashboard);
}

module.exports = { getDashboard };
