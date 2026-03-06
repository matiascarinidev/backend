import mongoose from "mongoose";
import dotenv from "dotenv";
dotenv.config();

const connectDB = async () => {
  try {
    await mongoose
      .connect(
        process.env.MONGODB_URI || "mongodb://localhost:27017/restaurant"
      )
      .then(() => console.log("Conectado a MongoDB"));
  } catch (err) {
    console.error("Error de conexión a MongoDB:", err.message);
    process.exit(1);
  }
};

export default connectDB;
