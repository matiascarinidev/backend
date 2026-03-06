import jwt from "jsonwebtoken";

export const authenticate =
  (roles = []) =>
  (req, res, next) => {
    const token = req.header("Authorization")?.replace("Bearer ", "");

    if (!token) return res.status(401).send("Access Denied");

    try {
      const verified = jwt.verify(token, process.env.JWT_SECRET);
      req.user = verified;

      if (roles.length && !roles.includes(verified.role)) {
        return res.status(403).send("Forbidden");
      }

      next();
    } catch (err) {
      console.error("Authentication error:", err.message); // Log the error for debugging
      res.status(400).json({ error: "Invalid Token", details: err.message }); // Provide a descriptive response
    }
  };
