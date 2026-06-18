from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import Optional, List, Any, Dict
from datetime import datetime
from app.models.models import UserRole, OrderStatus, PaymentStatus, PaymentMethod
import re


# ─── Base ─────────────────────────────────────────────────
class BaseResponse(BaseModel):
    class Config:
        from_attributes = True


# ─── Auth ─────────────────────────────────────────────────
class UserRegister(BaseModel):
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("كلمة المرور لازم تكون 8 حروف على الأقل")
        if not re.search(r"[A-Z]", v):
            raise ValueError("كلمة المرور لازم تحتوي على حرف كبير")
        if not re.search(r"\d", v):
            raise ValueError("كلمة المرور لازم تحتوي على رقم")
        return v

    @field_validator("full_name")
    @classmethod
    def validate_name(cls, v):
        if len(v.strip()) < 3:
            raise ValueError("الاسم لازم يكون 3 حروف على الأقل")
        return v.strip()


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("كلمة المرور لازم تكون 8 حروف على الأقل")
        return v


# ─── User ─────────────────────────────────────────────────
class UserOut(BaseResponse):
    id: int
    email: str
    full_name: str
    phone: Optional[str]
    role: UserRole
    is_active: bool
    is_verified: bool
    avatar: Optional[str]
    created_at: datetime


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None


# ─── Address ─────────────────────────────────────────────
class AddressCreate(BaseModel):
    label: str = "Home"
    full_name: str
    phone: str
    street: str
    city: str
    governorate: str
    postal_code: Optional[str] = None
    is_default: bool = False


class AddressOut(BaseResponse):
    id: int
    label: str
    full_name: str
    phone: str
    street: str
    city: str
    governorate: str
    postal_code: Optional[str]
    is_default: bool


# ─── Category ────────────────────────────────────────────
class CategoryCreate(BaseModel):
    name: str
    name_ar: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    is_active: bool = True
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    name_ar: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class CategoryOut(BaseResponse):
    id: int
    name: str
    name_ar: Optional[str]
    slug: str
    description: Optional[str]
    image: Optional[str]
    parent_id: Optional[int]
    is_active: bool
    sort_order: int


# ─── Product ─────────────────────────────────────────────
class ProductImageOut(BaseResponse):
    id: int
    url: str
    alt_text: Optional[str]
    is_primary: bool
    sort_order: int


class ProductCreate(BaseModel):
    name: str
    name_ar: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    description_ar: Optional[str] = None
    price: float
    sale_price: Optional[float] = None
    cost_price: Optional[float] = None
    sku: Optional[str] = None
    barcode: Optional[str] = None
    stock_quantity: int = 0
    low_stock_threshold: int = 5
    weight: Optional[float] = None
    category_id: Optional[int] = None
    brand: Optional[str] = None
    is_active: bool = True
    is_featured: bool = False
    tags: Optional[List[str]] = None
    attributes: Optional[Dict[str, Any]] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None

    @field_validator("price")
    @classmethod
    def validate_price(cls, v):
        if v < 0:
            raise ValueError("السعر لازم يكون موجب")
        return v


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    name_ar: Optional[str] = None
    description: Optional[str] = None
    description_ar: Optional[str] = None
    price: Optional[float] = None
    sale_price: Optional[float] = None
    stock_quantity: Optional[int] = None
    category_id: Optional[int] = None
    brand: Optional[str] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    tags: Optional[List[str]] = None
    attributes: Optional[Dict[str, Any]] = None


class ProductOut(BaseResponse):
    id: int
    name: str
    name_ar: Optional[str]
    slug: str
    description: Optional[str]
    description_ar: Optional[str]
    price: float
    sale_price: Optional[float]
    sku: Optional[str]
    stock_quantity: int
    brand: Optional[str]
    category_id: Optional[int]
    category: Optional[CategoryOut]
    images: List[ProductImageOut] = []
    is_active: bool
    is_featured: bool
    tags: Optional[List[str]]
    attributes: Optional[Dict[str, Any]]
    views_count: int
    sales_count: int
    in_stock: bool
    effective_price: float
    created_at: datetime


class ProductListOut(BaseResponse):
    id: int
    name: str
    name_ar: Optional[str]
    slug: str
    price: float
    sale_price: Optional[float]
    effective_price: float
    in_stock: bool
    is_featured: bool
    brand: Optional[str]
    images: List[ProductImageOut] = []
    category: Optional[CategoryOut]


# ─── Cart ─────────────────────────────────────────────────
class CartItemAdd(BaseModel):
    product_id: int
    quantity: int = 1

    @field_validator("quantity")
    @classmethod
    def validate_qty(cls, v):
        if v < 1:
            raise ValueError("الكمية لازم تكون 1 على الأقل")
        return v


class CartItemUpdate(BaseModel):
    quantity: int

    @field_validator("quantity")
    @classmethod
    def validate_qty(cls, v):
        if v < 1:
            raise ValueError("الكمية لازم تكون 1 على الأقل")
        return v


class CartItemOut(BaseResponse):
    id: int
    product_id: int
    product: ProductListOut
    quantity: int
    item_total: float = 0


class CartOut(BaseResponse):
    id: int
    items: List[CartItemOut] = []
    coupon_code: Optional[str] = None
    subtotal: float = 0
    discount_amount: float = 0
    total: float = 0
    items_count: int = 0


class ApplyCouponRequest(BaseModel):
    code: str


# ─── Order ────────────────────────────────────────────────
class OrderCreate(BaseModel):
    address_id: int
    payment_method: PaymentMethod = PaymentMethod.cash_on_delivery
    notes: Optional[str] = None


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    note: Optional[str] = None
    tracking_number: Optional[str] = None


class OrderItemOut(BaseResponse):
    id: int
    product_id: int
    product_name: str
    product_sku: Optional[str]
    quantity: int
    unit_price: float
    total_price: float


class OrderOut(BaseResponse):
    id: int
    order_number: str
    status: OrderStatus
    payment_status: PaymentStatus
    payment_method: PaymentMethod
    subtotal: float
    shipping_cost: float
    discount_amount: float
    tax_amount: float
    total: float
    shipping_full_name: str
    shipping_phone: str
    shipping_street: str
    shipping_city: str
    shipping_governorate: str
    coupon_code: Optional[str]
    tracking_number: Optional[str]
    notes: Optional[str]
    items: List[OrderItemOut] = []
    created_at: datetime


# ─── Coupon ───────────────────────────────────────────────
class CouponCreate(BaseModel):
    code: str
    discount_type: str = "percentage"
    discount_value: float
    min_order_amount: float = 0
    max_uses: Optional[int] = None
    expires_at: Optional[datetime] = None


class CouponOut(BaseResponse):
    id: int
    code: str
    discount_type: str
    discount_value: float
    min_order_amount: float
    max_uses: Optional[int]
    used_count: int
    is_active: bool
    expires_at: Optional[datetime]


# ─── Review ───────────────────────────────────────────────
class ReviewCreate(BaseModel):
    product_id: int
    rating: int
    comment: Optional[str] = None

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v):
        if not 1 <= v <= 5:
            raise ValueError("التقييم لازم يكون بين 1 و 5")
        return v


class ReviewOut(BaseResponse):
    id: int
    product_id: int
    user_id: int
    user: Optional[UserOut]
    rating: int
    comment: Optional[str]
    is_approved: bool
    created_at: datetime


# ─── Payment ─────────────────────────────────────────────
class PaymentIntentCreate(BaseModel):
    order_id: int


class PaymentIntentOut(BaseModel):
    client_secret: str
    payment_intent_id: str


# ─── Admin Dashboard ─────────────────────────────────────
class DashboardStats(BaseModel):
    total_revenue: float
    total_orders: int
    total_customers: int
    total_products: int
    pending_orders: int
    low_stock_products: int
    revenue_today: float
    orders_today: int


# ─── Pagination ──────────────────────────────────────────
class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
