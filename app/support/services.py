import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.audit.services import record
from app.core.database import utcnow
from app.events.models import Event, StaffAssignment
from app.notifications.services import notify
from app.orders.models import Order
from app.shared.exceptions import AppError, Forbidden, NotFound
from app.shared.utils import random_code
from app.support.models import CaseKind, CaseStatus, SupportCase, SupportMessage
from app.support.schemas import CaseContext, CaseCreate, CaseDetail, CaseOut, CaseUpdate, MessageOut
from app.tickets.models import Ticket
from app.users.models import User, UserRole
from app.users.schemas import UserBrief

STATUS_LABEL = {
    CaseStatus.OPEN: "Open", CaseStatus.IN_PROGRESS: "In Progress",
    CaseStatus.WAITING_FOR_CUSTOMER: "Waiting for Customer", CaseStatus.RESOLVED: "Resolved",
}


def _case_query():
    return select(SupportCase).options(
        selectinload(SupportCase.messages).joinedload(SupportMessage.author),
        joinedload(SupportCase.requester), joinedload(SupportCase.assigned_to),
        joinedload(SupportCase.event), joinedload(SupportCase.order), joinedload(SupportCase.ticket),
    )


def _is_event_team(db: Session, user: User, event_id: uuid.UUID | None) -> bool:
    if event_id is None:
        return False
    event = db.get(Event, event_id)
    if event and event.organizer_id == user.id:
        return True
    return db.scalar(select(StaffAssignment.id).where(
        StaffAssignment.event_id == event_id, StaffAssignment.user_id == user.id)) is not None


def _roles(db: Session, user: User, case: SupportCase) -> tuple[bool, bool]:
    is_admin = user.role == UserRole.PLATFORM_ADMIN
    if case.kind == CaseKind.ORGANIZER:
        staff = is_admin
    else:
        staff = _is_event_team(db, user, case.event_id) or (is_admin and case.is_escalated)
    return (staff or case.requester_id == user.id), staff


def _platform_admins(db: Session) -> list[User]:
    return list(db.scalars(select(User).where(User.role == UserRole.PLATFORM_ADMIN, User.is_active.is_(True))))


def _staff_recipients(db: Session, case: SupportCase) -> list[User]:
    if case.assigned_to_id:
        return [db.get(User, case.assigned_to_id)]
    if case.kind == CaseKind.ORGANIZER:
        return _platform_admins(db)
    recipients = [db.get(User, case.event.organizer_id)] if case.event else []
    if case.is_escalated:
        recipients += _platform_admins(db)
    return recipients


def _resolve_context(db: Session, user: User, data: CaseCreate) -> tuple[uuid.UUID | None, uuid.UUID | None, uuid.UUID | None]:
    event_id, order_id, ticket_id = data.event_id, data.order_id, data.ticket_id
    if ticket_id:
        ticket = db.get(Ticket, ticket_id)
        if ticket is None:
            raise NotFound("Ticket not found", "ticket_not_found")
        order_id, event_id = ticket.order_id, ticket.event_id
    if order_id:
        order = db.get(Order, order_id)
        if order is None:
            raise NotFound("Order not found", "order_not_found")
        if order.user_id != user.id and not _is_event_team(db, user, order.event_id):
            raise Forbidden("This order belongs to another account", "not_your_order")
        event_id = order.event_id
    if event_id and db.get(Event, event_id) is None:
        raise NotFound("Event not found", "event_not_found")
    return event_id, order_id, ticket_id


def create_case(db: Session, user: User, data: CaseCreate) -> SupportCase:
    event_id, order_id, ticket_id = _resolve_context(db, user, data)
    if data.kind == CaseKind.ATTENDEE and event_id is None:
        raise AppError("Open the request from an event, order or ticket page", "context_required")
    if data.kind == CaseKind.ORGANIZER and user.role not in (UserRole.ORGANIZER, UserRole.PLATFORM_ADMIN):
        raise Forbidden("Only organizers can write to platform support", "insufficient_role")
    case = SupportCase(
        number=f"SC-{random_code(6)}", kind=data.kind, category=data.category, subject=data.subject.strip(),
        requester_id=user.id, event_id=event_id, order_id=order_id, ticket_id=ticket_id,
        messages=[SupportMessage(author_id=user.id, body=data.message.strip())],
    )
    db.add(case)
    db.flush()
    record(db, actor=user, action="support.opened", entity_type="support_case", entity_id=case.id, event_id=event_id,
           description=f"Support case {case.number} opened: {case.subject}")
    case = get_case_unchecked(db, case.id)
    for person in _staff_recipients(db, case):
        notify(db, person, "support_message", f"New support request {case.number}",
               f"{user.name} wrote: {data.message.strip()[:500]}", link=f"/support/{case.id}")
    db.commit()
    return case


def get_case_unchecked(db: Session, case_id: uuid.UUID) -> SupportCase:
    case = db.scalar(_case_query().where(SupportCase.id == case_id).execution_options(populate_existing=True))
    if case is None:
        raise NotFound("Support case not found", "case_not_found")
    return case


def get_case(db: Session, case_id: uuid.UUID, user: User) -> SupportCase:
    case = get_case_unchecked(db, case_id)
    if not _roles(db, user, case)[0]:
        raise Forbidden("You do not have access to this support case", "case_forbidden")
    return case


def list_cases(db: Session, user: User, scope: str = "mine", status: CaseStatus | None = None,
               event_id: uuid.UUID | None = None) -> list[SupportCase]:
    query = _case_query().order_by(SupportCase.updated_at.desc())
    if scope == "managed":
        mine = select(Event.id).where(Event.organizer_id == user.id)
        assigned = select(StaffAssignment.event_id).where(StaffAssignment.user_id == user.id)
        query = query.where(SupportCase.kind == CaseKind.ATTENDEE,
                            or_(SupportCase.event_id.in_(mine), SupportCase.event_id.in_(assigned)))
    elif scope == "platform":
        if user.role != UserRole.PLATFORM_ADMIN:
            raise Forbidden("Only platform administrators can see this queue", "insufficient_role")
        query = query.where(or_(SupportCase.kind == CaseKind.ORGANIZER, SupportCase.is_escalated.is_(True)))
    else:
        query = query.where(SupportCase.requester_id == user.id)
    if status:
        query = query.where(SupportCase.status == status)
    if event_id:
        query = query.where(SupportCase.event_id == event_id)
    return list(db.scalars(query))


def _set_status(db: Session, case: SupportCase, actor: User, status: CaseStatus) -> None:
    if case.status == status:
        return
    old, case.status = case.status, status
    record(db, actor=actor, action="support.status_changed", entity_type="support_case", entity_id=case.id,
           event_id=case.event_id, description=f"Support case {case.number}: {STATUS_LABEL[old]} → {STATUS_LABEL[status]}")
    if actor.id != case.requester_id:
        notify(db, case.requester, "support_status", f"Support request {case.number}: {STATUS_LABEL[status]}",
               f"The status of «{case.subject}» changed to {STATUS_LABEL[status]}.", link=f"/support/{case.id}")


def add_message(db: Session, case: SupportCase, user: User, body: str) -> SupportCase:
    _, is_staff = _roles(db, user, case)
    case.messages.append(SupportMessage(author_id=user.id, body=body.strip()))
    case.updated_at = utcnow()
    if is_staff and user.id != case.requester_id:
        if case.status == CaseStatus.OPEN:
            _set_status(db, case, user, CaseStatus.IN_PROGRESS)
        notify(db, case.requester, "support_message", f"New reply in support request {case.number}",
               f"{user.name} replied: {body.strip()[:500]}", link=f"/support/{case.id}")
    else:
        if case.status in (CaseStatus.WAITING_FOR_CUSTOMER, CaseStatus.RESOLVED):
            _set_status(db, case, user, CaseStatus.IN_PROGRESS)
        for person in _staff_recipients(db, case):
            notify(db, person, "support_message", f"New message in support request {case.number}",
                   f"{user.name} wrote: {body.strip()[:500]}", link=f"/support/{case.id}")
    db.commit()
    return get_case_unchecked(db, case.id)


def update_case(db: Session, case: SupportCase, user: User, data: CaseUpdate) -> SupportCase:
    _, is_staff = _roles(db, user, case)
    changes = data.model_dump(exclude_unset=True)
    if changes.get("is_escalated") and not case.is_escalated:
        if case.kind != CaseKind.ATTENDEE:
            raise AppError("Organizer cases already go to platform support", "already_platform_case")
        case.is_escalated = True
        record(db, actor=user, action="support.escalated", entity_type="support_case", entity_id=case.id,
               event_id=case.event_id, description=f"Support case {case.number} escalated to platform support")
        for admin in _platform_admins(db):
            notify(db, admin, "support_assignment", f"Support request {case.number} was escalated",
                   f"«{case.subject}» needs platform support.", link=f"/support/{case.id}")
    if "status" in changes or "assigned_to_id" in changes:
        if not is_staff:
            raise Forbidden("Only the support side can change the status or the assignee", "case_forbidden")
        if changes.get("status"):
            _set_status(db, case, user, changes["status"])
        if "assigned_to_id" in changes and changes["assigned_to_id"] != case.assigned_to_id:
            assignee = db.get(User, changes["assigned_to_id"]) if changes["assigned_to_id"] else None
            if assignee is not None and not _roles(db, assignee, case)[1]:
                raise AppError("This person cannot handle the case", "invalid_assignee")
            case.assigned_to_id = assignee.id if assignee else None
            if assignee and assignee.id != user.id:
                notify(db, assignee, "support_assignment", f"Support request {case.number} was assigned to you",
                       f"«{case.subject}» from {case.requester.name}.", link=f"/support/{case.id}")
    case.updated_at = utcnow()
    db.commit()
    return get_case_unchecked(db, case.id)


def case_out(db: Session, case: SupportCase, viewer: User, detail: bool = False) -> CaseOut | CaseDetail:
    _, can_manage = _roles(db, viewer, case)
    context = CaseContext(
        event_id=case.event_id, event_title=case.event.title if case.event else None,
        event_slug=case.event.slug if case.event else None, order_id=case.order_id,
        order_number=case.order.number if case.order else None, ticket_id=case.ticket_id,
        ticket_code=case.ticket.code if case.ticket else None,
    )
    base = dict(
        id=case.id, number=case.number, kind=case.kind, category=case.category, subject=case.subject, status=case.status,
        is_escalated=case.is_escalated, requester=UserBrief.model_validate(case.requester),
        assigned_to=UserBrief.model_validate(case.assigned_to) if case.assigned_to else None, context=context,
        created_at=case.created_at, updated_at=case.updated_at, message_count=len(case.messages), can_manage=can_manage,
    )
    if not detail:
        return CaseOut(**base)
    messages = [MessageOut(
        id=m.id, author_id=m.author_id, author_name=m.author.name, from_staff=m.author_id != case.requester_id,
        is_mine=m.author_id == viewer.id, body=m.body, created_at=m.created_at) for m in case.messages]
    return CaseDetail(**base, messages=messages)
