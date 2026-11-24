import uuid

from pydantic import BaseModel, ConfigDict, Field


class VenueIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    city: str = Field(min_length=1, max_length=255)
    address: str = Field(min_length=1, max_length=255)
    capacity: int | None = Field(None, ge=1)
    use_predefined_layout: bool = Field(False, description="Attach the predefined concert-hall seat map to this venue")


class VenueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    city: str
    address: str
    capacity: int | None
    has_seat_map: bool


class SeatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    number: int
    is_accessible: bool


class RowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    label: str
    seats: list[SeatOut]


class SectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    price_category: str
    rows: list[RowOut]


class VenueLayoutOut(VenueOut):
    sections: list[SectionOut]
