"""Definition des permissions RBAC et dependency FastAPI pour les verifier.

Chaque permission suit la convention "ressource:action" (ex: "task:create").
Le scope par site (exception ABAC) est verifie separement au niveau du service
concerne, pas ici, car il depend de la ressource cible et pas seulement du role.

La liste des permissions accordees est calculee a l'authentification (voir
auth_service) a partir de la table role_permissions, puis embarquee dans le
JWT (claim "perms") : aucune requete DB n'est necessaire pour verifier une
permission a chaque appel.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user_payload(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        return decode_access_token(token)
    except Exception as exc:  # noqa: BLE001 - toute erreur JWT => 401
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session invalide ou expiree.",
        ) from exc


def require_permission(permission: str):
    def dependency(payload: dict = Depends(get_current_user_payload)) -> dict:
        allowed = set(payload.get("perms", []))
        if "*" not in allowed and permission not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission insuffisante pour cette action.",
            )
        return payload

    return dependency
