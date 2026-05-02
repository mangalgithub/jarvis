const express = require("express");

const chatRoutes = require("./routes/chat.routes");
const dashboardRoutes = require("./routes/dashboard.routes");
const authRoutes = require("./routes/auth.routes");
const { errorMiddleware } = require("./middleware/error.middleware");

const app = express();

app.use((req, res, next) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET,POST,PUT,PATCH,DELETE,OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type,Authorization,X-Requested-With");
  res.setHeader("Access-Control-Allow-Credentials", "true");

  if (req.method === "OPTIONS") {
    return res.status(200).end();
  }
  next();
});

app.use(express.json({ limit: "10mb" }));
app.use(express.urlencoded({ limit: "10mb", extended: true }));

app.get("/", (req, res) => {
  res.json({ message: "Jarvis backend is running" });
});

app.get("/health", (req, res) => {
  res.json({ status: "ok", service: "jarvis-backend" });
});

app.use(["/api/chat", "/chat"], chatRoutes);
app.use(["/api/dashboard", "/dashboard"], dashboardRoutes);
app.use(["/api/auth", "/auth"], authRoutes);

app.use(errorMiddleware);

module.exports = app;
