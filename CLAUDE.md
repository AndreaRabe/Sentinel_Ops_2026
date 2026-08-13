# Sentinel Ops — contexte projet

Plateforme de gestion d'equipe securite (taches, planning, incidents, audit).
Toutes les decisions de conception detaillees sont dans `sentinel-ops-cahier-des-charges.md` — le lire avant toute modification structurante (schema DB, RBAC, architecture).

## Contexte non negociable

- 5-15 utilisateurs, self-hosted sur reseau local (LAN), un seul developpeur. Ne jamais proposer de solution cloud/Kubernetes/microservices.
- Retention audit legale : 3 ans, contractuelle avec un client. La table `audit_logs` est **append-only** : ne jamais creer de route ou de code permettant UPDATE/DELETE dessus.
- Cloture d'une tache par un agent = pas de validation bloquante par un superieur (decide explicitement).
- Deploiement manuel maitrise (`git pull` + `make migrate` + `docker compose up -d --build`) — ne jamais mettre en place d'auto-deploiement declenche a distance.

## Stack

- Backend : FastAPI + Poetry + SQLAlchemy (async) + Alembic + Argon2id + APScheduler (pas de Celery/Redis broker).
- Frontend : React + Vite + TypeScript + Tailwind, TanStack Query (etat serveur) + Zustand (etat UI global uniquement).
- DB : PostgreSQL. Cache/rate-limit : Redis.

## Conventions de code

- Backend : separation stricte `api/endpoints` (validation + permission) -> `services` (logique metier + appel audit explicite) -> `repositories` (acces donnees pur). Ne jamais faire de requete SQL directement dans un endpoint ou un service.
- Toute mutation de donnee sensible doit appeler `audit_service.log_action(...)` explicitement dans le service concerne.
- RBAC : verifier via `require_permission("resource:action")`. Le scope multi-site est une verification ABAC ciblee en plus du RBAC, a faire dans le service (comparer le site de l'utilisateur au site de la ressource), jamais suppose.
- Frontend : formulaires en react-hook-form + zod. Etat serveur toujours via React Query, jamais stocke dans Zustand.
- Identite visuelle : theme "Command Center" — Manrope + IBM Plex Mono (donnees uniquement : KPI, horodatages, IDs), tokens de couleur dans `frontend/src/styles/tokens.css`, dashboard editorial (hairlines, pas de cartes empilees).

## Roadmap actuelle

Voir section 13 du cahier des charges pour le detail des phases. Prochaine etape : Phase 5 — Auth & RBAC (fondation dont dependent tous les autres modules). Ne pas developper de module metier avant que l'authentification et les permissions soient completes et testees.

## Commandes utiles

```bash
make install   # poetry install + npm install
make dev       # environnement de developpement complet (docker compose dev)
make test      # tests backend (pytest) + frontend (vitest)
make migrate   # alembic upgrade head
make seed      # bootstrap du compte Super Admin si base vierge
```
