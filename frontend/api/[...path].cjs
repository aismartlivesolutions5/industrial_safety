const BACKEND = process.env.BACKEND_URL || "https://industrial-safety-1-ieju.onrender.com";

module.exports = async function handler(req, res) {
  const segments = Array.isArray(req.query.path) ? req.query.path : [req.query.path];
  const apiPath = segments.join("/");

  const { path: _p, ...rest } = req.query;
  const qs = new URLSearchParams(
    Object.entries(rest).map(([k, v]) => [k, String(v)])
  ).toString();

  const url = `${BACKEND}/${apiPath}${qs ? "?" + qs : ""}`;

  try {
    const isWrite = ["POST", "PUT", "PATCH"].includes(req.method || "");
    const response = await fetch(url, {
      method: req.method || "GET",
      headers: isWrite ? { "Content-Type": "application/json" } : {},
      body: isWrite ? JSON.stringify(req.body) : undefined,
    });

    const data = await response.json();
    res.status(response.status).json(data);
  } catch (err) {
    res.status(504).json({ error: "Gateway timeout", detail: String(err) });
  }
};
