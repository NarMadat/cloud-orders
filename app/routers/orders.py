import json
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db, redis_client
from app.models import Order
from app.schemas import OrderCreate, OrderUpdate, OrderResponse
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/orders", tags=["Orders"])

CACHE_KEY_ORDERS_LIST = "cache:orders:all"
CACHE_TTL_SECONDS = 60


def invalidate_orders_cache():
    if settings.REDIS_ENABLED and redis_client:
        try:
            redis_client.delete(CACHE_KEY_ORDERS_LIST)
        except Exception as e:
            logger.warning(f"Could not invalidate Redis cache: {e}")


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(order_in: OrderCreate, db: Session = Depends(get_db)):
    total = round(order_in.quantity * order_in.unit_price, 2)
    db_order = Order(
        customer_name=order_in.customer_name,
        customer_email=order_in.customer_email,
        item_name=order_in.item_name,
        quantity=order_in.quantity,
        unit_price=order_in.unit_price,
        total_price=total,
        status="pending"
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    invalidate_orders_cache()
    return db_order


@router.get("", response_model=List[OrderResponse])
def list_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    # Try reading from Redis cache if requesting first page
    if skip == 0 and limit == 20 and settings.REDIS_ENABLED and redis_client:
        try:
            cached = redis_client.get(CACHE_KEY_ORDERS_LIST)
            if cached:
                orders_data = json.loads(cached)
                return orders_data
        except Exception as e:
            logger.warning(f"Failed to read orders from Redis cache: {e}")

    orders = db.query(Order).offset(skip).limit(limit).all()

    # Cache first page
    if skip == 0 and limit == 20 and settings.REDIS_ENABLED and redis_client:
        try:
            serialized = [
                OrderResponse.model_validate(o).model_dump(mode="json")
                for o in orders
            ]
            redis_client.setex(CACHE_KEY_ORDERS_LIST, CACHE_TTL_SECONDS, json.dumps(serialized))
        except Exception as e:
            logger.warning(f"Failed to set Redis cache: {e}")

    return orders


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with ID {order_id} not found"
        )
    return order


@router.patch("/{order_id}", response_model=OrderResponse)
def update_order(order_id: int, order_in: OrderUpdate, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with ID {order_id} not found"
        )

    if order_in.status is not None:
        order.status = order_in.status
    if order_in.quantity is not None:
        order.quantity = order_in.quantity
        order.total_price = round(order.quantity * order.unit_price, 2)

    db.commit()
    db.refresh(order)
    invalidate_orders_cache()
    return order


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with ID {order_id} not found"
        )

    db.delete(order)
    db.commit()
    invalidate_orders_cache()
    return None
