const express = require("express");
const { 
  postSmsExpense, 
  getSmsExpensesController,
  deduplicateExpensesController,
} = require("../controllers/expenses.controller");

const router = express.Router();

router.post("/sms", postSmsExpense);
router.get("/sms", getSmsExpensesController);
router.post("/deduplicate", deduplicateExpensesController);

module.exports = router;

