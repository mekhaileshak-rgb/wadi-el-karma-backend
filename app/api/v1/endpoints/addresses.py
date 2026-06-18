from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.api.v1.deps import get_db, get_current_user
from app.models.models import Address as AddressModel, User
from app.schemas.schemas import AddressCreate, AddressOut

router = APIRouter()

@router.post("/addresses", response_model=AddressOut, status_code=status.HTTP_201_CREATED)
def create_address(
    address_in: AddressCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_address = AddressModel(**address_in.model_dump(), user_id=current_user.id)
    db.add(new_address)
    db.commit()
    db.refresh(new_address)
    return new_address