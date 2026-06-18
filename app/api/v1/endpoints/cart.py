from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.db.database import get_db
from app.models.models import Cart, CartItem, Product, Coupon, User
from app.schemas.schemas import CartItemAdd, CartItemUpdate, CartOut, CartItemOut, ApplyCouponRequest
from app.api.v1.deps import get_current_user
from datetime import datetime

router = APIRouter(prefix="/cart", tags=["Cart"])


def _get_or_create_cart(user: User, db: Session) -> Cart:
    cart = db.query(Cart).filter(Cart.user_id == user.id).first()
    if not cart:
        cart = Cart(user_id=user.id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart


def _calculate_cart(cart: Cart, db: Session) -> dict:
    items_data = []
    subtotal = 0.0

    items = db.query(CartItem).options(
        joinedload(CartItem.product).joinedload(Product.images),
        joinedload(CartItem.product).joinedload(Product.category),
    ).filter(CartItem.cart_id == cart.id).all()

    for item in items:
        item_total = item.product.effective_price * item.quantity
        subtotal += item_total
        items_data.append({
            "id": item.id,
            "product_id": item.product_id,
            "product": item.product,
            "quantity": item.quantity,
            "item_total": item_total,
        })

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

    return {
        "id": cart.id,
        "items": items_data,
        "coupon_code": coupon_code,
        "subtotal": round(subtotal, 2),
        "discount_amount": round(discount, 2),
        "total": round(subtotal - discount, 2),
        "items_count": sum(i["quantity"] for i in items_data),
    }


@router.get("", response_model=CartOut)
def get_cart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cart = _get_or_create_cart(current_user, db)
    return _calculate_cart(cart, db)


@router.post("/items", response_model=CartOut, status_code=201)
def add_to_cart(
    data: CartItemAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(
        Product.id == data.product_id, Product.is_active == True
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="المنتج مش موجود")
    if product.stock_quantity < data.quantity:
        raise HTTPException(status_code=400, detail=f"الكمية المتاحة {product.stock_quantity} فقط")

    cart = _get_or_create_cart(current_user, db)
    existing = db.query(CartItem).filter(
        CartItem.cart_id == cart.id, CartItem.product_id == data.product_id
    ).first()

    if existing:
        new_qty = existing.quantity + data.quantity
        if new_qty > product.stock_quantity:
            raise HTTPException(status_code=400, detail=f"الكمية المتاحة {product.stock_quantity} فقط")
        existing.quantity = new_qty
    else:
        item = CartItem(cart_id=cart.id, product_id=data.product_id, quantity=data.quantity)
        db.add(item)

    db.commit()
    return _calculate_cart(cart, db)


@router.put("/items/{item_id}", response_model=CartOut)
def update_cart_item(
    item_id: int,
    data: CartItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cart = _get_or_create_cart(current_user, db)
    item = db.query(CartItem).filter(
        CartItem.id == item_id, CartItem.cart_id == cart.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="العنصر مش موجود في الكارت")

    if data.quantity > item.product.stock_quantity:
        raise HTTPException(status_code=400, detail=f"الكمية المتاحة {item.product.stock_quantity} فقط")

    item.quantity = data.quantity
    db.commit()
    return _calculate_cart(cart, db)


@router.delete("/items/{item_id}", response_model=CartOut)
def remove_from_cart(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cart = _get_or_create_cart(current_user, db)
    item = db.query(CartItem).filter(
        CartItem.id == item_id, CartItem.cart_id == cart.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="العنصر مش موجود")
    db.delete(item)
    db.commit()
    return _calculate_cart(cart, db)


@router.delete("", response_model=CartOut)
def clear_cart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cart = _get_or_create_cart(current_user, db)
    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
    cart.coupon_id = None
    db.commit()
    return _calculate_cart(cart, db)


@router.post("/coupon", response_model=CartOut)
def apply_coupon(
    data: ApplyCouponRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    coupon = db.query(Coupon).filter(
        Coupon.code == data.code.upper(), Coupon.is_active == True
    ).first()
    if not coupon:
        raise HTTPException(status_code=404, detail="الكود ده مش صحيح أو منتهي")
    if coupon.expires_at and coupon.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="الكود ده انتهت صلاحيته")
    if coupon.max_uses and coupon.used_count >= coupon.max_uses:
        raise HTTPException(status_code=400, detail="الكود ده اتستخدم الحد الأقصى")

    cart = _get_or_create_cart(current_user, db)
    cart.coupon_id = coupon.id
    db.commit()
    return _calculate_cart(cart, db)


@router.delete("/coupon", response_model=CartOut)
def remove_coupon(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cart = _get_or_create_cart(current_user, db)
    cart.coupon_id = None
    db.commit()
    return _calculate_cart(cart, db)
