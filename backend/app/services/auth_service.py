"""Service d'authentification (Phase 5) - regles metier + audit explicite.

Politique de mot de passe (zxcvbn + historique anti-reutilisation),
emission/rotation des tokens JWT + refresh token opaque hashe.

Le verrouillage brute-force (cahier des charges section 7) est implemente
SANS Redis : le compteur est une fenetre glissante lue dans `audit_logs`, ou
chaque echec est de toute facon deja journalise. A l'echelle du projet
(5-15 utilisateurs, LAN), une requete indexee sur 15 minutes de journal coute
moins cher a exploiter qu'un service supplementaire a installer et surveiller.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AccountLockedError,
    InvalidCredentialsError,
    PasswordPolicyError,
)
from app.core.security import (
    check_password_strength,
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.user import User
from app.repositories import (
    password_history_repository,
    refresh_token_repository,
    role_repository,
    user_repository,
)
from app.services import audit_service


async def _issue_tokens(db: AsyncSession, user: User) -> tuple[str, str]:
    permissions = await role_repository.get_permission_codes(db, user.role_id)
    access_token = create_access_token(str(user.id), user.role.name, permissions)
    refresh_token_plain = generate_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
    await refresh_token_repository.create(
        db, user.id, hash_refresh_token(refresh_token_plain), expires_at
    )
    return access_token, refresh_token_plain


async def _lockout_window_start(db: AsyncSession, user: User | None) -> datetime:
    """Debut de la fenetre de comptage des echecs.

    On repart de la derniere connexion reussie quand elle est plus recente que
    la fenetre : sinon des echecs anterieurs a une connexion legitime
    continueraient a compter et pourraient verrouiller un utilisateur qui
    vient pourtant de prouver qu'il connait son mot de passe.
    """
    window_start = datetime.now(timezone.utc) - timedelta(minutes=settings.login_lockout_minutes)
    if user is not None and user.last_login_at and user.last_login_at > window_start:
        return user.last_login_at
    return window_start


async def _assert_not_locked(
    db: AsyncSession, email: str, user: User | None, ip_address: str | None
) -> None:
    since = await _lockout_window_start(db, user)
    failures = await audit_service.count_failed_logins(db, email, since)
    if failures < settings.login_max_attempts:
        return

    # Le verrouillage lui-meme est journalise : c'est un evenement de securite
    # a part entiere, distinct d'un simple echec de mot de passe.
    await audit_service.log_action(
        db,
        actor_user_id=user.id if user else None,
        action="auth.login_blocked",
        resource_type="user",
        resource_id=email,
        details={"failed_attempts": failures},
        ip_address=ip_address,
    )
    await db.commit()
    raise AccountLockedError(
        f"Trop de tentatives echouees. Reessayez dans {settings.login_lockout_minutes} minutes."
    )


async def authenticate(
    db: AsyncSession, email: str, password: str, ip_address: str | None
) -> tuple[str, str, bool]:
    user = await user_repository.get_by_email(db, email)

    # Verifie AVANT toute comparaison de mot de passe : un compte verrouille ne
    # doit pas pouvoir etre teste, meme avec le bon mot de passe.
    await _assert_not_locked(db, email, user, ip_address)

    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        await audit_service.log_action(
            db,
            actor_user_id=user.id if user else None,
            action="auth.login_failed",
            resource_type="user",
            resource_id=email,
            ip_address=ip_address,
        )
        await db.commit()
        raise InvalidCredentialsError()

    access_token, refresh_token_plain = await _issue_tokens(db, user)
    await user_repository.update_last_login(db, user)
    await audit_service.log_action(
        db,
        actor_user_id=user.id,
        action="auth.login_success",
        resource_type="user",
        resource_id=str(user.id),
        ip_address=ip_address,
    )
    await db.commit()
    return access_token, refresh_token_plain, user.must_change_password


async def refresh(
    db: AsyncSession, refresh_token_plain: str, ip_address: str | None
) -> tuple[str, str, bool]:
    token_hash = hash_refresh_token(refresh_token_plain)
    token = await refresh_token_repository.get_valid_by_hash(db, token_hash)
    if token is None or token.expires_at < datetime.now(timezone.utc):
        raise InvalidCredentialsError("Session expiree, veuillez vous reconnecter.")

    user = await user_repository.get_by_id(db, token.user_id)
    if user is None or not user.is_active:
        raise InvalidCredentialsError()

    await refresh_token_repository.revoke(db, token)
    access_token, new_refresh_token_plain = await _issue_tokens(db, user)
    await audit_service.log_action(
        db,
        actor_user_id=user.id,
        action="auth.token_refreshed",
        resource_type="user",
        resource_id=str(user.id),
        ip_address=ip_address,
    )
    await db.commit()
    return access_token, new_refresh_token_plain, user.must_change_password


async def logout(db: AsyncSession, refresh_token_plain: str, ip_address: str | None) -> None:
    token_hash = hash_refresh_token(refresh_token_plain)
    token = await refresh_token_repository.get_valid_by_hash(db, token_hash)
    if token is None:
        return
    await refresh_token_repository.revoke(db, token)
    await audit_service.log_action(
        db,
        actor_user_id=token.user_id,
        action="auth.logout",
        resource_type="user",
        resource_id=str(token.user_id),
        ip_address=ip_address,
    )
    await db.commit()


async def change_password(
    db: AsyncSession,
    user: User,
    current_password: str,
    new_password: str,
    ip_address: str | None,
) -> None:
    if not verify_password(current_password, user.password_hash):
        raise InvalidCredentialsError("Mot de passe actuel incorrect.")

    errors = check_password_strength(new_password, [user.email, user.first_name, user.last_name])
    if errors:
        raise PasswordPolicyError(" ".join(errors))

    recent_hashes = await password_history_repository.get_recent_hashes(db, user.id)
    if any(verify_password(new_password, old_hash) for old_hash in recent_hashes):
        raise PasswordPolicyError("Ce mot de passe a deja ete utilise recemment.")

    await password_history_repository.add(db, user.id, user.password_hash)
    await user_repository.update_password(db, user, hash_password(new_password))
    await audit_service.log_action(
        db,
        actor_user_id=user.id,
        action="auth.password_changed",
        resource_type="user",
        resource_id=str(user.id),
        ip_address=ip_address,
    )
    await db.commit()
