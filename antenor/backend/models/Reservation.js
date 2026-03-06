import mongoose from "mongoose";

const ReservationSchema = new mongoose.Schema(
  {
    clientName: { type: String, required: true },
    date: { type: Date, required: true },
    time: { type: String, required: true },
    guests: { type: Number, required: true },
    user: { type: mongoose.Schema.Types.ObjectId, ref: "User" },
  },
  { timestamps: true }
);

export default mongoose.model("Reservation", ReservationSchema);
