"""Primitives partagees par tous les modules : pagination, reponses generiques.

Convention d'API : pagination par `page`/`page_size` (cahier des charges
section 8).
"""

from math import ceil
from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field

T = TypeVar("T")

MAX_PAGE_SIZE = 200


class Pagination(BaseModel):
    page: int = 1
    page_size: int = 25

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def pagination_params(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=MAX_PAGE_SIZE),
) -> Pagination:
    return Pagination(page=page, page_size=page_size)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def build(cls, items: list[T], total: int, pagination: Pagination) -> "Page[T]":
        return cls(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            pages=ceil(total / pagination.page_size) if pagination.page_size else 0,
        )


class MessageResponse(BaseModel):
    message: str


class TemporaryPasswordResponse(BaseModel):
    """Mot de passe temporaire affiche UNE seule fois a l'ecran de l'administrateur.

    Jamais renvoye ailleurs, jamais journalise en clair : la valeur n'existe
    en clair que dans cette reponse HTTP.
    """

    temporary_password: str = Field(description="A transmettre a l'utilisateur hors application.")
