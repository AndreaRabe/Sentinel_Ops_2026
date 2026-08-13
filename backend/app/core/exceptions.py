"""Exceptions metier custom, mappees vers des reponses HTTP coherentes."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class NotFoundError(Exception):
    def __init__(self, message: str = "Ressource introuvable."):
        self.message = message


class ConflictError(Exception):
    def __init__(self, message: str = "Conflit avec l'etat actuel de la ressource."):
        self.message = message


class InvalidCredentialsError(Exception):
    def __init__(self, message: str = "Identifiants invalides."):
        self.message = message


class PasswordPolicyError(Exception):
    def __init__(self, message: str = "Le mot de passe ne respecte pas la politique de securite."):
        self.message = message


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def handle_not_found(_: Request, exc: NotFoundError):
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "NOT_FOUND", "message": exc.message}},
        )

    @app.exception_handler(ConflictError)
    async def handle_conflict(_: Request, exc: ConflictError):
        return JSONResponse(
            status_code=409,
            content={"error": {"code": "CONFLICT", "message": exc.message}},
        )

    @app.exception_handler(InvalidCredentialsError)
    async def handle_invalid_credentials(_: Request, exc: InvalidCredentialsError):
        return JSONResponse(
            status_code=401,
            content={"error": {"code": "INVALID_CREDENTIALS", "message": exc.message}},
        )

    @app.exception_handler(PasswordPolicyError)
    async def handle_password_policy(_: Request, exc: PasswordPolicyError):
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "PASSWORD_POLICY", "message": exc.message}},
        )
