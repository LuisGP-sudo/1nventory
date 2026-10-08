import json
import os

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

DATA_FILE = "data.json"

STOCK_URL = os.getenv("STOCK_URL")


def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def error(message, status_code):
    return jsonify({"erreur": message}), status_code


@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.get("/devices")
def get_devices():
    data = load_data()
    return jsonify(data["devices"]), 200


@app.post("/devices")
def create_device():
    body = request.get_json(silent=True)

    if not body:
        return error("JSON invalide", 400)

    required_fields = [
        "modele",
        "marque",
        "affectation",
        "statut"
    ]

    for field in required_fields:
        if field not in body:
            return error(f"Champ manquant : {field}", 400)

    if body["statut"] not in ["utilise", "range"]:
        return error("Statut invalide", 400)

    if body["statut"] == "range" and body["affectation"] is not None:
        return error(
            "Un poste range doit avoir une affectation null",
            400
        )

    data = load_data()

    new_id = max(
        [device["id"] for device in data["devices"]],
        default=0
    ) + 1

    device = {
        "id": new_id,
        "modele": body["modele"],
        "marque": body["marque"],
        "affectation": body["affectation"],
        "statut": body["statut"]
    }

    data["devices"].append(device)

    save_data(data)

    return jsonify(device), 201


@app.put("/devices/<int:device_id>")
def update_device(device_id):
    body = request.get_json(silent=True)

    if not body:
        return error("JSON invalide", 400)

    if "affectation" not in body or "statut" not in body:
        return error("Champs manquants", 400)

    if body["statut"] not in ["utilise", "range"]:
        return error("Statut invalide", 400)

    if body["statut"] == "range" and body["affectation"] is not None:
        return error(
            "Un poste range doit avoir une affectation null",
            400
        )

    data = load_data()

    device = next(
        (
            device
            for device in data["devices"]
            if device["id"] == device_id
        ),
        None
    )

    if device is None:
        return error("Poste introuvable", 404)

    device["affectation"] = body["affectation"]
    device["statut"] = body["statut"]

    save_data(data)

    return jsonify(device), 200


@app.get("/requests")
def get_requests():
    data = load_data()
    return jsonify(data["requests"]), 200


@app.post("/requests")
def create_request():
    body = request.get_json(silent=True)

    if not body:
        return error("JSON invalide", 400)

    if "demandeur" not in body or "modele" not in body:
        return error("Champs manquants", 400)

    data = load_data()

    new_id = max(
        [item["id"] for item in data["requests"]],
        default=0
    ) + 1

    new_request = {
        "id": new_id,
        "demandeur": body["demandeur"],
        "modele": body["modele"],
        "etat": "en_attente"
    }

    data["requests"].append(new_request)

    save_data(data)

    return jsonify(new_request), 201


@app.get("/stock")
def get_stock():
    if not STOCK_URL:
        return error("STOCK_URL non configuree", 400)

    try:
        response = requests.get(
            f"{STOCK_URL}/stock",
            timeout=5
        )
    except requests.RequestException:
        return error("Service stock indisponible", 404)

    if response.status_code != 200:
        return error("Service stock indisponible", 404)

    return jsonify(response.json()), 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000
    )