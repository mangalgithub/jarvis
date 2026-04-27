async function getDashboard(req, res) {
  res.json({
    news: null,
    finance: null,
    health: null,
    stocks: null,
    learning: null,
    reminders: [],
  });
}

module.exports = { getDashboard };
