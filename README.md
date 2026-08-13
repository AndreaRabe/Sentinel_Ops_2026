# Sentinel Ops

Plateforme de gestion d'équipe sécurité — tâches, planning, incidents, audit.

Documentation complète du projet (périmètre, architecture, modèle de données, sécurité, roadmap) : voir `sentinel-ops-cahier-des-charges.md`.

> **Docker et Redis non utilisés pour le moment.** Le projet tourne actuellement en installation native (backend/frontend/PostgreSQL lancés directement sur la machine). La conteneurisation (Docker Compose + nginx) et Redis (cache, verrouillage brute-force du login) font partie de l'architecture cible documentée dans le cahier des charges et seront réintroduits plus tard — voir la remarque de sécurité correspondante plus bas.

---

## Stack

- **Frontend** : React + Vite + TypeScript + Tailwind
- **Backend** : FastAPI + Poetry + SQLAlchemy (async) + Alembic
- **Base de données** : PostgreSQL, migrations gérées par **Alembic** (voir section dédiée plus bas)
- **Tâches planifiées** : APScheduler (récurrence des tâches, détection des retards)

---

## Prérequis

- Python 3.12 + [Poetry](https://python-poetry.org/)
- Node.js 20+
- PostgreSQL 16 installé et démarré localement
- Un fichier `.env` à la racine (copier `.env.example` et le renseigner — voir section **Configuration** ci-dessous, jamais commiter `.env`)

---

## Configuration (`.env`)

```bash
cp .env.example .env
```

Le fichier `.env` est lu par le backend (`pydantic-settings`) et par les commandes du `Makefile`. Détail de chaque variable :

### Base de données

| Variable | Rôle |
|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Identifiants à créer dans votre instance PostgreSQL locale (`createuser`/`createdb`, ou via `psql`). |
| `DATABASE_URL` | URL de connexion complète utilisée par SQLAlchemy/Alembic : `postgresql+asyncpg://<user>:<password>@localhost:5432/<db>`. Doit rester cohérente avec les 3 variables ci-dessus. |

### Sécurité / authentification

| Variable | Rôle |
|---|---|
| `JWT_SECRET_KEY` | Clé de signature des access tokens JWT (256 bits minimum). **Obligatoire à régénérer avant tout déploiement réel** — ne jamais garder la valeur d'exemple. Génération : `python3 -c "import secrets; print(secrets.token_hex(32))"` ou `openssl rand -hex 32`. |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Durée de vie de l'access token (défaut 15 min, gardé en mémoire côté client, jamais persisté). |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | Durée de vie du refresh token opaque (défaut 30 jours, stocké hashé en base, transporté en cookie httpOnly). |
| `COOKIE_SECURE` | Attribut `Secure` du cookie de refresh token. **`false` tant que l'application tourne en HTTP local** (cas actuel). À passer manuellement à `true` dès que l'application sera servie en HTTPS. |

### Seed (premier compte)

| Variable | Rôle |
|---|---|
| `SEED_ADMIN_EMAIL` | Email du compte Super Admin créé automatiquement sur base vierge (voir "Premier démarrage" plus bas). Le mot de passe temporaire n'est jamais dans `.env` : il est généré aléatoirement et affiché une seule fois dans la sortie de `make seed`. |

### Frontend / CORS

| Variable | Rôle |
|---|---|
| `VITE_API_BASE_URL` | URL de base de l'API telle qu'appelée par le navigateur. `http://localhost:8000/api/v1` en local. |
| `CORS_ALLOWED_ORIGINS` | Origine(s) autorisée(s) par le backend (`allow_credentials=True` étant actif, ne jamais mettre `*`). Doit correspondre exactement à l'origine depuis laquelle le frontend est servi. Plusieurs origines possibles, séparées par des virgules. |

---

## Démarrage — environnement de développement

1. Assurez-vous que PostgreSQL tourne localement, et que la base/l'utilisateur définis dans `.env` existent.
2. Installez les dépendances :
   ```bash
   make install
   ```
3. Appliquez les migrations puis créez le compte Super Admin initial :
   ```bash
   make migrate
   make seed
   ```
   Le mot de passe temporaire du Super Admin s'affiche dans la sortie de `make seed` — il n'est jamais stocké en clair ni committé.
4. Lancez backend et frontend en parallèle :
   ```bash
   make dev
   ```

L'application est accessible sur `http://localhost:5173` (frontend) et l'API sur `http://localhost:8000/api/v1` (`/docs` pour la documentation OpenAPI interactive).

Connectez-vous avec l'email/mot de passe du Super Admin : le système forcera immédiatement un changement de mot de passe avant tout accès au reste de l'application. Depuis ce compte, créez ensuite les comptes réels de l'équipe (Responsable, Chefs d'équipe, Agents) via **Administration → Ajouter un utilisateur**.

`make seed` est idempotent : le relancer ne recrée jamais de second compte Super Admin si un existe déjà.

---

## Base de données — migrations (Alembic)

Le schéma est entièrement défini par des migrations versionnées dans `backend/alembic/versions/` — **aucune modification manuelle de la base**, y compris pour `role_permissions` (voir rappel sécurité plus bas).

- `make migrate` : applique les migrations en attente (`alembic upgrade head`). C'est la seule commande qui modifie le schéma.
- `make migration name="ajoute_table_x"` : génère une nouvelle migration à partir des changements détectés sur les modèles SQLAlchemy (`app/models/`), à relire et ajuster manuellement avant de commiter.

La migration initiale (`0001_initial_schema`) met en place :
- les tables d'identité et RBAC : `users`, `roles`, `permissions`, `role_permissions`, `sites`, `user_sites`, `refresh_tokens`, `password_history` ;
- la table d'audit `audit_logs`, protégée par un **trigger PostgreSQL** qui bloque toute tentative d'`UPDATE`/`DELETE` au niveau du moteur (append-only réel, y compris pour le rôle propriétaire de la table — conformément à l'exigence de rétention légale 3 ans) ;
- le peuplement initial des rôles et de leur matrice de permissions, à partir de `backend/app/core/rbac_matrix.py` (source de vérité unique, référencée aussi par le JWT à l'authentification).

---

## Déploiement en production

Pas encore mis en place : la stratégie cible (Docker Compose + nginx en TLS auto-signé, `git pull` + `make migrate` + build/relance des services) est documentée dans `sentinel-ops-cahier-des-charges.md` mais n'est pas encore opérationnelle dans ce dépôt. À faire quand la conteneurisation sera réintroduite.

---

## Commandes utiles (Makefile)

| Commande | Effet |
|---|---|
| `make install` | Installe les dépendances backend (Poetry) et frontend (npm) |
| `make dev` | Lance backend (uvicorn --reload) et frontend (Vite) en parallèle |
| `make test` | Lance les tests backend (pytest) et frontend (vitest) |
| `make lint` | Vérifie le style de code (ruff, black, eslint) |
| `make migrate` | Applique les migrations de base de données (Alembic) |
| `make migration name="..."` | Génère une nouvelle migration à partir des modèles |
| `make seed` | Crée le compte Super Admin initial si la base est vierge (idempotent) |
| `make backup` | Déclenche une sauvegarde manuelle de la base de données (`pg_dump` local) |

---

## Structure du dépôt

```
.
├── backend/                              # API FastAPI
│   ├── app/
│   │   ├── api/v1/endpoints/             # Validation + permissions (require_permission)
│   │   ├── services/                     # Logique métier + appel audit explicite
│   │   ├── repositories/                 # Accès données pur (aucune règle métier)
│   │   ├── models/                       # Modèles SQLAlchemy
│   │   └── core/                         # Config, sécurité (JWT/Argon2id), RBAC
│   └── alembic/versions/                 # Migrations DB versionnées
├── frontend/                             # SPA React
├── Makefile
├── .env.example
└── sentinel-ops-cahier-des-charges.md    # Documentation complète du projet (architecture cible incluse)
```

---

## Sauvegardes

`make backup` déclenche un `pg_dump` local vers `backups/`. **Important** : ces sauvegardes doivent être copiées régulièrement hors de la machine (disque externe ou stockage distant) — l'engagement de rétention de 3 ans sur l'audit n'a de valeur que si les données survivent à une panne matérielle locale.

---

## Sécurité — rappels essentiels

- Ne jamais commiter `.env` ou tout fichier contenant des secrets.
- Toute modification du schéma de permissions (`role_permissions`) doit passer par une migration versionnée (voir `backend/app/core/rbac_matrix.py` et section Alembic ci-dessus), jamais une modification manuelle en base.
- `audit_logs` est protégée par un trigger PostgreSQL append-only : aucun code applicatif ne doit tenter d'`UPDATE`/`DELETE` dessus (cela échouerait de toute façon au niveau base).
- `COOKIE_SECURE` doit être passé à `true` dès que l'application n'est plus servie en HTTP local uniquement.
- **Verrouillage brute-force différé** : le cahier des charges (section 7) prévoit un blocage après 5 tentatives de login échouées en 15 min via Redis. Redis n'étant pas utilisé pour le moment, ce blocage n'est pas actif — seules les tentatives échouées restent journalisées dans `audit_logs`. À réactiver dans `auth_service.py` dès que Redis sera réintroduit.

---

## Documentation complémentaire

Voir `sentinel-ops-cahier-des-charges.md` pour : le détail du modèle de données, l'architecture applicative complète (y compris la conteneurisation cible), la stratégie de sécurité, l'API, la stratégie de tests, la stratégie DevOps et la roadmap par phases.
