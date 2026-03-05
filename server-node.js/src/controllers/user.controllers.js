import {
  listItems,
  getItem,
  editItem,
  addItem,
  deleteItem,
} from "../models/users.models.js";
export function listUsers(req, res) {
  try {
    const { resp } = listItems();
    res.status(200).json(resp);
  } catch (err) {
    res.status(500).send(err);
  }
}
export function getUser(req, res) {
  try {
    const resp = getItem(req.params.id);
    res.status(200).json(resp);
  } catch (err) {
    res.status(500).send(err.mess);
  }
}

export function editUser(req, res) {
  try {
    const resp = editItem(req.params.id, req.body);
    res.status(200).json(resp);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
}
export function addUser(req, res) {
  try {
    const resp = addItem(req.body);
    res.status(200).json(resp);
  } catch (err) {
    res.status(500).send(err);
  }
}

export function deleteUser(req, res) {
  try {
    const resp = deleteItem(req.params.id);
    res.status(200).json(resp);
  } catch (err) {
    res.status(500).send(err);
  }
}
