from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel, EmailStr, Field


class OrderBase(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=100, example="John Doe")
    customer_email: EmailStr = Field(..., example="john@example.com")
    item_name: str = Field(..., min_length=1, max_length=100, example="Cloud Server Standard")
    quantity: int = Field(..., gt=0, example=2)
    unit_price: float = Field(..., gt=0, example=49.99)


class OrderCreate(OrderBase):
    pass


class OrderUpdate(BaseModel):
    status: Optional[str] = Field(None, example="processed")
    quantity: Optional[int] = Field(None, gt=0, example=3)


class OrderResponse(OrderBase):
    id: int
    total_price: float
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HealthStatus(BaseModel):
    status: str
    database: str
    redis: str
    timestamp: datetime


class AppInfo(BaseModel):
    app_name: str
    version: str
    environment: str
    hostname: str
    features: Dict[str, bool]
