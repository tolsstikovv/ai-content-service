import asyncio
from pathlib import Path

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.main as main_module
from app.models import Base


@pytest.fixture()
def test_engine_and_session(tmp_path: Path):
    db_file = tmp_path / "test.db"
    database_url = f"sqlite+aiosqlite:///{db_file}"

    engine = create_async_engine(database_url, echo=False)
    test_session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def init_models():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init_models())
    return engine, test_session_factory


@pytest.fixture()
def app_with_test_db(test_engine_and_session):
    engine, test_session_factory = test_engine_and_session

    async def override_get_session():
        async with test_session_factory() as session:
            yield session

    main_module.app.dependency_overrides[main_module.get_session] = override_get_session

    original_hash = main_module.pwd_context.hash
    original_verify = main_module.pwd_context.verify
    main_module.pwd_context.hash = lambda password: f"hash::{password}"
    main_module.pwd_context.verify = lambda password, hashed: hashed == f"hash::{password}"

    yield main_module.app

    main_module.pwd_context.hash = original_hash
    main_module.pwd_context.verify = original_verify
    main_module.app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def test_auth_and_projects_smoke(app_with_test_db):
    async def scenario():
        transport = httpx.ASGITransport(app=app_with_test_db)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            unauth = await client.get("/projects")
            assert unauth.status_code == 401

            register = await client.post(
                "/register",
                data={"email": "smoke@example.com", "password": "secret123"},
                follow_redirects=False,
            )
            assert register.status_code == 303

            login = await client.post(
                "/login",
                data={"email": "smoke@example.com", "password": "secret123"},
                follow_redirects=False,
            )
            assert login.status_code == 303

            add_project = await client.post(
                "/projects/add",
                data={
                    "name": "Smoke Project",
                    "description": "basic project",
                    "enable_telegram": "true",
                    "enable_vk": "true",
                },
                follow_redirects=False,
            )
            assert add_project.status_code == 303

            projects = await client.get("/projects")
            assert projects.status_code == 200
            assert "Smoke Project" in projects.text

    asyncio.run(scenario())


def test_content_and_pipeline_smoke(app_with_test_db, monkeypatch: pytest.MonkeyPatch):
    async def scenario():
        transport = httpx.ASGITransport(app=app_with_test_db)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post(
                "/register",
                data={"email": "content@example.com", "password": "secret123"},
                follow_redirects=False,
            )
            await client.post(
                "/login",
                data={"email": "content@example.com", "password": "secret123"},
                follow_redirects=False,
            )

            await client.post(
                "/projects/add",
                data={"name": "Content Project", "description": "desc"},
                follow_redirects=False,
            )

            project_id = 1
            add_content = await client.post(
                f"/projects/{project_id}/content/add",
                data={"title": "My title", "image_style": "realistic", "image_count": "2"},
                follow_redirects=False,
            )
            assert add_content.status_code == 303

            content_list = await client.get(f"/projects/{project_id}/content")
            assert content_list.status_code == 200
            assert "My title" in content_list.text

            called = {}

            def fake_delay(**kwargs):
                called.update(kwargs)

            monkeypatch.setattr(main_module.celery_full_pipeline, "delay", fake_delay)

            content_id = 1
            run_pipeline = await client.post(f"/content/{content_id}/run_pipeline")
            assert run_pipeline.status_code == 200
            assert run_pipeline.json()["message"] == "Pipeline запущен"
            assert called == {"content_item_id": content_id}

    asyncio.run(scenario())
