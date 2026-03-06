import express from "express";
import jwt from "jsonwebtoken";
import User from "../models/User.js";
import bcrypt from "bcryptjs";

const router = express.Router();

router.post("/register", async (req, res) => {
  const { email, password, role } = req.body;
  const user = new User({ email, password, role });
  await user.save();
  res.status(201).send("User registered");
});

router.post("/login", async (req, res) => {
  const { email, password } = req.body;
  const user = await User.findOne({ email });
  if (!user || !(await bcrypt.compare(password, user.password))) {
    return res.status(400).send("Invalid credentials");
  }

  const token = jwt.sign(
    { _id: user._id, role: user.role },
    process.env.JWT_SECRET
  );
  res.json({ token });
});

export default router;
