from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
from app.db.database import get_db
from app.models.models import Wishlist, Product, User
from app.schemas.schemas import ProductListOut
from app.api.v1.deps import get_current_user

router = APIRouter(prefix="/wishlist", tags=["Wishlist"])


@router.get("", response_model=List[ProductListOut])
def get_wishlist(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = db.query(Wishlist).options(
        joinedload(Wishlist.product).joinedload(Product.images),
        joinedload(Wishlist.product).joinedload(Product.category),
    ).filter(Wishlist.user_id == current_user.id).all()
    return [item.product for item in items]


@router.post("/{product_id}", status_code=201)
def add_to_wishlist(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == product_id, Product.is_active == True).first()
    if not product:
        raise HTTPException(status_code=404, detail="المنتج مش موجود")

    existing = db.query(Wishlist).filter(
        Wishlist.user_id == current_user.id, Wishlist.product_id == product_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="المنتج ده موجود في الـ wishlist خلاص")

    db.add(Wishlist(user_id=current_user.id, product_id=product_id))
    db.commit()
    return {"message": "تم الإضافة للـ wishlist"}


@router.delete("/{product_id}", status_code=204)
def remove_from_wishlist(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.query(Wishlist).filter(
        Wishlist.user_id == current_user.id, Wishlist.product_id == product_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="المنتج مش موجود في الـ wishlist")
    db.delete(item)
    db.commit()
