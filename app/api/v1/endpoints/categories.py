from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.models import Category, User
from app.schemas.schemas import CategoryCreate, CategoryUpdate, CategoryOut
from app.api.v1.deps import get_current_admin
from app.utils.file_upload import save_upload_file
from slugify import slugify
try:
    from slugify import slugify
except ImportError:
    from python_slugify import slugify

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=List[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).filter(Category.is_active == True).order_by(Category.sort_order).all()


@router.get("/{category_id}", response_model=CategoryOut)
def get_category(category_id: int, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="التصنيف مش موجود")
    return category


@router.post("", response_model=CategoryOut, status_code=201)
def create_category(
    data: CategoryCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    slug = data.slug or slugify(data.name)
    if db.query(Category).filter(Category.slug == slug).first():
        raise HTTPException(status_code=400, detail="الـ slug ده موجود خلاص")

    category = Category(**data.model_dump(exclude={"slug"}), slug=slug)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.put("/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int,
    data: CategoryUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="التصنيف مش موجود")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=204)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="التصنيف مش موجود")
    db.delete(category)
    db.commit()


@router.post("/{category_id}/image")
async def upload_category_image(
    category_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="التصنيف مش موجود")
    category.image = await save_upload_file(file, folder="categories")
    db.commit()
    return {"image": category.image}
