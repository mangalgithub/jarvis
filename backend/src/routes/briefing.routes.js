const express = require("express");
const { getBriefing } = require("../controllers/briefing.controller");

const router = express.Router();

router.get("/", getBriefing);

module.exports = router;
