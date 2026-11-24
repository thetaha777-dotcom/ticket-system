import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import models as _models  # noqa: F401  (registers every table)
from app.activation.routes import router as activation_router
from app.admin.routes import router as admin_router
from app.analytics.routes import router as analytics_router
from app.auth.routes import router as auth_router
from app.checkin.routes import router as checkin_router
from app.core.config import settings
from app.core.database import SessionLocal
from app.events.routes import organizer_router as organizer_events_router
from app.events.routes import router as events_router
from app.orders.routes import organizer_router as organizer_orders_router
from app.orders.routes import router as orders_router
from app.orders.services import expire_stale_orders
from app.promos.routes import organizer_router as organizer_promos_router
from app.promos.routes import router as promos_router
from app.shared.exceptions import AppError
from app.shared.uploads import router as uploads_router
from app.support.routes import router as support_router
from app.tickets.routes import organizer_router as organizer_tickets_router
from app.tickets.routes import router as tickets_router
from app.users.routes import router as users_router
from app.venues.routes import router as venues_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("biletflow")


def _release_expired_reservations() -> int:
    with SessionLocal() as db:
        return expire_stale_orders(db)


async def _expiry_loop() -> None:
    while True:
        await asyncio.sleep(30)
        try:
            released = await asyncio.to_thread(_release_expired_reservations)
            if released:
                log.info("Released %s expired reservation(s)", released)
        except Exception:
            log.exception("Could not release expired reservations")


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(_expiry_loop())
    yield
    task.cancel()


app = FastAPI(
    title="BiletFlow API",
    version="1.0.0",
    description=(
        "Self-service event ticketing platform for Kazakhstan (academic MVP).\n\n"
        "**All payments, refunds, identity checks and payouts are simulations - no real money moves.**\n\n"
        "Sign in with `POST /api/v1/auth/login`, or use the **Authorize** button with an email and password."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail, "code": exc.code})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
    first = errors[0] if errors else {"field": "", "message": "Invalid request"}
    detail = f"{first['field']}: {first['message']}" if first["field"] else first["message"]
    return JSONResponse(status_code=422, content={"detail": detail, "code": "validation_error", "errors": errors})


api = APIRouter(prefix="/api/v1")
for router in (
    auth_router, users_router, venues_router, events_router, orders_router, tickets_router, promos_router,
    support_router, checkin_router,
    organizer_events_router, organizer_tickets_router, organizer_orders_router, activation_router,
    organizer_promos_router, analytics_router,
    admin_router, uploads_router,
):
    api.include_router(router)
app.include_router(api)

Path(settings.media_dir).mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.media_dir), name="media")


@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "environment": settings.environment}
