from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from typing import Optional, List
from datetime import datetime, timedelta
from app.db.database import get_db
from app.models.models import (
    User, Product, Order, OrderStatus, OrderStatusHistory,
    Coupon, Review, UserRole, PaymentStatus
)
from app.schemas.schemas import (
    DashboardStats, OrderOut, OrderStatusUpdate,
    UserOut, CouponCreate, CouponOut, ReviewOut
)
from app.api.v1.deps import get_current_admin
import math

router = APIRouter(prefix="/admin", tags=["Admin"])


# ─── Dashboard ───────────────────────────────────────────
@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())

    total_revenue = db.query(func.sum(Order.total)).filter(
        Order.payment_status == PaymentStatus.paid
    ).scalar() or 0.0

    revenue_today = db.query(func.sum(Order.total)).filter(
        Order.payment_status == PaymentStatus.paid,
        Order.created_at >= today_start
    ).scalar() or 0.0

    return DashboardStats(
        total_revenue=total_revenue,
        total_orders=db.query(Order).count(),
        total_customers=db.query(User).filter(User.role == UserRole.customer).count(),
        total_products=db.query(Product).filter(Product.is_active == True).count(),
        pending_orders=db.query(Order).filter(Order.status == OrderStatus.pending).count(),
        low_stock_products=db.query(Product).filter(
            Product.stock_quantity <= Product.low_stock_threshold,
            Product.is_active == True
        ).count(),
        revenue_today=revenue_today,
        orders_today=db.query(Order).filter(Order.created_at >= today_start).count(),
    )


@router.get("/dashboard/revenue-chart")
def revenue_chart(
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    start_date = datetime.utcnow() - timedelta(days=days)
    results = db.query(
        func.date(Order.created_at).label("date"),
        func.sum(Order.total).label("revenue"),
        func.count(Order.id).label("orders"),
    ).filter(
        Order.created_at >= start_date,
        Order.payment_status == PaymentStatus.paid
    ).group_by(func.date(Order.created_at)).all()

    return [{"date": str(r.date), "revenue": r.revenue or 0, "orders": r.orders} for r in results]


@router.get("/dashboard/top-products")
def top_products(
    limit: int = 10,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    products = db.query(Product).options(
        joinedload(Product.images)
    ).order_by(desc(Product.sales_count)).limit(limit).all()
    return [{"id": p.id, "name": p.name, "sales_count": p.sales_count, "price": p.price} for p in products]


# ─── Orders Management ───────────────────────────────────
@router.get("/orders", response_model=dict)
def admin_list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[OrderStatus] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    query = db.query(Order).options(joinedload(Order.items)).order_by(Order.created_at.desc())

    if status:
        query = query.filter(Order.status == status)
    if search:
        query = query.filter(Order.order_number.ilike(f"%{search}%"))

    total = query.count()
    orders = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [OrderOut.model_validate(o) for o in orders],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size),
    }


@router.put("/orders/{order_id}/status", response_model=OrderOut)
def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    order = db.query(Order).options(
        joinedload(Order.items), joinedload(Order.status_history)
    ).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="الطلب مش موجود")

    order.status = data.status
    if data.tracking_number:
        order.tracking_number = data.tracking_number

    db.add(OrderStatusHistory(
        order_id=order.id,
        status=data.status,
        note=data.note,
    ))
    db.commit()
    db.refresh(order)
    return order


# ─── Users Management ────────────────────────────────────
@router.get("/users", response_model=dict)
def admin_list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[UserRole] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    query = db.query(User)
    if search:
        query = query.filter(
            User.email.ilike(f"%{search}%") | User.full_name.ilike(f"%{search}%")
        )
    if role:
        query = query.filter(User.role == role)

    total = query.count()
    users = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [UserOut.model_validate(u) for u in users],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size),
    }


@router.put("/users/{user_id}/toggle-status")
def toggle_user_status(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم مش موجود")
    user.is_active = not user.is_active
    db.commit()
    return {"user_id": user_id, "is_active": user.is_active}


@router.put("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    role: UserRole,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم مش موجود")
    user.role = role
    db.commit()
    return {"user_id": user_id, "role": role}


# ─── Coupons Management ──────────────────────────────────
@router.get("/coupons", response_model=List[CouponOut])
def list_coupons(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    return db.query(Coupon).order_by(Coupon.created_at.desc()).all()


@router.post("/coupons", response_model=CouponOut, status_code=201)
def create_coupon(
    data: CouponCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    if db.query(Coupon).filter(Coupon.code == data.code.upper()).first():
        raise HTTPException(status_code=400, detail="الكود ده موجود خلاص")
    coupon = Coupon(**data.model_dump(), code=data.code.upper())
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return coupon


@router.delete("/coupons/{coupon_id}", status_code=204)
def delete_coupon(
    coupon_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise HTTPException(status_code=404, detail="الكوبون مش موجود")
    db.delete(coupon)
    db.commit()


# ─── Reviews Management ──────────────────────────────────
@router.get("/reviews", response_model=dict)
def admin_list_reviews(
    page: int = Query(1, ge=1),
    page_size: int = Query(20),
    approved: Optional[bool] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    query = db.query(Review).options(joinedload(Review.user))
    if approved is not None:
        query = query.filter(Review.is_approved == approved)
    total = query.count()
    reviews = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [ReviewOut.model_validate(r) for r in reviews],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size),
    }


@router.put("/reviews/{review_id}/approve")
def approve_review(
    review_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="الريفيو مش موجود")
    review.is_approved = True
    db.commit()
    return {"message": "تم اعتماد الريفيو"}


@router.delete("/reviews/{review_id}", status_code=204)
def delete_review(
    review_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="الريفيو مش موجود")
    db.delete(review)
    db.commit()
