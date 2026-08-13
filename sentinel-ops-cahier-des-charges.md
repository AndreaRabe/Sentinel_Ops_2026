# Sentinel Ops — Cahier des charges & architecture

Plateforme de gestion d'équipe sécurité — récapitulatif des décisions validées.

---

## 1. Contexte du projet

| Point | Décision |
|---|---|
| Équipe | 5-15 personnes |
| Hiérarchie | Responsable → Chef d'équipe → Agent |
| Sites | Multi-site, vue centrale obligatoire |
| Usage | Production réelle |
| Déploiement | Self-hosted, réseau local (LAN), un seul développeur |
| Rétention audit | 3 ans, exigence contractuelle client |

---

## 2. Périmètre fonctionnel

### V1 (à développer maintenant)
- Authentification (login, logout, reset mot de passe, sessions, mot de passe temporaire forcé au premier login)
- RBAC : rôles, permissions, scope par site
- Gestion des tâches : création, assignation multiple, statuts, priorité, échéance, récurrence complexe (RRULE), templates réutilisables, commentaires, pièces jointes, checklist, dépendances, historique
- Vues Kanban et Backlog (vues sur les mêmes données tâches)
- Calendrier/planning simple (affichage, sans rotations/gardes)
- Gestion des équipes, sites, agents (chef d'équipe multi-site possible)
- Module incidents complet (gravité, résolution, pièces jointes, historique d'actions)
- Dashboard (tâches du jour, en retard, urgentes, charge de travail)
- Notifications in-app
- Rapports + exports PDF/Excel, filtrage jour/semaine/mois
- Audit complet, append-only, conservation 3 ans

### V2 (backlog)
- MFA
- Rotations/gardes, gestion des congés/absences
- Notifications email (et éventuellement SMS)
- Rôle auditeur séparé (si exigé par un client)
- Intégrations externes (LDAP, SSO, calendrier externe)

---

## 3. Rôles & RBAC

| Rôle | Portée | Capacités clés |
|---|---|---|
| Super Admin | Global | Système, rôles, utilisateurs, paramètres |
| Responsable | Tous les sites | Vue centrale, gestion agents/chefs d'équipe, tous les rapports et audits |
| Chef d'équipe | Un ou plusieurs sites | Création/assignation de tâches, planning, incidents de ses sites |
| Agent | Ses tâches assignées | Exécution, déclaration d'incident, clôture sans validation bloquante |

RBAC pur partout, sauf un point ABAC nécessaire : le scope par site (comparaison site de l'utilisateur / site de la ressource).

---

## 4. Modèle de données — entités principales

**Identité & accès** : `users` (avec `must_change_password`, `password_changed_at`, `mfa_enabled` réservé), `roles`, `permissions`, `role_permissions`, `sites`, `user_sites`, `refresh_tokens`, `password_history`

**Tâches** : `task_templates` (récurrence RRULE nullable = usage manuel ou automatique), `tasks` (soft delete), `task_assignments` (many-to-many), `task_comments`, `task_attachments`, `task_checklist_items`, `task_dependencies`

**Incidents** : `incidents`, `incident_actions`, `incident_attachments`

**Système** : `notifications`, `system_settings`, `audit_logs` (append-only, insert-only au niveau privilèges DB)

Soft delete partout sur les entités sensibles à l'audit (users, tasks, incidents, sites).

### Machine à états d'une tâche
```
DRAFT → ASSIGNED → IN_PROGRESS → COMPLETED
                  ↘ POSTPONED
                  ↘ CANCELLED (à tout moment avant COMPLETED)
         → LATE (automatique si due_at dépassé, statut ≠ COMPLETED/CANCELLED)
```
Clôture par l'agent sans validation bloquante (décidé).

---

## 5. Architecture technique globale

```
Client (React+Vite+TS+Tailwind)
        │ HTTPS (certificat auto-signé, LAN)
     Nginx (reverse proxy, TLS)
        │
   Backend FastAPI (monolithe modulaire)
        │
 PostgreSQL ── Redis (cache, rate limiting) ── APScheduler (récurrence, retards, exports)
        │
  Stockage fichiers (volume Docker local)
```

**Tâches asynchrones** : APScheduler intégré (pas de Celery/Redis broker séparé — trop lourd à opérer seul pour 5 utilisateurs en LAN).

**Auth** : JWT access token (15 min, mémoire client) + refresh token opaque (cookie httpOnly/Secure/SameSite=Strict, stocké hashé en DB).

---

## 6. Stack technique

| Couche | Choix | Justification courte |
|---|---|---|
| Frontend | React + Vite + TypeScript + Tailwind | SPA suffisant (pas de SSR requis), Vite rapide, TS indispensable vu la complexité du domaine |
| Backend | FastAPI + Poetry | Typage Pydantic, doc OpenAPI auto, async natif |
| Base de données | PostgreSQL | Intégrité stricte, JSON natif pour l'audit, contraintes avancées |
| Cache/rate limit | Redis | Léger, utile même sans broker de tâches |
| Async/planification | APScheduler | Simplicité d'exploitation pour un dev solo |
| Infra | Docker Compose, Nginx | Pas de Kubernetes — disproportionné pour cette échelle |
| Tests | Pytest, Vitest, Playwright | Couverture ciblée sur la criticité |
| CI | GitHub Actions | Lint + tests avant fusion, déploiement manuel |

---

## 7. Sécurité

- Hash mots de passe : Argon2id, longueur min 12, vérification robustesse (zxcvbn), historique anti-réutilisation
- Verrouillage brute-force : 5 tentatives / 15 min via Redis, loggé en audit
- RBAC appliqué via dependency FastAPI (`require_permission`), scope site en complément (ABAC ciblé)
- Protections XSS (échappement React + CSP), CSRF (cookie SameSite=Strict), injection SQL (ORM paramétré), CORS restreint à l'origine du frontend
- Secrets via `.env` non versionné, clé JWT 256 bits
- HTTPS avec certificat auto-signé (contexte LAN), HSTS volontairement limité/désactivé pour ce contexte

---

## 8. API — conventions

- Base `/api/v1/...`, JSON, pagination `page`/`page_size`, erreurs standardisées, documentation OpenAPI auto-générée
- Endpoints détaillés par module : Auth, Administration (users/roles/sites/teams), Tâches, Incidents, Notifications, Rapports, Audit (lecture seule stricte, aucune route d'écriture exposée)

---

## 9. Architecture backend (FastAPI)

Séparation stricte : `api/endpoints` (validation + permissions) → `services` (règles métier + appel explicite à l'audit) → `repositories` (accès données pur) → PostgreSQL.

Structure : `core/`, `db/`, `models/`, `schemas/`, `repositories/`, `services/`, `api/v1/`, `middleware/`, `jobs/`, `tests/` — plus Alembic (migrations), Poetry (dépendances), Makefile (commandes), script de seed (premier compte Super Admin), endpoint `/health`.

---

## 10. Architecture frontend (React)

- État serveur : TanStack Query (cache, invalidation, mises à jour optimistes)
- État UI global : Zustand (session, thème, sidebar)
- Formulaires : react-hook-form + Zod
- Routing protégé par permission (`<ProtectedRoute>`, `<Can>`), redirection forcée si `must_change_password`
- Structure : `pages/`, `features/` (découpage par domaine métier), `components/ui`, `components/layout`, `lib/`

---

## 11. Direction UX/UI — "Sentinel Ops / Command Center"

Identité validée à partir d'un brief de design haute-fidélité :
- Typographie : Manrope (UI) + IBM Plex Mono (données : KPI, horodatages, IDs)
- Palette OKLCH theme-aware (dark/light), couleurs sémantiques (primary rouge, success, warning, danger, info) toujours couleur + texte, jamais couleur seule
- Dashboard éditorial sans cartes empilées — hairlines, gros chiffres tabulaires animés (count-up)
- Écrans validés en mockup : Login (split-screen brandé), Dashboard, Tâches (Liste + Kanban avec changement de statut live), Drawer de création de tâche
- Animations de chargement contextuelles : effet "scan" pour le chargement de listes/pages, "pulse dots" pour les actions inline, "progress ring" pour les opérations longues (exports)

---

## 12. Tests

Couverture quasi-totale ciblée sur : machine à états des tâches, RBAC par rôle, scope multi-site, immutabilité de l'audit, politique de mot de passe, gestion des tokens JWT.
Backend : unitaires (services mockés) + intégration (DB de test) + matrice de permissions par rôle.
Frontend : composants (Vitest+RTL) + E2E (Playwright) sur les parcours critiques.

---

## 13. DevOps

- Git trunk-based simplifié, PR même en solo, CI qui bloque la fusion si tests critiques échouent
- Docker Compose : nginx, frontend, backend, migrate (job unique), postgres, redis
- Déploiement manuel maîtrisé (`git pull` + `make migrate` + `docker compose up -d --build`) — pas d'auto-déploiement sur la machine personnelle
- Sauvegardes : `pg_dump` quotidien + **copie hors machine indispensable** (point de vigilance : single point of failure sur une seule machine, à ne pas négliger vu l'engagement de rétention 3 ans)
- Monitoring proportionné : healthchecks Docker, endpoint `/health`, logs JSON avec rotation — pas de Prometheus/Grafana à cette échelle

---

## 14. Ce qu'il reste à faire

- Roadmap détaillée par phases avec jalons
- Setup initial du dépôt (structure des dossiers, Poetry, Docker Compose, CI de base)
- Implémentation progressive module par module, en commençant par Auth + RBAC (fondation de tout le reste)
- Écrans restants à designer : Planning/Calendrier, Incidents, Équipe/Agents, Rapports, Audit, Paramètres, Administration
