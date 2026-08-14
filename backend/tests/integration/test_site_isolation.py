"""Etancheite du scope multi-site, bout en bout sur une vraie base.

C'est le test le plus important du projet : une erreur ici est une fuite de
donnees entre sites. Les tests unitaires (tests/unit/test_scope.py) verifient
les predicats ; celui-ci verifie que les services les appellent VRAIMENT, sur
des donnees reelles.

Prerequis : une base de test migree (`make migrate` avec DATABASE_URL pointant
sur elle), puis TEST_DATABASE_URL renseigne. Sans cela le module est ignore.
"""

import uuid

import pytest

from app.core.exceptions import ForbiddenError
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.enums import IncidentSeverity, TaskPriority
from app.repositories import role_repository, site_repository
from app.schemas.common import Pagination
from app.services import incident_service, task_service
from tests.conftest import requires_database

pytestmark = [pytest.mark.integration, requires_database]

PAGE = Pagination(page=1, page_size=100)


async def _make_user(db, role_name: str, site_ids: set[uuid.UUID]):
    from app.models.user import User

    role = await role_repository.get_by_name(db, role_name)
    assert role is not None, f"Role {role_name} absent : migrations non appliquees ?"

    user = User(
        first_name="Test",
        last_name=role_name,
        email=f"{uuid.uuid4().hex}@test.local",
        password_hash=hash_password("MotDePasseDeTest!2026"),
        role_id=role.id,
        must_change_password=False,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user, ["role"])
    if site_ids:
        await site_repository.set_sites_for_user(db, user.id, site_ids)
    return user


@pytest.fixture
async def two_sites_fixture():
    """Deux sites, un chef d'equipe sur chacun, un responsable global."""
    async with SessionLocal() as db:
        site_a = await site_repository.create(db, f"Site A {uuid.uuid4().hex[:6]}")
        site_b = await site_repository.create(db, f"Site B {uuid.uuid4().hex[:6]}")

        chef_a = await _make_user(db, "chef_equipe", {site_a.id})
        chef_b = await _make_user(db, "chef_equipe", {site_b.id})
        responsable = await _make_user(db, "responsable", set())
        await db.commit()

        yield {
            "site_a": site_a,
            "site_b": site_b,
            "chef_a": chef_a,
            "chef_b": chef_b,
            "responsable": responsable,
        }


async def test_a_chef_cannot_create_a_task_on_another_site(two_sites_fixture):
    ctx = two_sites_fixture
    async with SessionLocal() as db:
        chef_a = await db.merge(ctx["chef_a"])
        with pytest.raises(ForbiddenError):
            await task_service.create_task(
                db,
                chef_a,
                title="Ronde sur un site interdit",
                description=None,
                site_id=ctx["site_b"].id,
                priority=TaskPriority.NORMAL,
                due_at=None,
                estimated_minutes=None,
                assignee_ids=[],
                checklist_labels=[],
                template_id=None,
                ip_address=None,
            )


async def test_a_chef_does_not_see_the_tasks_of_another_site(two_sites_fixture):
    ctx = two_sites_fixture
    async with SessionLocal() as db:
        chef_b = await db.merge(ctx["chef_b"])
        await task_service.create_task(
            db,
            chef_b,
            title="Tache confidentielle du site B",
            description=None,
            site_id=ctx["site_b"].id,
            priority=TaskPriority.NORMAL,
            due_at=None,
            estimated_minutes=None,
            assignee_ids=[],
            checklist_labels=[],
            template_id=None,
            ip_address=None,
        )

    async with SessionLocal() as db:
        chef_a = await db.merge(ctx["chef_a"])
        tasks, total = await task_service.list_tasks(db, chef_a, PAGE)
        titles = [task.title for task in tasks]
        assert "Tache confidentielle du site B" not in titles
        assert all(task.site_id == ctx["site_a"].id for task in tasks)


async def test_a_chef_cannot_open_a_task_of_another_site_by_its_id(two_sites_fixture):
    ctx = two_sites_fixture
    async with SessionLocal() as db:
        chef_b = await db.merge(ctx["chef_b"])
        task = await task_service.create_task(
            db,
            chef_b,
            title="Tache du site B",
            description=None,
            site_id=ctx["site_b"].id,
            priority=TaskPriority.NORMAL,
            due_at=None,
            estimated_minutes=None,
            assignee_ids=[],
            checklist_labels=[],
            template_id=None,
            ip_address=None,
        )

    # Connaitre l'identifiant ne doit rien ouvrir : c'est le scenario d'attaque
    # le plus simple (URL devinee ou partagee).
    async with SessionLocal() as db:
        chef_a = await db.merge(ctx["chef_a"])
        with pytest.raises(ForbiddenError):
            await task_service.get_task(db, chef_a, task.id)


async def test_the_responsable_sees_every_site(two_sites_fixture):
    ctx = two_sites_fixture
    async with SessionLocal() as db:
        chef_a = await db.merge(ctx["chef_a"])
        await task_service.create_task(
            db,
            chef_a,
            title="Tache du site A",
            description=None,
            site_id=ctx["site_a"].id,
            priority=TaskPriority.NORMAL,
            due_at=None,
            estimated_minutes=None,
            assignee_ids=[],
            checklist_labels=[],
            template_id=None,
            ip_address=None,
        )

    async with SessionLocal() as db:
        responsable = await db.merge(ctx["responsable"])
        _, total = await task_service.list_tasks(db, responsable, PAGE)
        site_ids = {
            task.site_id for task in (await task_service.list_tasks(db, responsable, PAGE))[0]
        }
        assert total >= 1
        # Vue centrale : aucun filtre site n'est applique.
        assert ctx["site_a"].id in site_ids


async def test_incidents_are_isolated_the_same_way(two_sites_fixture):
    ctx = two_sites_fixture
    async with SessionLocal() as db:
        chef_b = await db.merge(ctx["chef_b"])
        await incident_service.create_incident(
            db,
            chef_b,
            title="Intrusion site B",
            description="Detail confidentiel.",
            severity=IncidentSeverity.MAJOR,
            site_id=ctx["site_b"].id,
            occurred_at=None,
            ip_address=None,
        )

    async with SessionLocal() as db:
        chef_a = await db.merge(ctx["chef_a"])
        incidents, _ = await incident_service.list_incidents(db, chef_a, PAGE)
        assert all(incident.site_id == ctx["site_a"].id for incident in incidents)


async def test_a_chef_cannot_declare_an_incident_on_another_site(two_sites_fixture):
    ctx = two_sites_fixture
    async with SessionLocal() as db:
        chef_a = await db.merge(ctx["chef_a"])
        with pytest.raises(ForbiddenError):
            await incident_service.create_incident(
                db,
                chef_a,
                title="Incident hors perimetre",
                description="Ne doit pas etre accepte.",
                severity=IncidentSeverity.MINOR,
                site_id=ctx["site_b"].id,
                occurred_at=None,
                ip_address=None,
            )
