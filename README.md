# 1nventory

Application web de gestion d'inventaire du parc informatique : postes (modèle, marque, affectation, statut), stock et demandes d'équipement.

Projet Docker & Docker Compose réalisé en groupe de 3.

URL with Duck DNS: [https://1nventory.duckdns.org](https://1nventory.duckdns.org)

## Architecture

4 conteneurs, 4 images (multi-stage build), publiées sur un registry privé Docker Hub. Un serveur Caddy, installé sur l'hôte (le droplet DigitalOcean), assure le HTTPS.

| Service | Rôle                                   | Techno                  | Port interne | Exposé                       |
|---------|----------------------------------------|-------------------------|--------------|------------------------------|
| `proxy` | Reverse proxy interne, point d'entrée  | nginx:1.27-alpine       | 80           | `127.0.0.1:8080` uniquement  |
| `front` | Interface web                          | nginx:alpine            | 80           | non                          |
| `api`   | Postes, affectations, demandes         | Python Flask + gunicorn | 5000         | non                          |
| `stock` | Quantités en stock (SQLite persistant) | Python Flask + gunicorn | 5001         | non                          |

```
internet ─ 443 ─▶ Caddy (hôte, HTTPS) ─▶ 127.0.0.1:8080 ─▶ proxy ─┬─ /      → front:80
                                                                    └─ /api/  → api:5000 → stock:5001
```

Aucun conteneur n'est joignable directement depuis Internet : le `proxy` n'écoute que sur `127.0.0.1:8080`, et seul Caddy (ports 80 et 443 de l'hôte) est public. L'`api` appelle `stock` via le réseau interne (`STOCK_URL=http://stock:5001`).

## Images (registry privé)

```
luisgp863/repo-luis:proxy
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

En local, ouvrir ensuite http://localhost:8080. Sur le serveur, l'application est servie en HTTPS par Caddy (voir plus bas).

Arrêter : `docker compose down` (les données de stock sont conservées). Tout réinitialiser, volume compris : `docker compose down -v`.

## Déploiement sur DigitalOcean

Le script `startup-script.sh` prépare un droplet Ubuntu 24.04 (cloud-init, ou exécution manuelle). Il :

1. installe Docker et le plugin Compose (dépôt officiel) ;
2. installe Caddy (dépôt officiel) et écrit `/etc/caddy/Caddyfile` ;
3. configure le pare-feu `ufw` (ports 22, 80 et 443) ;
4. clone ce dépôt dans `/opt/1nventaire` et crée `prod/.env` à partir de `.env.example` ;
5. si un token Docker Hub est fourni, fait le `docker login`, puis `docker compose pull` et `docker compose up -d`.

Utilisation :

- À la création du droplet : *Advanced options* → *Add Initialization scripts*, puis coller le script.
- Ou, directement sur la machine :

```bash
chmod +x startup-script.sh
./startup-script.sh 2>&1 | tee setup.log
```

Sans token, la dernière étape se fait à la main :

```bash
cd /opt/1nventaire/prod
docker login -u luisgp863
docker compose up -d
```

Le token Docker Hub (variable `DOCKERHUB_TOKEN`, vide par défaut) n'est jamais écrit dans le dépôt : il doit être en lecture seule et révoqué après usage.

## HTTPS avec Caddy et Let's Encrypt

Caddy tourne directement sur l'hôte et fait office de reverse proxy externe. Il obtient et renouvelle automatiquement le certificat Let's Encrypt du domaine DuckDNS, puis transmet le trafic au conteneur `proxy` :

```
1nventory.duckdns.org {
    reverse_proxy 127.0.0.1:8080
}
```

Prérequis :

- le sous-domaine DuckDNS doit pointer vers l'IP publique du droplet (`dig +short 1nventory.duckdns.org`) ;
- les ports 80 (validation Let's Encrypt et redirection) et 443 doivent être ouverts, dans `ufw` et dans le pare-feu DigitalOcean s'il y en a un.

Vérification :

```bash
curl -I https://1nventory.duckdns.org
curl https://1nventory.duckdns.org/api/stock
systemctl status caddy
journalctl -u caddy --no-pager | tail -20
```

Les certificats sont stockés sur l'hôte et survivent à `docker compose down`.

## Reverse proxy interne (nginx)

Un conteneur nginx (`proxy`) est le seul service Docker qui publie un port, et uniquement sur la boucle locale. Il reçoit les requêtes de Caddy et les redirige selon l'URL :

| URL           | Destination                                          |
|---------------|------------------------------------------------------|
| `/api/...`    | `http://api:5000/...` (le préfixe `/api` est retiré) |
| tout le reste | `http://front:80`                                    |

Extrait de `proxy/nginx.conf` :

```nginx
location /api/ {
  proxy_pass http://api:5000/;
  proxy_set_header Host $host;
  proxy_set_header X-Real-IP $remote_addr;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  proxy_set_header X-Forwarded-Proto $scheme;
}

location / {
  proxy_pass http://front:80;
  # mêmes en-têtes proxy_set_header
}
```

La configuration est copiée dans l'image (`proxy/Dockerfile`, basé sur `nginx:1.27-alpine`) : aucun fichier de configuration n'est nécessaire côté production.

Intérêts : un seul point d'entrée pour les conteneurs, `front` et `api` ne sont pas exposés directement, pas de problème de CORS, et les en-têtes `X-Forwarded-*` transmettent l'origine de la requête.

### Vérifier que le proxy fonctionne

Sur la machine qui exécute le compose :

```bash
curl -I localhost:8080/                  # 200 OK (front, via le proxy)
curl localhost:8080/api/stock            # données de stock (proxy → api → stock)
docker compose logs proxy --tail 10      # les requêtes apparaissent
docker port prod-front-1                 # aucun port publié
docker compose stop proxy
curl -I localhost:8080/                  # Connection refused
docker compose start proxy
```

## Réseaux et sous-réseaux

Le trafic est séparé en deux réseaux Docker, chacun avec son sous-réseau :

| Réseau     | Sous-réseau     | Services                | Particularité                             |
|------------|-----------------|-------------------------|-------------------------------------------|
| `frontnet` | `172.20.0.0/24` | `proxy`, `front`, `api` | côté web                                  |
| `backnet`  | `172.21.0.0/24` | `api`, `stock`          | `internal: true` (aucun accès à internet) |

```
frontnet : proxy ── front
              └──── api ──┐
backnet  :        api ── stock
```

- L'`api` est dans les deux réseaux : elle fait le lien entre le web et les données.
- `stock` n'est que dans `backnet` : ni le `proxy` ni le `front` ne peuvent le joindre, ni par son nom ni par son IP.
- Les services se trouvent par leur nom (`http://api:5000`, `http://stock:5001`), les adresses IP sont attribuées automatiquement par Docker.

Vérification de l'isolation :

```bash
docker network inspect prod_frontnet prod_backnet | grep -E "Name|Subnet"
docker compose exec front wget -qO- -T 3 http://stock:5001/health   # doit échouer
docker compose exec api python -c "import urllib.request; print(urllib.request.urlopen('http://stock:5001/health').read())"   # doit répondre
```

## Explication du docker-compose.yml

Le fichier `prod/docker-compose.yml` décrit comment les 4 conteneurs sont lancés ensemble en production. Il n'y a aucun `build:` : tout vient des images du registry.

### Les services

| Service | Image                       | Particularités                                                                                                |
|---------|-----------------------------|---------------------------------------------------------------------------------------------------------------|
| `proxy` | `luisgp863/repo-luis:proxy` | Seul service qui publie un port (`127.0.0.1:8080:80`). Réseau `frontnet`. Dépend de `front` et `api`.         |
| `front` | `luisgp863/repo-luis:front` | Aucun port publié. Réseau `frontnet`. Dépend de `api`.                                                        |
| `api`   | `luisgp863/repo-luis:api`   | Lit sa configuration dans `.env` (`env_file`). Réseaux `frontnet` et `backnet`. Attend que `stock` soit sain. |
| `stock` | `luisgp863/repo-luis:stock` | Réseau `backnet` uniquement. Monte le volume `stock_data` sur `/data` pour garder la base SQLite.             |

### Les options utilisées

- **`image`** : l'image est téléchargée depuis le registry privé Docker Hub (il faut faire `docker login` avant).
- **`pull_policy: always`** : à chaque `docker compose up`, Docker vérifie et télécharge la dernière version du tag. On récupère ainsi toujours l'image la plus récente poussée par l'équipe.
- **`ports: "127.0.0.1:8080:80"`** : le port 8080 de la machine, accessible uniquement depuis la machine elle-même (`127.0.0.1`), est relié au port 80 du conteneur `proxy`. Seul `proxy` publie un port ; `front`, `api` et `stock` ne sont joignables que depuis les réseaux internes Docker. Caddy, sur l'hôte, fait le lien avec Internet.
- **`networks`** : chaque service est rattaché uniquement aux réseaux dont il a besoin (voir la section précédente).
- **`env_file: .env`** : les variables d'environnement (par exemple `STOCK_URL=http://stock:5001`) sont lues dans le fichier `.env`, qui n'est pas versionné. Un modèle est fourni dans `.env.example`.
- **`volumes: stock_data:/data`** : le volume nommé `stock_data` (déclaré tout en bas du fichier) survit à la suppression des conteneurs. C'est ce qui rend le stock persistant.
- **`restart: unless-stopped`** : le conteneur redémarre automatiquement après un plantage ou un redémarrage de la machine, sauf s'il a été arrêté volontairement.

### Les healthchecks

Chaque service est testé régulièrement pour savoir s'il fonctionne vraiment, et pas seulement s'il est démarré.

| Service | Test                                              | Paramètres                                                  |
|---------|---------------------------------------------------|-------------------------------------------------------------|
| `proxy` | `wget` sur `http://127.0.0.1:80`                  | toutes les 10 s, timeout 3 s, 3 essais, `start_period: 10s` |
| `front` | `wget` sur `http://127.0.0.1:80`                  | toutes les 10 s, timeout 3 s, 3 essais                      |
| `api`   | requête Python sur `http://localhost:5000/health` | toutes les 10 s, timeout 3 s, 3 essais, `start_period: 10s` |
| `stock` | requête Python sur `http://localhost:5001/health` | toutes les 10 s, timeout 3 s, 3 essais, `start_period: 10s` |

`start_period: 10s` laisse 10 secondes au service pour démarrer avant que les échecs ne comptent. Après 3 échecs de suite, le conteneur passe en `unhealthy`.

Pour `proxy` et `front`, on utilise `127.0.0.1` et non `localhost` : dans les images alpine, `localhost` est résolu d'abord en IPv6 (`::1`) alors que nginx n'écoute qu'en IPv4, ce qui faisait échouer le test alors que le service fonctionnait.

### L'ordre de démarrage (`depends_on`)

```
stock (sain)  →  api  →  front  →  proxy
```

- `api` attend que `stock` soit `healthy` (`condition: service_healthy`), car elle l'appelle pour les quantités.
- `front` attend que `api` soit démarré.
- `proxy` attend `front` et `api`, car nginx doit pouvoir résoudre leurs noms au démarrage.

## Contrat d'API

JSON partout. Erreurs au format `{"erreur": "message"}`. Chaque service expose `GET /health`. Le navigateur accède à l'API via le proxy, sous le préfixe `/api/` (ex. `GET /api/devices`).

**front → api**

| Route               | Rôle                                |
|---------------------|-------------------------------------|
| `GET /devices`      | liste des postes                    |
| `POST /devices`     | ajouter un poste                    |
| `PUT /devices/<id>` | modifier affectation / statut       |
| `POST /requests`    | demande d'équipement                |
| `GET /requests`     | liste des demandes                  |
| `GET /stock`        | quantités (relayées depuis `stock`) |

**api → stock**

| Route                 | Rôle                                  |
|-----------------------|---------------------------------------|
| `GET /stock`          | toutes les quantités                  |
| `GET /stock/<modele>` | une quantité                          |
| `PUT /stock/<modele>` | fixer la quantité (`{"quantite": 4}`) |

Valeurs fixes : `statut` = `utilise` | `range` ; `etat` = `en_attente` | `acceptee` | `refusee`.

## Persistance du stock

Le service `stock` enregistre ses données dans une base SQLite (`/data/stock.db`), montée sur le volume Docker `stock_data`. Les quantités survivent donc au redémarrage et à la mise à jour de l'image.

## Sécurité (résumé)

- Segmentation réseau : `backnet` est `internal`, `stock` n'est joignable que par l'`api`.
- Aucun conteneur exposé directement : le `proxy` n'écoute que sur `127.0.0.1:8080`.
- HTTPS avec un certificat Let's Encrypt renouvelé automatiquement par Caddy.
- Pare-feu `ufw` : seuls les ports 22, 80 et 443 sont ouverts.
- Images multi-stage, tags de base fixés, utilisateur non-root pour les services Python.
- Aucun secret dans le dépôt : `.env` et les tokens ne sont pas versionnés (`.env.example` sert de modèle).

## Structure du dépôt

```
proxy/               Dockerfile + nginx.conf (reverse proxy interne)
front/               Dockerfile + site statique + config nginx
api/                 Dockerfile + API Flask
stock/               Dockerfile + service de stock
prod/                docker-compose.yml de production + .env.example
startup-script.sh    installation d'un droplet (Docker, Caddy, pare-feu, déploiement)
```

## Équipe

- Front : Youssef
- API : Arnaud
- Stock: Luis
