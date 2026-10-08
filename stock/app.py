import os
import sqlite3
from flask import Flask, jsonify, request

app = Flask(__name__)
DB = os.environ.get("DB_PATH", "/data/stock.db")

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    with db() as c:
        c.execute("CREATE TABLE IF NOT EXISTS stock (modele TEXT PRIMARY KEY, quantite INTEGER NOT NULL)")
        c.executemany("INSERT OR IGNORE INTO stock VALUES (?, ?)",
                      [("Latitude 5420", 5), ("ThinkPad T14", 3)])

init()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/stock")
def lista():
    with db() as c:
        rows = c.execute("SELECT modele, quantite FROM stock").fetchall()
    return jsonify([dict(r) for r in rows])

@app.get("/stock/<modele>")
def uno(modele):
    with db() as c:
        r = c.execute("SELECT modele, quantite FROM stock WHERE modele=?", (modele,)).fetchone()
    if r is None:
        return {"erreur": "Modèle introuvable"}, 404
    return dict(r)

@app.put("/stock/<modele>")
def maj(modele):
    data = request.get_json(silent=True) or {}
    q = data.get("quantite")
    if not isinstance(q, int) or q < 0:
        return {"erreur": "quantite doit être un entier >= 0"}, 400
    with db() as c:
        c.execute("INSERT INTO stock VALUES (?, ?) "
                  "ON CONFLICT(modele) DO UPDATE SET quantite=excluded.quantite", (modele, q))
    return {"modele": modele, "quantite": q}
