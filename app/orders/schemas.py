from uuid import UUID, uuid4
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, PositiveInt
from typing import Optional


class Order(BaseModel):
    id: UUID = Field(default_factory=uuid4)
