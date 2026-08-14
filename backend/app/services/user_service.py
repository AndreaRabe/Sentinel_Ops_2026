"""Regles metier de gestion des comptes utilisateurs (module Administration).

Deux garde-fous propres a ce service, en plus du RBAC :
- personne ne peut attribuer un role a portee plus large que le sien
  (un Responsable ne fabrique pas de Super Admin) ;
- un role a portee limitee (chef d'equipe, agent) doit avoir au moins un site,
  sinon son perimetre serait vide et il ne verrait rien.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import scope
from app.core.exceptions import BusinessRuleError, ConflictError, ForbiddenError, NotFoundError
from app.core.security import generate_temporary_password, hash_password
from app.models.site import Site
from app.models.user import User
from app.repositories import (
    refresh_token_repository,
    role_repository,
    site_repository,
    user_repository,
)
from app.schemas.common import Pagination
from app.services import audit_service, scope_service


async def _resolve_role(db: AsyncSession, actor: User, role_name: str):
    role = await role_repository.get_by_name(db, role_name)
    if role is None:
        raise NotFoundError(f"Role inconnu : {role_name}.")
    if scope.has_global_scope(role.name) and actor.role.name != "super_admin":
        raise ForbiddenError("Seul un Super Admin peut attribuer un role a portee globale.")
    return role


async def _validate_sites(
    db: AsyncSession, actor: User, role_name: str, site_ids: list[uuid.UUID]
) -> set[uuid.UUID]:
    unique_ids = set(site_ids)

    if scope.has_global_scope(role_name):
        # Portee globale : l'affectation site n'a pas de sens et serait
        # trompeuse a l'ecran. On la refuse explicitement plutot que de
        # l'ignorer silencieusement.
        if unique_ids:
            raise BusinessRuleError(
                "Un role a portee globale couvre tous les sites : ne lui en affectez aucun."
            )
        return set()

    if not unique_ids:
        raise BusinessRuleError("Ce role exige au moins un site d'affectation.")

    for site_id in unique_ids:
        if await site_repository.get_by_id(db, site_id) is None:
            raise NotFoundError(f"Site introuvable : {site_id}.")

    # Un chef d'equipe ne peut pas affecter quelqu'un a un site qu'il ne couvre pas.
    await scope_service.assert_sites_allowed(db, actor, unique_ids)
    return unique_ids


async def _sites_of(db: AsyncSession, user: User) -> list[Site]:
    site_ids = await site_repository.get_site_ids_for_user(db, user.id)
    if not site_ids:
        return []
    return await site_repository.list_all(db, site_ids=site_ids, include_inactive=True)


async def list_users(
    db: AsyncSession,
    actor: User,
    pagination: Pagination,
    *,
    role_name: str | None = None,
    query_text: str | None = None,
    include_inactive: bool = True,
) -> tuple[list[tuple[User, list[Site]]], int]:
    site_ids = await scope_service.visible_site_ids(db, actor)
    users, total = await user_repository.search(
        db,
        pagination,
        site_ids=site_ids,
        role_name=role_name,
        query_text=query_text,
        include_inactive=include_inactive,
    )
    return [(user, await _sites_of(db, user)) for user in users], total


async def get_user(db: AsyncSession, actor: User, user_id: uuid.UUID) -> tuple[User, list[Site]]:
    user = await user_repository.get_alive_by_id(db, user_id)
    if user is None:
        raise NotFoundError("Utilisateur introuvable.")

    sites = await _sites_of(db, user)
    if not scope.has_global_scope(actor.role.name) and actor.id != user.id:
        actor_sites = await scope_service.get_user_site_ids(db, actor)
        if not actor_sites & {site.id for site in sites}:
            raise ForbiddenError("Cet utilisateur n'appartient pas a vos sites.")
    return user, sites


async def create_user(
    db: AsyncSession,
    actor: User,
    *,
    first_name: str,
    last_name: str,
    email: str,
    role_name: str,
    site_ids: list[uuid.UUID],
    ip_address: str | None,
) -> tuple[User, list[Site], str]:
    email = email.lower().strip()
    if await user_repository.get_by_email(db, email) is not None:
        raise ConflictError("Un compte utilise deja cette adresse email.")

    role = await _resolve_role(db, actor, role_name)
    resolved_sites = await _validate_sites(db, actor, role.name, site_ids)

    temporary_password = generate_temporary_password()
    user = await user_repository.create(
        db,
        first_name=first_name,
        last_name=last_name,
        email=email,
        password_hash=hash_password(temporary_password),
        role_id=role.id,
    )
    await site_repository.set_sites_for_user(db, user.id, resolved_sites)

    await audit_service.log_action(
        db,
        actor_user_id=actor.id,
        action="user.created",
        resource_type="user",
        resource_id=str(user.id),
        details={"email": email, "role": role.name, "sites": [str(s) for s in resolved_sites]},
        ip_address=ip_address,
    )
    await db.commit()
    return user, await _sites_of(db, user), temporary_password


async def update_user(
    db: AsyncSession,
    actor: User,
    user_id: uuid.UUID,
    *,
    first_name: str | None,
    last_name: str | None,
    email: str | None,
    role_name: str | None,
    site_ids: list[uuid.UUID] | None,
    ip_address: str | None,
) -> tuple[User, list[Site]]:
    user, _ = await get_user(db, actor, user_id)

    changes: dict = {}
    if email:
        email = email.lower().strip()
        existing = await user_repository.get_by_email(db, email)
        if existing is not None and existing.id != user.id:
            raise ConflictError("Un compte utilise deja cette adresse email.")
        if email != user.email:
            changes["email"] = email
    if first_name and first_name != user.first_name:
        changes["first_name"] = first_name
    if last_name and last_name != user.last_name:
        changes["last_name"] = last_name

    target_role_name = user.role.name
    if role_name and role_name != user.role.name:
        # Changer le role de quelqu'un implique de pouvoir attribuer l'ancien
        # comme le nouveau : sinon un chef d'equipe pourrait "degrader" un
        # responsable pour reprendre la main dessus.
        await _resolve_role(db, actor, user.role.name)
        role = await _resolve_role(db, actor, role_name)
        changes["role_id"] = role.id
        target_role_name = role.name

    if changes:
        await user_repository.update_fields(db, user, **changes)

    site_changed = False
    if site_ids is not None or "role_id" in changes:
        # Un changement de role peut invalider l'affectation site existante
        # (portee globale <-> portee limitee) : on revalide dans les deux cas.
        requested = (
            site_ids if site_ids is not None else [site.id for site in await _sites_of(db, user)]
        )
        resolved_sites = await _validate_sites(db, actor, target_role_name, requested)
        await site_repository.set_sites_for_user(db, user.id, resolved_sites)
        site_changed = True

    if not changes and not site_changed:
        return user, await _sites_of(db, user)

    await audit_service.log_action(
        db,
        actor_user_id=actor.id,
        action="user.updated",
        resource_type="user",
        resource_id=str(user.id),
        details={
            **{k: str(v) for k, v in changes.items()},
            **({"sites_updated": True} if site_changed else {}),
        },
        ip_address=ip_address,
    )
    await db.commit()
    await db.refresh(user, ["role"])
    return user, await _sites_of(db, user)


async def set_activation(
    db: AsyncSession,
    actor: User,
    user_id: uuid.UUID,
    is_active: bool,
    ip_address: str | None,
) -> User:
    user, _ = await get_user(db, actor, user_id)
    if user.id == actor.id:
        raise BusinessRuleError("Vous ne pouvez pas desactiver votre propre compte.")
    await _resolve_role(db, actor, user.role.name)

    await user_repository.set_active(db, user, is_active)
    if not is_active:
        # Desactiver sans revoquer laisserait la session en cours vivante
        # jusqu'a expiration du refresh token (30 jours par defaut).
        await refresh_token_repository.revoke_all_for_user(db, user.id)

    await audit_service.log_action(
        db,
        actor_user_id=actor.id,
        action="user.activated" if is_active else "user.deactivated",
        resource_type="user",
        resource_id=str(user.id),
        ip_address=ip_address,
    )
    await db.commit()
    return user


async def reset_password(
    db: AsyncSession, actor: User, user_id: uuid.UUID, ip_address: str | None
) -> str:
    """Reinitialisation par un administrateur.

    V1 volontairement sans envoi d'email (les notifications email sont en V2,
    cahier des charges section 2) : le mot de passe temporaire est affiche une
    fois a l'administrateur, qui le transmet a l'utilisateur hors application.
    """
    user, _ = await get_user(db, actor, user_id)
    await _resolve_role(db, actor, user.role.name)

    temporary_password = generate_temporary_password()
    await user_repository.force_password_reset(db, user, hash_password(temporary_password))
    await refresh_token_repository.revoke_all_for_user(db, user.id)

    await audit_service.log_action(
        db,
        actor_user_id=actor.id,
        action="user.password_reset",
        resource_type="user",
        resource_id=str(user.id),
        ip_address=ip_address,
    )
    await db.commit()
    return temporary_password
