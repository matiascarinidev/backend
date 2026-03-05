import db from "../config/db.js";
import { randomUUID } from "node:crypto";

export function getItem(id) {
  try {
    const user = db?.users?.filter((user) => user?.id === id);
    if (!user) throw new Error("Usuario no encontrado");
    return user;
  } catch (err) {
    console.log("Error", err);
  }
}

export function listItems() {
  try {
    return db?.users;
  } catch (err) {
    console.log("Error", err);
  }
}

export function editItem(id, data) {
  try {
    const index = db.users.findIndex((user) => user.id === id);
    if (index === -1) throw new Error("User Not found");
    db.users[index] = { ...db.users[index], ...data };
    return db.users[index];
  } catch (err) {
    console.log("Error", err);
  }
}
export function addItem(data) {
  try {
    const newUser = { id: randomUUID(), ...data };
    db.users.push(newUser);
    return newUser;
  } catch (err) {
    console.log("Error", err);
  }
}

export function deleteItem(id) {
  try {
    const index = db.users.findIndex((user) => user.id === id);
    if (index === -1) throw new Error("User not Found");
  } catch (err) {
    console.log("Error", err);
  }
}
