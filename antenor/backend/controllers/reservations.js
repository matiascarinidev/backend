import Reservation from "../models/Reservation.js";

export const createReservation = async (req, res) => {
  const { clientName, date, time, guests } = req.body;
  const reservation = new Reservation({
    clientName,
    date,
    time,
    guests,
    user: req.user._id,
  });
  await reservation.save();
  res.status(201).json(reservation);
};

export const getReservations = async (req, res) => {
  const reservations = await Reservation.find().populate("user", "email role");
  res.json(reservations);
};

export const updateReservation = async (req, res) => {
  const updated = await Reservation.findByIdAndUpdate(req.params.id, req.body, {
    new: true,
  });
  res.json(updated);
};

export const deleteReservation = async (req, res) => {
  await Reservation.findByIdAndDelete(req.params.id);
  res.status(204).send();
};
