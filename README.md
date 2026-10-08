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

## Explication du docker-compose.yml

Le fichier `prod/docker-compose.yml` décrit comment les 3 conteneurs sont lancés ensemble en production. Il n'y a aucun `build:` : tout vient des images du registry.

### Les services

| Service | Image | Particularités |
|---|---|---|
| `front` | `luisgp863/repo-luis:front` | Seul service qui publie un port (`80:80`). Dépend de `api`. |
| `api` | `luisgp863/repo-luis:api` | Lit sa configuration dans `.env` (`env_file`). Attend que `stock` soit sain. |
| `stock` | `luisgp863/repo-luis:stock` | Monte le volume `stock_data` sur `/data` pour garder la base SQLite. |

### Les options utilisées

- **`image`** : l'image est téléchargée depuis le registry privé Docker Hub (il faut faire `docker login` avant).
- **`pull_policy: always`** : à chaque `docker compose up`, Docker vérifie et télécharge la dernière version du tag. On récupère ainsi toujours l'image la plus récente poussée par l'équipe.
- **`ports: "80:80"`** : le port 80 de la machine est relié au port 80 du conteneur. Seul `front` est exposé ; `api` et `stock` ne sont joignables que depuis le réseau interne Docker.
- **`env_file: .env`** : les variables d'environnement (par exemple `STOCK_URL=http://stock:5001`) sont lues dans le fichier `.env`, qui n'est pas versionné. Un modèle est fourni dans `.env.example`.
- **`volumes: stock_data:/data`** : le volume nommé `stock_data` (déclaré tout en bas du fichier) survit à la suppression des conteneurs. C'est ce qui rend le stock persistant.
- **`restart: unless-stopped`** : le conteneur redémarre automatiquement après un plantage ou un redémarrage de la machine, sauf s'il a été arrêté volontairement.

### Les healthchecks

Chaque service est testé régulièrement pour savoir s'il fonctionne vraiment, et pas seulement s'il est démarré.

| Service | Test | Paramètres |
|---|---|---|
| `front` | `wget` sur `http://localhost:80` | toutes les 10 s, timeout 3 s, 3 essais |
| `api` | requête Python sur `http://localhost:5000/health` | idem + `start_period: 10s` |
| `stock` | requête Python sur `http://localhost:5001/health` | idem + `start_period: 10s` |

`start_period: 10s` laisse 10 secondes au service pour démarrer avant que les échecs ne comptent. Après 3 échecs de suite, le conteneur passe en `unhealthy`.

### L'ordre de démarrage (`depends_on`)

```
stock (sain)  →  api  →  front
```

- `api` attend que `stock` soit `healthy` (`condition: service_healthy`), car elle l'appelle pour les quantités.
- `front` attend que `api` soit démarré.

### Réseau

Aucun réseau n'est déclaré : Compose en crée un par défaut (`prod_default`). Les conteneurs s'y trouvent par leur nom de service (`http://api:5000`, `http://stock:5001`), sans avoir besoin d'adresses IP.

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
