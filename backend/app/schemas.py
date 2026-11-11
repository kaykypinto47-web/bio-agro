from datetime import date, datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=160)
    password: str


class UserOut(ORM):
    id: int
    name: str
    email: str
    role: str
    active: bool


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    role: Literal["admin", "operador", "motorista"] = "operador"


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ProducerIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    province: str = Field(min_length=2, max_length=80)
    district: str | None = Field(default=None, max_length=80)


class ProducerOut(ORM, ProducerIn):
    id: int


class ProductIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    category: str | None = None
    unit: str = "kg"


class ProductOut(ORM, ProductIn):
    id: int


class LotIn(BaseModel):
    producer_id: int
    product_id: int
    quantity: float = Field(gt=0)
    harvest_date: date
    origin: str | None = Field(default=None, max_length=160)


class LotOut(ORM):
    id: int
    code: str
    quantity: float
    harvest_date: date
    origin: str | None
    status: str
    producer: ProducerOut
    product: ProductOut


class DeliveryIn(BaseModel):
    lot_id: int
    destination: str = Field(min_length=2, max_length=200)
    driver_id: int | None = None
    notes: str | None = Field(default=None, max_length=500)


class EventOut(ORM):
    status: str
    note: str | None
    created_at: datetime


class DeliveryOut(ORM):
    id: int
    code: str
    destination: str
    status: str
    notes: str | None
    receiver_name: str | None
    confirmation_method: str | None
    created_at: datetime
    confirmed_at: datetime | None
    lot: LotOut
    driver: UserOut | None
    events: list[EventOut]


class DeliveryCreated(DeliveryOut):
    # O código só é mostrado UMA vez, na criação (guardamos apenas o hash).
    confirmation_code: str


class StatusIn(BaseModel):
    status: Literal["em_transito", "cancelada"]
    note: str | None = Field(default=None, max_length=300)


class ConfirmIn(BaseModel):
    code: str = Field(min_length=6, max_length=6)
    receiver_name: str = Field(min_length=2, max_length=120)


class AuditOut(ORM):
    id: int
    user_id: int | None
    action: str
    entity: str
    entity_id: int | None
    detail: str | None
    created_at: datetime


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    role: Literal["admin", "operador", "motorista"] | None = None
    active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=100)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=100)
