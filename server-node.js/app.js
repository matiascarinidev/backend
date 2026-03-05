import express from "express";
import cors from "cors";

import userRoutes from "./src/routes/user.routes.js";

const app = express();
const port = 3000;

app.use(cors());
app.use(express.json());

app.use("/users", userRoutes);

if (process.env.NODE_ENV !== "test") {
  app.listen(port, () =>
    console.log(`⚡️[server]: Server is running at https://localhost:${port}`)
  );
}

export default app;
