from flask import Flask, jsonify, request

app = Flask(__name__)
stock = {"Latitude 5420": 5, "ThinkPad T14": 3}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/stock")
def lista():
    return jsonify([{"modele": m, "quantite": q} for m, q in stock.items()])

@app.get("/stock/<modele>")
def uno(modele):
    if modele not in stock:
        return {"erreur": "Modèle introuvable"}, 404
    return {"modele": modele, "quantite": stock[modele]}

@app.put("/stock/<modele>")
def maj(modele):
    stock[modele] = request.get_json()["quantite"]
    return {"modele": modele, "quantite": stock[modele]}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
