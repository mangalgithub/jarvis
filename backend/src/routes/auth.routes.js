const express = require('express');

const router = express.Router();
const AGENT_SERVICE_URL = process.env.AGENT_SERVICE_URL || "http://localhost:8000";

router.post('/register', async (req, res, next) => {
  try {
    const response = await fetch(`${AGENT_SERVICE_URL}/agent/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body)
    });
    
    const data = await response.json();
    if (!response.ok) {
      return res.status(response.status).json(data);
    }
    res.json(data);
  } catch (error) {
    next(error);
  }
});

router.post('/login', async (req, res, next) => {
  try {
    const response = await fetch(`${AGENT_SERVICE_URL}/agent/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body)
    });
    
    const data = await response.json();
    if (!response.ok) {
      return res.status(response.status).json(data);
    }
    res.json(data);
  } catch (error) {
    next(error);
  }
});

module.exports = router;
