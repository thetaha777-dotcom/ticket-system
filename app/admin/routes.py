import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.activation.schemas import SuspendIn
from app.activation.services import set_suspended
from app.admin import services
from app.admin.schemas import (
    ActivationRow,
    AdminEventPage,
    AdminOrderPage,
    Overview,
    PromoActivityRow,
    ReportRow,
    ReportUpdate,
    SettingsOut,
    SettingsUpdate,
    SuspendEventIn,
    UserAdminUpdate,
    UserPage,
)
from app.admin.settings import all_settings, update_settings
from app.audit.schemas import AuditLogOut
from app.audit.services import list_logs, record
from app.auth.dependencies import require_admin
from app.auth.schemas import Message
from app.core.database import get_db
from app.orders.models import OrderStatus, PaymentKind, PaymentStatus
from app.orders.schemas import PaymentOut, RefundOut
from app.users.models import User, UserRole
from app.users.schemas import UserOut

router = APIRouter(prefix="/admin", tags=["platform admin"], dependencies=[Depends(require_admin)])


@router.get("/overview", response_model=Overview)
def overview(db: Session = Depends(get_db)):
    return services.overview(db)


@router.get("/users", response_model=UserPage)
def users(q: str | None = None, role: UserRole | None = None, limit: int = Query(50, ge=1, le=200),
          offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    items, total = services.list_users(db, q, role, limit, offset)
    return UserPage(items=items, total=total)


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: uuid.UUID, data: UserAdminUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return services.update_user(db, admin, user_id, data)


@router.get("/events", response_model=AdminEventPage)
def events(q: str | None = None, suspended: bool | None = None, limit: int = Query(50, ge=1, le=200),
           offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    items, total = services.list_events(db, q, suspended, limit, offset)
    return AdminEventPage(items=items, total=total)


@router.post("/events/{event_id}/suspend", response_model=Message)
def suspend_event(event_id: uuid.UUID, data: SuspendEventIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    services.set_event_suspended(db, admin, event_id, data.reason)
    return Message(detail="Event suspended")


@router.post("/events/{event_id}/unsuspend", response_model=Message)
def unsuspend_event(event_id: uuid.UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    services.set_event_suspended(db, admin, event_id, None)
    return Message(detail="Event restored")


@router.get("/orders", response_model=AdminOrderPage)
def orders(q: str | None = None, status: OrderStatus | None = None, limit: int = Query(50, ge=1, le=200),
           offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    items, total = services.list_orders(db, q, status, limit, offset)
    return AdminOrderPage(items=items, total=total)


@router.get("/payments", response_model=list[PaymentOut])
def payments(q: str | None = None, status: PaymentStatus | None = None, kind: PaymentKind | None = None,
             limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    return services.list_payments(db, q, status, kind, limit, offset)


@router.get("/refunds", response_model=list[RefundOut])
def refunds(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    return services.list_refunds(db, limit, offset)


@router.get("/activations", response_model=list[ActivationRow])
def activations(db: Session = Depends(get_db)):
    return services.list_activations(db)


@router.post("/activations/{activation_id}/suspend", response_model=Message)
def suspend_activation(activation_id: uuid.UUID, data: SuspendIn, admin: User = Depends(require_admin),
                       db: Session = Depends(get_db)):
    set_suspended(db, activation_id, admin, data.reason)
    return Message(detail="Paid sales suspended")


@router.post("/activations/{activation_id}/reinstate", response_model=Message)
def reinstate_activation(activation_id: uuid.UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    set_suspended(db, activation_id, admin, None)
    return Message(detail="Paid sales reinstated")


@router.get("/reports", response_model=list[ReportRow])
def reports(status: str | None = Query(None, pattern="^(open|reviewed|dismissed)$"), db: Session = Depends(get_db)):
    return services.list_reports(db, status)


@router.patch("/reports/{report_id}", response_model=ReportRow)
def review_report(report_id: uuid.UUID, data: ReportUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return services.review_report(db, admin, report_id, data.status, data.resolution_note)


@router.get("/promo-activity", response_model=list[PromoActivityRow])
def promo_activity(db: Session = Depends(get_db)):
    return services.promo_activity(db)


@router.get("/audit-log", response_model=list[AuditLogOut])
def audit_log(event_id: uuid.UUID | None = None, action: str | None = None, limit: int = Query(200, ge=1, le=500),
              offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    return list_logs(db, event_id=event_id, action=action, limit=limit, offset=offset)


@router.get("/settings", response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db)):
    return all_settings(db)


@router.put("/settings", response_model=SettingsOut)
def put_settings(data: SettingsUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    values = update_settings(db, admin, data.model_dump(exclude_unset=True))
    record(db, actor=admin, action="settings.updated", entity_type="platform_settings", entity_id="platform",
           description=f"Platform settings changed: {data.model_dump(exclude_unset=True)}")
    db.commit()
    return values


@router.get("/export/{report}.csv")
def export(report: str, db: Session = Depends(get_db)):
    return Response(content=services.export_csv(db, report), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="biletflow-{report}.csv"'})
