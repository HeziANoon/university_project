from fastapi import FastAPI, Request, Depends, HTTPException, Form, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import random
import shutil
import os

from database import get_db, engine, Base
import models

app = FastAPI(title="АИС ОхотУчёт")

# Подключение статических файлов (CSS, JS, загруженные фото)
os.makedirs("static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# 1. ГЛАВНАЯ СТРАНИЦА (Дашборд)
@app.get("/")
async def get_dashboard_page(request: Request, db: AsyncSession = Depends(get_db)):
    total_harvested_res = await db.execute(select(func.sum(models.Quota.current)))
    total_harvested = total_harvested_res.scalar() or 0

    total_limit_res = await db.execute(select(func.sum(models.Quota.total)))
    total_limit = total_limit_res.scalar() or 1

    active_perm_res = await db.execute(
        select(func.count(models.Permission.id))
        .where(models.Permission.status == "Активно")
    )
    active_permissions_count = active_perm_res.scalar() or 0

    quotas_result = await db.execute(select(models.Quota).order_by(models.Quota.id))
    quotas = quotas_result.scalars().all()

    events_result = await db.execute(
        select(models.HarvestEvent)
        .order_by(models.HarvestEvent.timestamp.desc())
        .limit(5)
    )
    recent_events = events_result.scalars().all()

    stats = {
        "total_harvested": total_harvested,
        "total_limit": total_limit,
        "active_permissions": active_permissions_count,
        "progress_percent": round((total_harvested / total_limit) * 100, 1),
        "quotas": quotas,
        "events": recent_events
    }

    return templates.TemplateResponse(
        request, "dashboard.html", context={"request": request, "stats": stats}
    )

# 2. КАРТА (ГИС)
@app.get("/map")
async def get_map_page(request: Request):
    return templates.TemplateResponse(request, "map.html", context={"request": request})

# 3. РАЗРЕШЕНИЯ (Реестр)
@app.get("/permissions")
async def get_permissions_page(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Permission).order_by(models.Permission.id.desc()))
    permissions = result.scalars().all()
    return templates.TemplateResponse(
        request, "permissions.html", context={"request": request, "permissions": permissions}
    )

# API: Выдача разрешения (Исправлено: 303 Redirect и передача даты)
@app.post("/permissions/issue")
async def issue_permission(
    hunter_fio: str = Form(...),
    animal_type: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    generated_number = f"РЗР-2026-{random.randint(1000, 9999)}"
    current_date = datetime.now().strftime("%Y-%m-%d")

    new_permission = models.Permission(
        number=generated_number,
        fio=hunter_fio,
        animal=animal_type,
        date=current_date,
        status="Активно"
    )
    db.add(new_permission)
    await db.commit()
    
    # 303 See Other форсирует GET-запрос браузера на /permissions
    return RedirectResponse(url="/permissions", status_code=303)

# API: Аннулирование разрешения
@app.post("/api/permissions/{number}/revoke")
async def revoke_permission(number: str, db: AsyncSession = Depends(get_db)):
    query = (
        update(models.Permission)
        .where(models.Permission.number == number)
        .values(status="Завершено")
    )
    result = await db.execute(query)
    await db.commit()
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Разрешение не найдено")
    return {"success": True, "message": f"Разрешение {number} аннулировано"}

# 4. ОХОТНИКИ
@app.get("/hunters")
async def get_hunters_page(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(
            models.Permission.fio.label("hunter_fio"), 
            func.count(models.Permission.id).label("total_permits")
        )
        .group_by(models.Permission.fio)
    )
    hunters = result.all()
    return templates.TemplateResponse(
        request, "hunters.html", context={"request": request, "hunters": hunters}
    )

# 5. ОТЧЕТЫ
@app.get("/reports")
async def get_reports_page(request: Request, db: AsyncSession = Depends(get_db)):
    quotas_result = await db.execute(select(models.Quota))
    quotas = quotas_result.scalars().all()
    
    report_data = {
        "labels": [q.animal_type for q in quotas],
        "current": [q.current for q in quotas],
        "total": [q.total for q in quotas]
    }
    return templates.TemplateResponse(
        request, "reports.html", context={"request": request, "report_data": report_data}
    )