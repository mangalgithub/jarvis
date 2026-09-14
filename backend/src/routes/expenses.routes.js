const express = require("express");
const { postSmsExpense, getSmsExpensesController } = require("../controllers/expenses.controller");

const router = express.Router();

router.post("/sms", postSmsExpense);
router.get("/sms", getSmsExpensesController);

module.exports = router;
