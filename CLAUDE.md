# Sentinel Ops — contexte projet

Plateforme de gestion d'equipe securite (taches, planning, incidents, audit).
Toutes les decisions de conception detaillees sont dans `sentinel-ops-cahier-des-charges.md` — le lire avant toute modification structurante (schema DB, RBAC, architecture).

## Contexte non negociable

- 5-15 utilisateurs, self-hosted sur reseau local (LAN), un seul developpeur. Ne jamais proposer de solution cloud/Kubernetes/microservices.
- Retention audit legale : 3 ans, contractuelle avec un client. La table `audit_logs` est **append-only** : ne jamais creer de route ou de code permettant UPDATE/DELETE dessus.
- Cloture d'une tache par un agent = pas de validation bloquante par un superieur (decide explicitement).
- Deploiement manuel maitrise — ne jamais mettre en place d'auto-deploiement declenche a distance. Docker/nginx font partie de l'architecture cible (voir cahier des charges) mais ne sont pas encore utilises : le projet tourne pour le moment en installation native (voir README).

## Stack

- Backend : FastAPI + Poetry + SQLAlchemy (async) + Alembic + Argon2id + APScheduler (pas de Celery/Redis broker).
- Frontend : React + Vite + TypeScript + Tailwind, TanStack Query (etat serveur) + Zustand (etat UI global uniquement).
- DB : PostgreSQL. Cache/rate-limit : Redis prevu dans l'architecture cible mais pas encore utilise (contexte pro strict de l'utilisateur) — le verrouillage brute-force du login qui en depend est donc actuellement desactive (voir README, section Securite).

## Conventions de code

- Backend : separation stricte `api/endpoints` (validation + permission) -> `services` (logique metier + appel audit explicite) -> `repositories` (acces donnees pur). Ne jamais faire de requete SQL directement dans un endpoint ou un service.
- Toute mutation de donnee sensible doit appeler `audit_service.log_action(...)` explicitement dans le service concerne.
- RBAC : verifier via `require_permission("resource:action")`. Le scope multi-site est une verification ABAC ciblee en plus du RBAC, a faire dans le service (comparer le site de l'utilisateur au site de la ressource), jamais suppose.
- Frontend : formulaires en react-hook-form + zod. Etat serveur toujours via React Query, jamais stocke dans Zustand.
- Identite visuelle : theme "Command Center" — Manrope + IBM Plex Mono (donnees uniquement : KPI, horodatages, IDs), tokens de couleur dans `frontend/src/styles/tokens.css`, dashboard editorial (hairlines, pas de cartes empilees).

## Roadmap actuelle

Voir **section 14** du cahier des charges pour le detail des phases et les ecarts assumes.

Les phases 1 a 12 sont faites : auth/RBAC, administration, taches, incidents, dashboard, planning, notifications, rapports/exports, audit, jobs planifies, l'ensemble des ecrans frontend, et le durcissement (verrouillage brute-force, tests d'integration, specs E2E).

Prochaine etape : **Phase 13 — mise en production** (Docker Compose + nginx TLS, sauvegardes hors machine).

Deux points restent a arbitrer par l'utilisateur, ne pas trancher seul :
- **Entite « equipes »** : le perimetre V1 la mentionne, le modele de donnees de la section 4 ne la comporte pas. Couverte aujourd'hui par sites + role chef_equipe.
- **Docker / nginx** : documentes comme cible mais retires de l'outillage actif (voir git log). Ne pas les reintroduire sans demande explicite.

## Tests

- `make test` : unitaires backend (aucune base requise, `tests/conftest.py` pose les variables d'environnement) + vitest frontend.
- Tests d'integration : marques `@pytest.mark.integration`, sautes sans `TEST_DATABASE_URL`. Le plus important est `tests/integration/test_site_isolation.py` (etancheite multi-site).
- E2E Playwright dans `frontend/e2e/` : exigent une pile reelle, lances a la main via `npm run test:e2e`. **Jamais executes a ce jour.**

## Points d'attention specifiques

- **Machine a etats des taches** : `backend/app/core/task_state.py`, module pur et intégralement teste. Toute evolution du cycle de vie passe par la, jamais par une condition ad hoc dans un service.
- **Scope multi-site** : predicats purs dans `backend/app/core/scope.py`, resolution des sites dans `backend/app/services/scope_service.py`. Tout service manipulant une ressource rattachee a un site doit appeler `scope_service.assert_site_allowed(...)` explicitement.
- **APScheduler suppose UN SEUL processus backend.** Lancer uvicorn avec plusieurs workers dupliquerait les taches recurrentes : dans ce cas, mettre `SCHEDULER_ENABLED=false` sur tous les workers sauf un.
- **Pieces jointes** : stockees sur disque (`ATTACHMENTS_DIR`), metadonnees en base. Les deux doivent etre sauvegardes ensemble.
- **Moteur SQLAlchemy paresseux** (`app/db/session.py`) : cree au premier acces, pas a l'import. Ne pas revenir a une creation a l'import — cela imposerait d'installer asyncpg pour lancer le moindre test unitaire.
- **Verrouillage brute-force** : compteur lu dans `audit_logs`, pas de Redis. La verification precede toute comparaison de mot de passe, y compris pour un email inconnu.

## Commandes utiles

```bash
make install   # poetry install + npm install
make dev       # backend (uvicorn --reload) + frontend (Vite) en parallele, sans Docker
make test      # tests backend (pytest) + frontend (vitest)
make migrate   # alembic upgrade head
make seed      # bootstrap du compte Super Admin si base vierge
```
