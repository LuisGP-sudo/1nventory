# 1nventory — Gestion du parc informatique

Application web de gestion d'inventaire informatique : postes, affectations, statuts, stock et demandes d'équipement.

Projet réalisé en groupe de 3 dans le cadre d'un projet Docker et Docker Compose.

**Production :** https://1nventory.duckdns.org

## 1. Architecture

L'application comprend quatre services Docker, construits à partir de quatre images distinctes et publiées sur Docker Hub.

| Service | Rôle | Technologie | Port interne |
|---|---|---|---|
| `proxy` | Routage HTTP vers le front et l'API | Nginx 1.27 Alpine | 80 |
| `front` | Interface web | Nginx Alpine | 80 |
| `api` | Postes, affectations et demandes | Flask + Gunicorn | 5000 |
| `stock` | Gestion du stock et persistance SQLite | Flask + Gunicorn | 5001 |

En production, Caddy est installé sur le serveur Ubuntu. Il gère HTTPS et transmet les requêtes au proxy Nginx du projet.

```text
Navigateur
    |
    | HTTPS :443
    v
Caddy (serveur Ubuntu)
    |
    | HTTP vers 127.0.0.1:8080
    v
proxy (Nginx Docker :80)
    |----------------------|
    v                      v
front:80                 api:5000
                            |
                            v
                         stock:5001
```

Le proxy Docker est le seul service applicatif accessible via un port publié. Les services `front`, `api` et `stock` ne publient pas directement de port sur l'hôte.

## 2. Construction et partage des images — Docker Hub

Les images sont publiées dans le registre Docker Hub suivant :

```text
luisgp863/repo-luis:proxy
luisgp863/repo-luis:front
luisgp863/repo-luis:api
luisgp863/repo-luis:stock
```

### Construire et publier une image

Exemple pour le service `stock`, depuis la racine du dépôt :

```bash
docker build -t luisgp863/repo-luis:stock ./stock
docker login
docker push luisgp863/repo-luis:stock
```

Le même principe s'applique aux autres services en adaptant le répertoire et le tag.

- **Dockerfile :** décrit la construction de l'image, sa base et les dépendances nécessaires.
- **Image :** paquet contenant l'application et son environnement d'exécution.
- **Tag :** identifie une variante ou une version de l'image.
- **Registre :** permet de partager les images entre la machine de développement et le serveur de production.

Les Dockerfiles utilisent une construction multi-stage lorsque cela est prévu par leur contenu, afin de séparer les étapes de construction de l'image finale.

### Télécharger les images en production

```bash
docker compose pull
docker compose up -d
```

La production utilise les images du registre : le code source n'a pas besoin d'être présent sur le serveur pour exécuter les conteneurs.

> Les tags utilisés dans ce projet sont des tags réutilisables. Pour garantir la reproductibilité d'un déploiement, il est préférable de publier également des tags versionnés, plutôt que de dépendre uniquement d'un tag fixe tel que `stock`.

## 3. Installation et démarrage

### Prérequis

- Docker Engine et le plugin Docker Compose.
- Accès au registre Docker Hub si les images sont privées.
- Un fichier `.env` configuré à partir de `.env.example`.

### Lancement de l'application

Depuis la racine du dépôt :

```bash
cd prod
cp .env.example .env
```

Renseigner les variables requises dans `.env`, puis exécuter :

```bash
docker login
docker compose config -q
docker compose pull
docker compose up -d
docker compose ps
```

En environnement local, ouvrir :

http://localhost

### Déploiement sur le serveur de production

Sur le serveur Ubuntu :

```bash
cd /opt/1nventaire/prod
docker compose config -q
docker compose pull
docker compose up -d
docker compose ps
```

Le port du proxy Docker est publié uniquement sur l'interface locale :

```yaml
ports:
  - "127.0.0.1:8080:80"
```

Cela permet à Caddy de joindre le proxy sans exposer directement le port 8080 sur Internet.

### Arrêt et redémarrage

Arrêter les services et supprimer les conteneurs :

```bash
docker compose down
```

Redémarrer les services :

```bash
docker compose up -d
```

Les données du volume nommé sont conservées après un `docker compose down`.

**Attention :** `docker compose down -v` supprime également les volumes du projet et peut entraîner la perte des données du stock. À utiliser uniquement si une réinitialisation complète est souhaitée.

## 4. Reverse proxy et HTTPS

Deux reverse proxies ont des responsabilités distinctes.

### Caddy : entrée publique et TLS

Caddy est installé sur le serveur Ubuntu, en dehors de Docker. Il reçoit les connexions HTTP et HTTPS, gère les certificats TLS et transmet les requêtes au proxy applicatif.

Configuration `/etc/caddy/Caddyfile` :

```caddyfile
1nventory.duckdns.org {
    reverse_proxy 127.0.0.1:8080
}
```

Le domaine DuckDNS doit pointer vers l'adresse IP publique du serveur. Les ports TCP 80 et 443 doivent être autorisés dans le pare-feu du serveur et dans celui de DigitalOcean.

Caddy utilise son mécanisme de gestion automatique des certificats pour obtenir et renouveler le certificat TLS. Let's Encrypt peut fournir ce certificat. Le port 80 peut notamment servir à la validation du domaine et à la redirection vers HTTPS.

Valider et recharger la configuration :

```bash
caddy validate --config /etc/caddy/Caddyfile
systemctl reload caddy
systemctl status caddy --no-pager
```

### Nginx : routage applicatif

Le conteneur `proxy` distribue les requêtes selon leur chemin.

| Chemin demandé | Destination |
|---|---|
| `/api/...` | `http://api:5000/...` |
| Tous les autres chemins | `http://front:80` |

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
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

Le `/` final de `proxy_pass http://api:5000/;` permet de retirer le préfixe `/api/` lors du transfert. Ainsi, `/api/devices` est transmis à l'API sous le chemin `/devices`.

La configuration Nginx est intégrée à l'image Docker du proxy. Aucun montage de configuration externe n'est requis en production.

### Vérification de la chaîne de routage

```bash
# Vérifier les conteneurs
docker compose ps

# Vérifier le proxy local sur le serveur
curl -I http://127.0.0.1:8080

# Vérifier une route API à travers le proxy
curl https://1nventory.duckdns.org/api/stock

# Vérifier HTTPS
curl -Iv https://1nventory.duckdns.org

# Examiner les journaux
docker compose logs --tail=50 proxy
journalctl -u caddy -n 50 --no-pager
```

## 5. Réseaux Docker et isolation

L'application utilise deux réseaux Docker dédiés.

| Réseau | Sous-réseau configuré | Services | Fonction |
|---|---|---|---|
| `frontnet` | `172.20.0.0/24` | `proxy`, `front`, `api` | Communication côté web |
| `backnet` | `172.21.0.0/24` | `api`, `stock` | Communication avec le stock ; réseau interne |

```text
frontnet
  proxy ─── front
    |
    └────── api
               |
backnet        |
  api ─────── stock
```

- L'API appartient aux deux réseaux : elle communique avec le proxy et avec le service stock.
- Le service `stock` appartient uniquement à `backnet`.
- `backnet` est déclaré `internal: true`, ce qui limite sa connectivité externe.
- Les services se joignent par leur nom DNS Docker, par exemple `http://api:5000` et `http://stock:5001`.

Les sous-réseaux indiqués sont ceux configurés dans Compose. Ils doivent être vérifiés sur l'environnement réellement déployé.

### Vérifier les réseaux

```bash
docker network ls
docker network inspect prod_frontnet
docker network inspect prod_backnet
```

Tester l'isolation depuis le conteneur `front` :

```bash
docker compose exec front \
  wget -qO- -T 3 http://stock:5001/health
```

Cette requête doit échouer, car `front` n'appartient pas au réseau `backnet`.

Tester l'accès depuis l'API :

```bash
docker compose exec api python -c \
"import urllib.request; print(urllib.request.urlopen('http://stock:5001/health').read())"
```

Cette requête doit réussir si les services fonctionnent normalement.

## 6. Volumes et persistance

Le service `stock` stocke ses données dans une base SQLite :

```text
/data/stock.db
```

Le répertoire `/data` est associé à un volume Docker nommé `stock_data`.

Ce volume permet de conserver la base lorsque le conteneur est supprimé et recréé. Les données ne sont donc pas limitées au système de fichiers éphémère du conteneur.

Vérifier les volumes :

```bash
docker volume ls
docker volume inspect prod_stock_data
```

La persistance ne remplace pas une sauvegarde : pour protéger les données contre une suppression accidentelle ou une panne du serveur, des sauvegardes régulières restent nécessaires.

## 7. Configuration Docker Compose

Le fichier `prod/docker-compose.yml` définit les quatre services, les images, les réseaux, les volumes, les variables d'environnement, les dépendances et les healthchecks.

| Option | Fonction |
|---|---|
| `image` | Indique l'image à utiliser |
| `pull_policy: always` | Demande de vérifier l'image distante lors des opérations de démarrage concernées |
| `ports` | Publie un port du conteneur sur l'hôte |
| `networks` | Définit les réseaux auxquels le service appartient |
| `env_file` | Charge les variables depuis `.env` |
| `volumes` | Persiste les données en dehors du cycle de vie du conteneur |
| `restart: unless-stopped` | Redémarre le conteneur après un incident ou un redémarrage, sauf arrêt volontaire |
| `healthcheck` | Vérifie périodiquement l'état de fonctionnement du service |
| `depends_on` | Définit les dépendances et, si configuré, des conditions de santé au démarrage |

Le fichier de production ne contient pas de section `build` : les images sont construites et publiées séparément, puis téléchargées depuis le registre.

### Healthchecks

Chaque service possède un test de santé adapté à son fonctionnement.

| Service | Test |
|---|---|
| `proxy` | Requête HTTP vers `127.0.0.1:80` |
| `front` | Requête HTTP vers `127.0.0.1:80` |
| `api` | Requête vers `/health` sur le port 5000 |
| `stock` | Requête vers `/health` sur le port 5001 |

Les paramètres tels que `interval`, `timeout`, `retries` et `start_period` définissent la fréquence des contrôles, leur durée maximale, le nombre d'échecs avant de déclarer le service non sain et le délai de grâce initial.

Un état `healthy` confirme que le test configuré réussit ; il ne garantit pas à lui seul que toutes les fonctionnalités métier sont correctes.

### Ordre de démarrage

```text
stock healthy → api → front → proxy
```

L'API attend que le stock soit sain si `depends_on` utilise `condition: service_healthy`. Le front et le proxy sont ensuite démarrés selon les dépendances déclarées dans Compose.

Vérifier l'état des services :

```bash
docker compose ps
docker compose logs --tail=50
docker stats --no-stream
```

## 8. Contrat d'API

Les échanges utilisent le format JSON. Les erreurs sont renvoyées sous la forme `{"erreur": "message"}`. Chaque service expose une route `GET /health`.

### Front vers API

| Méthode | Route | Fonction |
|---|---|---|
| GET | `/devices` | Lister les postes |
| POST | `/devices` | Ajouter un poste |
| PUT | `/devices/<id>` | Modifier l'affectation ou le statut |
| GET | `/requests` | Lister les demandes |
| POST | `/requests` | Créer une demande |
| GET | `/stock` | Consulter les quantités |

Le navigateur accède à ces routes via le préfixe `/api/`, par exemple `GET /api/devices`.

### API vers stock

| Méthode | Route | Fonction |
|---|---|---|
| GET | `/stock` | Obtenir toutes les quantités |
| GET | `/stock/<modele>` | Obtenir la quantité d'un modèle |
| PUT | `/stock/<modele>` | Modifier la quantité, par exemple `{"quantite": 4}` |

Valeurs prévues :
- `statut` : `utilise` ou `range`.
- `etat` : `en_attente`, `acceptee` ou `refusee`.

## 9. Structure du dépôt

```text
proxy/    Dockerfile + nginx.conf
front/    Dockerfile + interface web + configuration Nginx
api/      Dockerfile + API Flask
stock/    Dockerfile + service de stock
prod/     docker-compose.yml + .env.example
```

## 10. Équipe

- Front : Youssef
- API : Arnaud
- Stock : Luis
