import express from "express";
import { authenticate } from "../middlewares/auth.js";
import {
  createReservation,
  getReservations,
  updateReservation,
  deleteReservation,
} from "../controllers/reservations.js";

const router = express.Router();

// Todos los usuarios autenticados pueden crear
router.post("/", authenticate(["client", "manager"]), createReservation);

// Solo manager puede ver/editar/eliminar
router.get("/", authenticate(["manager"]), getReservations);
router.put("/:id", authenticate(["manager"]), updateReservation);
router.delete("/:id", authenticate(["manager"]), deleteReservation);

export default router;
