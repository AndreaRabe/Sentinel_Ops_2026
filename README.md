# Sentinel Ops

Plateforme de gestion d'équipe sécurité — tâches, planning, incidents, audit.

Documentation complète du projet (périmètre, architecture, modèle de données, sécurité, roadmap) : voir `sentinel-ops-cahier-des-charges.md`.

---

## Stack

- **Frontend** : React + Vite + TypeScript + Tailwind
- **Backend** : FastAPI + Poetry + SQLAlchemy + Alembic
- **Base de données** : PostgreSQL
- **Cache / rate limiting** : Redis
- **Tâches planifiées** : APScheduler (récurrence des tâches, détection des retards)
- **Infra** : Docker Compose + Nginx (TLS auto-signé, réseau local)

---

## Prérequis

- Docker et Docker Compose
- Un fichier `.env` à la racine (copier `.env.example` et renseigner les valeurs — jamais commiter `.env`)

---

## Démarrage — environnement de développement

```bash
cp .env.example .env
make install        # poetry install (backend) + npm install (frontend)
make dev             # lance backend (reload) + frontend (Vite) + services docker (postgres, redis)
```

L'application est accessible sur `https://localhost:5173` (frontend) et l'API sur `https://localhost:8000/api/v1`.

---

## Démarrage — production (self-hosted, réseau local)

```bash
git pull origin main
make migrate         # alembic upgrade head
docker compose up -d --build
```

### Premier démarrage sur une base vierge

Au tout premier lancement, la base de données ne contient aucun utilisateur. Le service `seed` du `docker-compose.yml` détecte automatiquement cette situation et crée le compte **Super Admin** initial :

1. Lancez `docker compose up -d --build`.
2. Consultez les logs du service `seed` **une seule fois** :
   ```bash
   docker compose logs seed
   ```
   Le mot de passe temporaire généré y est affiché — il n'est jamais stocké en clair ni committé.
3. Connectez-vous avec cet identifiant/mot de passe. Le système forcera immédiatement un changement de mot de passe avant tout accès au reste de l'application.
4. Depuis ce compte, créez les comptes réels de l'équipe (Responsable, Chefs d'équipe, Agents) via **Administration → Ajouter un utilisateur**.

Ce mécanisme est idempotent : relancer `docker compose up` ne recrée jamais de second compte Super Admin si un existe déjà.

---

## Commandes utiles (Makefile)

| Commande | Effet |
|---|---|
| `make install` | Installe les dépendances backend (Poetry) et frontend (npm) |
| `make dev` | Lance l'environnement de développement complet |
| `make test` | Lance les tests backend (pytest) et frontend (vitest) |
| `make lint` | Vérifie le style de code (ruff, black, eslint, prettier) |
| `make migrate` | Applique les migrations de base de données (Alembic) |
| `make migration name="..."` | Génère une nouvelle migration à partir des modèles |
| `make docker-up` | Démarre tous les services Docker |
| `make backup` | Déclenche une sauvegarde manuelle de la base de données |

---

## Structure du dépôt

```
.
├── backend/          # API FastAPI
├── frontend/          # SPA React
├── docker-compose.yml
├── Makefile
├── .env.example
└── sentinel-ops-cahier-des-charges.md   # documentation complète du projet
```

---

## Sauvegardes

Un `pg_dump` automatique quotidien est configuré (`make backup` ou tâche planifiée). **Important** : ces sauvegardes doivent être copiées régulièrement hors de la machine hôte (disque externe ou stockage distant) — l'engagement de rétention de 3 ans sur l'audit n'a de valeur que si les données survivent à une panne matérielle locale.

---

## Sécurité — rappels essentiels

- Ne jamais commiter `.env` ou tout fichier contenant des secrets.
- Le certificat TLS est auto-signé (contexte réseau local) — voir le cahier des charges pour la procédure d'installation sur les postes clients.
- Toute modification du schéma de permissions (`role_permissions`) doit passer par une migration versionnée, jamais une modification manuelle en base de production.

---

## Documentation complémentaire

Voir `sentinel-ops-cahier-des-charges.md` pour : le détail du modèle de données, l'architecture applicative complète, la stratégie de sécurité, l'API, la stratégie de tests, la stratégie DevOps et la roadmap par phases.
# Sentinel_Ops_2026
