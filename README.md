# 1nventory

Application web de gestion d'inventaire du parc informatique : postes (modèle, marque, affectation, statut), stock et demandes d'équipement.

Projet Docker & Docker Compose réalisé en groupe de 3.

URL avec Duck DNS: [https://1nventory.duckdns.org](https://1nventory.duckdns.org)

## Architecture

4 conteneurs, 4 images (multi-stage build) publiées sur un registry privé Docker Hub. Caddy, installé sur le serveur, assure le HTTPS.

| Service | Rôle                                   | Techno                  | Port | Exposé                      |
|---------|----------------------------------------|-------------------------|------|-----------------------------|
| `proxy` | Reverse proxy interne                  | nginx:1.27-alpine       | 80   | `127.0.0.1:8080` uniquement |
| `front` | Interface web                          | nginx:alpine            | 80   | non                         |
| `api`   | Postes, affectations, demandes         | Python Flask + gunicorn | 5000 | non                         |
| `stock` | Quantités en stock (SQLite persistant) | Python Flask + gunicorn | 5001 | non                         |

```
internet → Caddy (HTTPS) → 127.0.0.1:8080 → proxy ─┬─ /      → front
                                                    └─ /api/  → api → stock
```

Images : `luisgp863/repo-luis:proxy`, `:front`, `:api`, `:stock`.

## Lancer l'application

```bash
cd prod
cp .env.example .env
docker login
docker compose pull
docker compose up -d
docker compose ps
```

En local : http://localhost:8080. Arrêter : `docker compose down` (le stock est conservé).

## Déploiement sur DigitalOcean

Le script `startup-script.sh` prépare un droplet Ubuntu : il installe Docker et Caddy, ouvre les ports 22, 80 et 443 (`ufw`), clone ce dépôt dans `/opt/1nventaire` et crée le `.env`.

```bash
chmod +x startup-script.sh
./startup-script.sh
cd /opt/1nventaire/prod
docker login -u luisgp863
docker compose up -d
```

## Réseaux

| Réseau     | Sous-réseau     | Services                | Particularité                |
|------------|-----------------|-------------------------|------------------------------|
| `frontnet` | `172.20.0.0/24` | `proxy`, `front`, `api` | côté web                     |
| `backnet`  | `172.21.0.0/24` | `api`, `stock`          | `internal` (sans internet)   |


## API

JSON partout, `GET /health` sur chaque service, erreurs au format `{"erreur": "message"}`. Le navigateur appelle l'API sous `/api/`.

| Route (front → api)  | Rôle                          |
|----------------------|-------------------------------|
| `GET/POST /devices`  | lister / ajouter un poste     |
| `PUT /devices/<id>`  | modifier affectation / statut |
| `GET/POST /requests` | demandes d'équipement         |
| `GET /stock`         | quantités (relayées par stock)|

## Équipe

- Youssef
- Arnaud
- Luis
