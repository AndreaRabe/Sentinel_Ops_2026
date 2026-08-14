"""Immutabilite du journal d'audit.

L'engagement contractuel de retention (3 ans, section 1 du cahier des charges)
ne vaut que si rien ne peut effacer ou reecrire une entree. Trois barrieres
existent, et ces tests verifient les deux premieres (la troisieme est le
trigger PostgreSQL, verifie par le test d'integration correspondant) :

1. aucune permission d'ecriture sur l'audit (voir test_rbac_matrix) ;
2. aucune fonction d'UPDATE/DELETE dans le code d'acces aux donnees ;
3. un trigger PostgreSQL qui refuse UPDATE/DELETE quel que soit le role.
"""

import inspect
import re

from app.api.v1.endpoints import audit as audit_endpoints
from app.repositories import audit_repository
from app.services import audit_service

WRITE_PATTERNS = (
    re.compile(r"\bupdate\s*\(", re.IGNORECASE),
    re.compile(r"\bdelete\s*\(", re.IGNORECASE),
)


def _source(module) -> str:
    return inspect.getsource(module)


def _public_functions(module) -> set[str]:
    """Fonctions DEFINIES par le module, hors symboles importes (select, func...)."""
    return {
        name
        for name, value in vars(module).items()
        if inspect.isfunction(value)
        and not name.startswith("_")
        and value.__module__ == module.__name__
    }


def test_audit_repository_exposes_no_mutation_function():
    # Seules la creation et la lecture sont permises.
    assert _public_functions(audit_repository) == {
        "create",
        "search",
        "distinct_actions",
        "count_failed_logins",
    }


def test_audit_repository_contains_no_update_or_delete_statement():
    source = _source(audit_repository)
    for pattern in WRITE_PATTERNS:
        assert not pattern.search(source), f"Instruction interdite trouvee : {pattern.pattern}"


def test_audit_service_exposes_no_mutation_function():
    assert _public_functions(audit_service) == {
        "log_action",
        "search",
        "list_actions",
        "count_failed_logins",
    }


def test_audit_endpoints_are_read_only():
    """Aucune route POST/PUT/PATCH/DELETE ne doit exister sur /audit."""
    methods = {
        method
        for route in audit_endpoints.router.routes
        for method in getattr(route, "methods", set())
    }
    assert methods <= {"GET", "HEAD", "OPTIONS"}, f"Routes d'ecriture exposees : {methods}"
