# 1nventory

Application web de gestion d'inventaire du parc informatique : postes (modèle, marque, affectation, statut), stock et demandes d'équipement.

Projet Docker & Docker Compose réalisé en groupe de 3.

## Architecture

3 conteneurs, 3 images (multi-stage build), publiées sur un registry privé Docker Hub.

| Service | Rôle | Techno | Port interne | Exposé |
|---|---|---|---|---|
| `front` | Interface web + proxy `/api/` vers l'API | nginx:alpine | 80 | oui (80) |
| `api` | Postes, affectations, demandes | Python Flask + gunicorn | 5000 | non |
| `stock` | Quantités en stock (SQLite persistant) | Python Flask + gunicorn | 5001 | non |

Seul le `front` est accessible depuis l'extérieur. L'`api` appelle `stock` via le réseau interne (`STOCK_URL=http://stock:5001`).

## Images (registry privé)

```
luisgp863/repo-luis:front
luisgp863/repo-luis:api
luisgp863/repo-luis:stock
```

Build et push d'une image (exemple pour `stock`) :

```bash
cd stock
docker build -t luisgp863/repo-luis:stock .
docker push luisgp863/repo-luis:stock
```

## Lancer l'application (production)

Les images sont téléchargées depuis le registry, aucun code source n'est nécessaire.

```bash
cd prod
cp .env.example .env
docker login
docker compose pull
docker compose up -d
docker compose ps
```

Ouvrir ensuite http://localhost.

Arrêter : `docker compose down` (les données de stock sont conservées).
Tout réinitialiser, volume compris : `docker compose down -v`.

## Contrat d'API

JSON partout. Erreurs au format `{"erreur": "message"}`. Chaque service expose `GET /health`.

**front → api**

| Route | Rôle |
|---|---|
| `GET /devices` | liste des postes |
| `POST /devices` | ajouter un poste |
| `PUT /devices/<id>` | modifier affectation / statut |
| `POST /requests` | demande d'équipement |
| `GET /requests` | liste des demandes |
| `GET /stock` | quantités (relayées depuis `stock`) |

**api → stock**

| Route | Rôle |
|---|---|
| `GET /stock` | toutes les quantités |
| `GET /stock/<modele>` | une quantité |
| `PUT /stock/<modele>` | fixer la quantité (`{"quantite": 4}`) |

Valeurs fixes : `statut` = `utilise` \| `range` ; `etat` = `en_attente` \| `acceptee` \| `refusee`.

## Persistance du stock

Le service `stock` enregistre ses données dans une base SQLite (`/data/stock.db`), montée sur le volume Docker `stock_data`. Les quantités survivent donc au redémarrage et à la mise à jour de l'image.

## Structure du dépôt

```
front/    Dockerfile + site statique + config nginx
api/      Dockerfile + API Flask
stock/    Dockerfile + service de stock
prod/     docker-compose.yml de production + .env.example
```

## Équipe

- Front : Youssef 
- API : Arnaud
- Stock, registry et compose de production : Luis

