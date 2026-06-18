from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.security import (
    verify_password, get_password_hash,
    create_access_token, create_refresh_token, verify_token
)
from app.models.models import User
from app.schemas.schemas import (
    UserRegister, UserLogin, TokenResponse, RefreshTokenRequest,
    UserOut, UserUpdate, ChangePasswordRequest, AddressCreate, AddressOut
)
from app.api.v1.deps import get_current_user
from app.utils.file_upload import save_upload_file
import os

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(data: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="الإيميل ده موجود خلاص")

    user = User(
        email=data.email,
        full_name=data.full_name,
        phone=data.phone,
        hashed_password=get_password_hash(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # هنا التعديل: ضيف "type" جوه الـ payload
    return TokenResponse(
        access_token=create_access_token({"sub": user.id, "type": "access"}),
        refresh_token=create_refresh_token({"sub": user.id, "type": "refresh"}),
    )


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="الإيميل أو كلمة المرور غلط")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="الحساب ده موقوف")

    # التعديل هنا: أضف "type": "access" و "type": "refresh"
    return TokenResponse(
        access_token=create_access_token({"sub": user.id, "type": "access"}),
        refresh_token=create_refresh_token({"sub": user.id, "type": "refresh"}),
    )

@router.post("/refresh", response_model=TokenResponse)
def refresh_token(data: RefreshTokenRequest, db: Session = Depends(get_db)):
    payload = verify_token(data.refresh_token, "refresh")
    if not payload:
        raise HTTPException(status_code=401, detail="Refresh token غير صالح")

    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="المستخدم مش موجود")

    return TokenResponse(
        access_token=create_access_token({"sub": user.id}),
        refresh_token=create_refresh_token({"sub": user.id}),
    )


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserOut)
def update_me(
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.full_name:
        current_user.full_name = data.full_name
    if data.phone is not None:
        current_user.phone = data.phone
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/avatar", response_model=UserOut)
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    url = await save_upload_file(file, folder="avatars")
    current_user.avatar = url
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="كلمة المرور القديمة غلط")
    current_user.hashed_password = get_password_hash(data.new_password)
    db.commit()
    return {"message": "تم تغيير كلمة المرور بنجاح"}


# ─── Addresses ───────────────────────────────────────────
@router.get("/me/addresses", response_model=list[AddressOut])
def get_addresses(current_user: User = Depends(get_current_user)):
    return current_user.addresses


@router.post("/me/addresses", response_model=AddressOut, status_code=201)
def add_address(
    data: AddressCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.models import Address
    if data.is_default:
        for addr in current_user.addresses:
            addr.is_default = False

    address = Address(user_id=current_user.id, **data.model_dump())
    db.add(address)
    db.commit()
    db.refresh(address)
    return address


@router.delete("/me/addresses/{address_id}", status_code=204)
def delete_address(
    address_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.models import Address
    address = db.query(Address).filter(
        Address.id == address_id, Address.user_id == current_user.id
    ).first()
    if not address:
        raise HTTPException(status_code=404, detail="العنوان مش موجود")
    db.delete(address)
    db.commit()
