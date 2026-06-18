from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func
from typing import Optional, List
from app.db.database import get_db
from app.models.models import Product, ProductImage, Category, User
from app.schemas.schemas import (
    ProductCreate, ProductUpdate, ProductOut, ProductListOut, ReviewCreate, ReviewOut
)
from app.api.v1.deps import get_current_user, get_current_admin
from app.utils.file_upload import save_upload_file
from slugify import slugify
# في بداية ملف app/api/v1/endpoints/products.py
try:
    from slugify import slugify
except ImportError:
    from slugify import slugify
import math

router = APIRouter(prefix="/products", tags=["Products"])


def _build_query(db: Session):
    return db.query(Product).options(
        joinedload(Product.images),
        joinedload(Product.category),
    )


@router.get("", response_model=dict)
def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    brand: Optional[str] = None,
    in_stock: Optional[bool] = None,
    is_featured: Optional[bool] = None,
    sort_by: str = Query("created_at", enum=["created_at", "price", "sales_count", "views_count"]),
    sort_order: str = Query("desc", enum=["asc", "desc"]),
    db: Session = Depends(get_db),
):
    query = _build_query(db).filter(Product.is_active == True)

    if search:
        query = query.filter(
            or_(
                Product.name.ilike(f"%{search}%"),
                Product.name_ar.ilike(f"%{search}%"),
                Product.description.ilike(f"%{search}%"),
                Product.brand.ilike(f"%{search}%"),
            )
        )
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if brand:
        query = query.filter(Product.brand.ilike(f"%{brand}%"))
    if in_stock is not None:
        if in_stock:
            query = query.filter(Product.stock_quantity > 0)
        else:
            query = query.filter(Product.stock_quantity == 0)
    if is_featured is not None:
        query = query.filter(Product.is_featured == is_featured)

    sort_col = getattr(Product, sort_by)
    query = query.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())

    total = query.count()
    products = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [ProductListOut.model_validate(p) for p in products],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size),
    }


@router.get("/featured", response_model=List[ProductListOut])
def featured_products(limit: int = 8, db: Session = Depends(get_db)):
    return _build_query(db).filter(
        Product.is_active == True, Product.is_featured == True
    ).limit(limit).all()


@router.get("/{slug}", response_model=ProductOut)
def get_product(slug: str, db: Session = Depends(get_db)):
    product = _build_query(db).filter(Product.slug == slug).first()
    if not product:
        raise HTTPException(status_code=404, detail="المنتج مش موجود")
    product.views_count += 1
    db.commit()
    return product


@router.post("", response_model=ProductOut, status_code=201)
def create_product(
    data: ProductCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    slug = data.slug or slugify(data.name)
    if db.query(Product).filter(Product.slug == slug).first():
        slug = f"{slug}-{func.now()}"

    product = Product(**data.model_dump(exclude={"slug"}), slug=slug)
    db.add(product)
    db.commit()
    db.refresh(product)
    return _build_query(db).filter(Product.id == product.id).first()


@router.put("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    data: ProductUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="المنتج مش موجود")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    return _build_query(db).filter(Product.id == product_id).first()


@router.delete("/{product_id}", status_code=204)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="المنتج مش موجود")
    db.delete(product)
    db.commit()


@router.post("/{product_id}/images", status_code=201)
async def upload_product_images(
    product_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="المنتج مش موجود")

    uploaded = []
    has_primary = db.query(ProductImage).filter(
        ProductImage.product_id == product_id, ProductImage.is_primary == True
    ).first()

    for i, file in enumerate(files):
        url = await save_upload_file(file, folder="products")
        img = ProductImage(
            product_id=product_id,
            url=url,
            is_primary=(not has_primary and i == 0),
            sort_order=i,
        )
        db.add(img)
        uploaded.append(url)

    db.commit()
    return {"uploaded": uploaded, "count": len(uploaded)}


@router.delete("/{product_id}/images/{image_id}", status_code=204)
def delete_product_image(
    product_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    img = db.query(ProductImage).filter(
        ProductImage.id == image_id, ProductImage.product_id == product_id
    ).first()
    if not img:
        raise HTTPException(status_code=404, detail="الصورة مش موجودة")
    db.delete(img)
    db.commit()


# ─── Reviews ─────────────────────────────────────────────
@router.get("/{product_id}/reviews", response_model=List[ReviewOut])
def get_reviews(product_id: int, db: Session = Depends(get_db)):
    from app.models.models import Review
    from sqlalchemy.orm import joinedload as jl
    return db.query(Review).options(jl(Review.user)).filter(
        Review.product_id == product_id, Review.is_approved == True
    ).all()


@router.post("/{product_id}/reviews", response_model=ReviewOut, status_code=201)
def add_review(
    product_id: int,
    data: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.models import Review
    existing = db.query(Review).filter(
        Review.product_id == product_id, Review.user_id == current_user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="عملت review على المنتج ده خلاص")

    review = Review(product_id=product_id, user_id=current_user.id,
                    rating=data.rating, comment=data.comment)
    db.add(review)
    db.commit()
    db.refresh(review)
    return review
