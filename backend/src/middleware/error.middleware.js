function errorMiddleware(error, req, res, next) {
  console.error(error.message || error);
  res.status(error.status || 500).json({ error: error.message || "Something went wrong" });
}

module.exports = { errorMiddleware };
