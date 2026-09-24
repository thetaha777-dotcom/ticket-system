from pydantic import BaseModel, EmailStr


class Attendee(BaseModel):
    name: str
    email: EmailStr
    active_orders: list #probably will need to
    active_tickets: list #change the type from list

class Organizer(BaseModel):
    name: str
    email: EmailStr
    active_events: list

class EventAdmin(BaseModel):
    name: str
    email: EmailStr
    assigned_events: list

class PlatformAdmin(BaseModel):
    name: str
    email: EmailStr