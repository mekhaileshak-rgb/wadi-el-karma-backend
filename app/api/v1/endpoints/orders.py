from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List
from app.db.database import get_db
from app.models.models import (
    Order, OrderItem, OrderStatusHistory, Cart, CartItem, Product,
    Address, Coupon, User, OrderStatus, PaymentMethod
)
from app.schemas.schemas import OrderCreate, OrderStatusUpdate, OrderOut
from app.api.v1.deps import get_current_user, get_current_admin
from datetime import datetime
import random
import string
import math

router = APIRouter(prefix="/orders", tags=["Orders"])


def _generate_order_number():
    return "WK-" + "".join(random.choices(string.digits, k=8))


def _load_order(db: Session):
    return db.query(Order).options(
        joinedload(Order.items),
        joinedload(Order.status_history),
    )


@router.post("", response_model=OrderOut, status_code=201)
def create_order(
    data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Validate address
    address = db.query(Address).filter(
        Address.id == data.address_id, Address.user_id == current_user.id
    ).first()
    if not address:
        raise HTTPException(status_code=404, detail="العنوان مش موجود")

    # Get cart
    cart = db.query(Cart).filter(Cart.user_id == current_user.id).first()
    if not cart:
        raise HTTPException(status_code=400, detail="الكارت فاضي")

    cart_items = db.query(CartItem).options(joinedload(CartItem.product)).filter(
        CartItem.cart_id == cart.id
    ).all()
    if not cart_items:
        raise HTTPException(status_code=400, detail="الكارت فاضي")

    # Calculate totals
    subtotal = 0.0
    order_items_data = []
    for item in cart_items:
        product = item.product
        if not product.is_active or product.stock_quantity < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"المنتج '{product.name}' مش متاح بالكمية دي"
            )
        price = product.effective_price
        total = price * item.quantity
        subtotal += total
        order_items_data.append({
            "product": product,
            "quantity": item.quantity,
            "unit_price": price,
            "total_price": total,
        })

    # Coupon discount
    discount = 0.0
    coupon_code = None
    if cart.coupon_id:
        coupon = db.query(Coupon).filter(Coupon.id == cart.coupon_id).first()
        if coupon and coupon.is_active and subtotal >= coupon.min_order_amount:
            coupon_code = coupon.code
            if coupon.discount_type == "percentage":
                discount = subtotal * (coupon.discount_value / 100)
            else:
                discount = min(coupon.discount_value, subtotal)
            coupon.used_count += 1

    shipping_cost = 50.0 if subtotal < 500 else 0.0  # Free shipping over 500 EGP
    total = subtotal - discount + shipping_cost

    # Create order
    order = Order(
        order_number=_generate_order_number(),
        user_id=current_user.id,
        payment_method=data.payment_method,
        subtotal=round(subtotal, 2),
        shipping_cost=shipping_cost,
        discount_amount=round(discount, 2),
        total=round(total, 2),
        coupon_code=coupon_code,
        notes=data.notes,
        shipping_full_name=address.full_name,
        shipping_phone=address.phone,
        shipping_street=address.street,
        shipping_city=address.city,
        shipping_governorate=address.governorate,
        shipping_postal_code=address.postal_code,
    )
    db.add(order)
    db.flush()

    # Create order items & deduct stock
    for item_data in order_items_data:
        order_item = OrderItem(
            order_id=order.id,
            product_id=item_data["product"].id,
            product_name=item_data["product"].name,
            product_sku=item_data["product"].sku,
            quantity=item_data["quantity"],
            unit_price=item_data["unit_price"],
            total_price=item_data["total_price"],
        )
        db.add(order_item)
        item_data["product"].stock_quantity -= item_data["quantity"]
        item_data["product"].sales_count += item_data["quantity"]

    # Initial status history
    db.add(OrderStatusHistory(order_id=order.id, status=OrderStatus.pending, note="تم إنشاء الطلب"))

    # Clear cart
    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
    cart.coupon_id = None

    db.commit()
    return _load_order(db).filter(Order.id == order.id).first()


@router.get("", response_model=dict)
def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    status: Optional[OrderStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = _load_order(db).filter(Order.user_id == current_user.id)
    if status:
        query = query.filter(Order.status == status)
    query = query.order_by(Order.created_at.desc())

    total = query.count()
    orders = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [OrderOut.model_validate(o) for o in orders],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size),
    }


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = _load_order(db).filter(
        Order.id == order_id, Order.user_id == current_user.id
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="الطلب مش موجود")
    return order


@router.post("/{order_id}/cancel", response_model=OrderOut)
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = db.query(Order).filter(
        Order.id == order_id, Order.user_id == current_user.id
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="الطلب مش موجود")
    if order.status not in [OrderStatus.pending, OrderStatus.confirmed]:
        raise HTTPException(status_code=400, detail="مش قادر تلغي الطلب في المرحلة دي")

    # Restore stock
    for item in order.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            product.stock_quantity += item.quantity
            product.sales_count -= item.quantity

    order.status = OrderStatus.cancelled
    db.add(OrderStatusHistory(order_id=order.id, status=OrderStatus.cancelled, note="تم إلغاء الطلب بواسطة العميل"))
    db.commit()
    return _load_order(db).filter(Order.id == order.id).first()
