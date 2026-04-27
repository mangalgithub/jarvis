function errorMiddleware(error, req, res, next) {
  console.error(error);
  res.status(500).json({ error: "Something went wrong" });
}

module.exports = { errorMiddleware };
