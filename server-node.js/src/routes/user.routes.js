import express from "express";
import {
  listUsers,
  getUser,
  editUser,
  addUser,
  deleteUser,
} from "../controllers/user.controllers.js";

const router = express.Router();
router.get("/", listUsers);
router.get("/:id", getUser);
router.put("/:id", editUser);
router.post("/", addUser);
router.delete("/:id", deleteUser);

export default router;
