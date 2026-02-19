from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from passlib.context import CryptContext
from app.db.session import async_session_factory
from app.models import User, Project, ContentItem, ErrorLog
from worker.celery_app import celery_full_pipeline

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
app = FastAPI()
templates = Jinja2Templates(directory="app/templates")


# ---------------------------
# Dependencies
# ---------------------------
async def get_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session


async def get_current_user(request: Request, session: AsyncSession = Depends(get_session)) -> User:
    email = request.cookies.get("user_email")
    if not email:
        raise HTTPException(status_code=401, detail="Не авторизован")
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")
    return user


# ---------------------------
# Auth
# ---------------------------
@app.get("/register")
async def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register")
async def register(request: Request, email: str = Form(...), password: str = Form(...), session: AsyncSession = Depends(get_session)):
    hashed = pwd_context.hash(password)
    new_user = User(email=email, hashed_password=hashed)
    session.add(new_user)
    await session.commit()
    return RedirectResponse("/login", status_code=303)


@app.get("/login")
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not pwd_context.verify(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Неверные данные"})
    response = RedirectResponse("/projects", status_code=303)
    response.set_cookie(key="user_email", value=user.email)
    return response


@app.get("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("user_email")
    return response


# ---------------------------
# Projects
# ---------------------------
@app.get("/projects")
async def projects(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse("projects.html", {"request": request, "projects": user.projects})


@app.get("/projects/add")
async def add_project_form(request: Request):
    return templates.TemplateResponse("add_project.html", {"request": request})


@app.post("/projects/add")
async def add_project(
    name: str = Form(...),
    description: str = Form(""),
    enable_telegram: bool = Form(True),
    enable_vk: bool = Form(True),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    project = Project(
        name=name,
        description=description,
        owner=user,
        enable_telegram=enable_telegram,
        enable_vk=enable_vk,
    )
    session.add(project)
    await session.commit()
    return RedirectResponse("/projects", status_code=303)


@app.get("/projects/{project_id}/edit")
async def edit_project_form(request: Request, project_id: int, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Project).where(Project.id == project_id, Project.user_id == user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")
    return templates.TemplateResponse("add_project.html", {"request": request, "project": project})


@app.post("/projects/{project_id}/edit")
async def edit_project(project_id: int, name: str = Form(...), description: str = Form(""),
                       enable_telegram: bool = Form(True), enable_vk: bool = Form(True),
                       user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    await session.execute(
        update(Project)
        .where(Project.id == project_id, Project.user_id == user.id)
        .values(name=name, description=description, enable_telegram=enable_telegram, enable_vk=enable_vk)
    )
    await session.commit()
    return RedirectResponse("/projects", status_code=303)


@app.post("/projects/{project_id}/delete")
async def delete_project(project_id: int, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    await session.execute(delete(Project).where(Project.id == project_id, Project.user_id == user.id))
    await session.commit()
    return RedirectResponse("/projects", status_code=303)


# ---------------------------
# Content Items
# ---------------------------
@app.get("/projects/{project_id}/content")
async def project_content(request: Request, project_id: int, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Project).where(Project.id == project_id, Project.user_id == user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")
    return templates.TemplateResponse("content_list.html", {"request": request, "project": project, "content_items": project.content_items})


@app.get("/projects/{project_id}/content/add")
async def add_content_form(request: Request, project_id: int):
    return templates.TemplateResponse("add_content.html", {"request": request, "project_id": project_id})


@app.post("/projects/{project_id}/content/add")
async def add_content(project_id: int, title: str = Form(...), image_style: str = Form(...), image_count: int = Form(1),
                      session: AsyncSession = Depends(get_session)):
    content_item = ContentItem(project_id=project_id, title=title, image_style=image_style, image_count=image_count, status="draft")
    session.add(content_item)
    await session.commit()
    return RedirectResponse(f"/projects/{project_id}/content", status_code=303)


@app.get("/content/{content_id}/edit")
async def edit_content_form(request: Request, content_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(ContentItem).where(ContentItem.id == content_id))
    content = result.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="Контент не найден")
    return templates.TemplateResponse("add_content.html", {"request": request, "project_id": content.project_id, "content": content})


@app.post("/content/{content_id}/edit")
async def edit_content(content_id: int, title: str = Form(...), image_style: str = Form(...), image_count: int = Form(1),
                       session: AsyncSession = Depends(get_session)):
    await session.execute(
        update(ContentItem)
        .where(ContentItem.id == content_id)
        .values(title=title, image_style=image_style, image_count=image_count)
    )
    await session.commit()
    result = await session.execute(select(ContentItem).where(ContentItem.id == content_id))
    content = result.scalar_one()
    return RedirectResponse(f"/projects/{content.project_id}/content", status_code=303)


@app.post("/content/{content_id}/delete")
async def delete_content(content_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(ContentItem).where(ContentItem.id == content_id))
    content = result.scalar_one_or_none()
    if content:
        await session.execute(delete(ContentItem).where(ContentItem.id == content_id))
        await session.commit()
        return RedirectResponse(f"/projects/{content.project_id}/content", status_code=303)
    raise HTTPException(status_code=404, detail="Контент не найден")


# ---------------------------
# QA Logs
# ---------------------------
@app.get("/content/{content_id}/qa_logs")
async def qa_logs(request: Request, content_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(ContentItem).where(ContentItem.id == content_id))
    content = result.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="Контент не найден")
    result_logs = await session.execute(select(ErrorLog).where(ErrorLog.content_item_id == content_id))
    logs = result_logs.scalars().all()
    return templates.TemplateResponse("qa_logs.html", {"request": request, "content_item": content, "logs": logs})


# ---------------------------
# Run pipeline manually
# ---------------------------
@app.post("/content/{content_id}/run_pipeline")
async def run_pipeline(content_id: int):
    celery_full_pipeline.delay(content_item_id=content_id)
    return {"message": "Pipeline запущен"}
