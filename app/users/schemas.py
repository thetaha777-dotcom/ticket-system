from pydantic import BaseModel


class Attendee(BaseModel):
    name: str
    email: str
    active_orders: list #probably will need to
    active_tickets: list #change the type from list

class Organizer(BaseModel):
    name: str
    email: str
    active_events: list

class EventAdmin(BaseModel):
    name: str
    email: str
    assigned_events: list

class PlatformAdmin(BaseModel):
    name: str
    email: str