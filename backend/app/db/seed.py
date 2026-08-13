"""Bootstrap du premier compte Super Admin sur base vierge.

Idempotent : ne fait rien si un compte super_admin existe deja.
Le mot de passe temporaire genere est affiche UNE FOIS dans les logs,
jamais stocke en clair ni committe. must_change_password force son
changement des la premiere connexion.
"""

import asyncio
import secrets

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.role import Role
from app.models.user import User


async def seed_super_admin() -> None:
    async with SessionLocal() as session:
        super_admin_role = (
            await session.execute(select(Role).where(Role.name == "super_admin"))
        ).scalar_one_or_none()
        if super_admin_role is None:
            print("[seed] Role 'super_admin' introuvable - lancez 'make migrate' avant le seed.")
            return

        existing = await session.execute(select(User).where(User.role_id == super_admin_role.id))
        if existing.scalar_one_or_none() is not None:
            print("[seed] Un compte Super Admin existe deja - rien a faire.")
            return

        temp_password = secrets.token_urlsafe(12)
        admin = User(
            first_name="Super",
            last_name="Admin",
            email=settings.seed_admin_email,
            password_hash=hash_password(temp_password),
            role_id=super_admin_role.id,
            must_change_password=True,
        )
        session.add(admin)
        await session.commit()

        print("=" * 60)
        print("[seed] Compte Super Admin cree.")
        print(f"[seed] Email    : {settings.seed_admin_email}")
        print(f"[seed] Mot de passe temporaire : {temp_password}")
        print("[seed] A changer obligatoirement a la premiere connexion.")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(seed_super_admin())
