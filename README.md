b # 🌿 Wadi El Karma - Backend API

Backend كامل لموقع Wadi El Karma للـ E-commerce مبني على **FastAPI + MySQL**.

## 🛠️ التقنيات

| التقنية | الاستخدام |
|---------|-----------|
| **FastAPI** | Web Framework |
| **SQLAlchemy** | ORM |
| **MySQL** | Database |
| **Alembic** | Migrations |
| **JWT** | Authentication |
| **bcrypt** | Password Hashing |
| **Stripe** | Payment Gateway |
| **Docker** | Containerization |

---

## 📁 هيكل المشروع

```
wadi-el-karma-backend/
├── app/
│   ├── api/v1/
│   │   ├── deps.py              # Auth dependencies
│   │   └── endpoints/
│   │       ├── auth.py          # تسجيل / دخول / بروفايل
│   │       ├── products.py      # المنتجات + صور + ريفيوز
│   │       ├── categories.py    # التصنيفات
│   │       ├── cart.py          # الكارت + كوبونات
│   │       ├── orders.py        # الطلبات
│   │       ├── payments.py      # Stripe Payment
│   │       ├── wishlist.py      # المفضلة
│   │       └── admin.py         # لوحة التحكم
│   ├── core/
│   │   ├── config.py            # الإعدادات
│   │   └── security.py          # JWT + Hashing
│   ├── db/
│   │   └── database.py          # DB Connection
│   ├── models/
│   │   └── models.py            # كل الـ Models
│   ├── schemas/
│   │   └── schemas.py           # كل الـ Pydantic Schemas
│   ├── utils/
│   │   └── file_upload.py       # رفع الصور
│   └── main.py                  # Entry Point
├── uploads/                     # الصور المرفوعة
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## 🚀 طريقة التشغيل

### 1. بدون Docker (للتطوير)

```bash
# نسخ المشروع وتثبيت الـ packages
pip install -r requirements.txt

# نسخ ملف الإعدادات
cp .env.example .env
# عدّل الـ .env بالإعدادات الصح

# تشغيل السيرفر
uvicorn app.main:app --reload --port 8000
```

### 2. مع Docker (الأسهل ✅)

```bash
# تشغيل كل حاجة (DB + API)
docker-compose up -d

# شوف الـ logs
docker-compose logs -f api
```

---

## 🗄️ قاعدة البيانات

الجداول بتتعمل أوتوماتيك عند أول تشغيل. للـ Migrations:

```bash
# إنشاء Migration جديدة
alembic revision --autogenerate -m "description"

# تطبيق الـ Migrations
alembic upgrade head

# الرجوع لـ Migration سابقة
alembic downgrade -1
```

---

## 📌 الـ API Endpoints

### 🔐 Authentication
| Method | Endpoint | الوصف |
|--------|----------|-------|
| POST | `/api/v1/auth/register` | تسجيل مستخدم جديد |
| POST | `/api/v1/auth/login` | تسجيل الدخول |
| POST | `/api/v1/auth/refresh` | تجديد الـ Token |
| GET | `/api/v1/auth/me` | بيانات المستخدم الحالي |
| PUT | `/api/v1/auth/me` | تعديل البروفايل |
| POST | `/api/v1/auth/me/avatar` | رفع صورة شخصية |
| POST | `/api/v1/auth/change-password` | تغيير كلمة المرور |
| GET | `/api/v1/auth/me/addresses` | عناويني |
| POST | `/api/v1/auth/me/addresses` | إضافة عنوان |
| DELETE | `/api/v1/auth/me/addresses/{id}` | حذف عنوان |

### 🛍️ Products
| Method | Endpoint | الوصف |
|--------|----------|-------|
| GET | `/api/v1/products` | قائمة المنتجات (search, filter, pagination) |
| GET | `/api/v1/products/featured` | المنتجات المميزة |
| GET | `/api/v1/products/{slug}` | تفاصيل منتج |
| POST | `/api/v1/products` | إضافة منتج (Admin) |
| PUT | `/api/v1/products/{id}` | تعديل منتج (Admin) |
| DELETE | `/api/v1/products/{id}` | حذف منتج (Admin) |
| POST | `/api/v1/products/{id}/images` | رفع صور (Admin) |
| GET | `/api/v1/products/{id}/reviews` | تقييمات المنتج |
| POST | `/api/v1/products/{id}/reviews` | إضافة تقييم |

### 📂 Categories
| Method | Endpoint | الوصف |
|--------|----------|-------|
| GET | `/api/v1/categories` | كل التصنيفات |
| POST | `/api/v1/categories` | إضافة تصنيف (Admin) |
| PUT | `/api/v1/categories/{id}` | تعديل تصنيف (Admin) |
| DELETE | `/api/v1/categories/{id}` | حذف تصنيف (Admin) |

### 🛒 Cart
| Method | Endpoint | الوصف |
|--------|----------|-------|
| GET | `/api/v1/cart` | عرض الكارت |
| POST | `/api/v1/cart/items` | إضافة للكارت |
| PUT | `/api/v1/cart/items/{id}` | تعديل الكمية |
| DELETE | `/api/v1/cart/items/{id}` | حذف من الكارت |
| DELETE | `/api/v1/cart` | مسح الكارت |
| POST | `/api/v1/cart/coupon` | تطبيق كوبون |
| DELETE | `/api/v1/cart/coupon` | إلغاء الكوبون |

### 📦 Orders
| Method | Endpoint | الوصف |
|--------|----------|-------|
| POST | `/api/v1/orders` | إنشاء طلب |
| GET | `/api/v1/orders` | طلباتي |
| GET | `/api/v1/orders/{id}` | تفاصيل طلب |
| POST | `/api/v1/orders/{id}/cancel` | إلغاء طلب |

### 💳 Payments
| Method | Endpoint | الوصف |
|--------|----------|-------|
| POST | `/api/v1/payments/create-intent` | إنشاء Stripe Payment Intent |
| POST | `/api/v1/payments/webhook` | Stripe Webhook |
| GET | `/api/v1/payments/order/{id}/status` | حالة الدفع |

### ❤️ Wishlist
| Method | Endpoint | الوصف |
|--------|----------|-------|
| GET | `/api/v1/wishlist` | قائمة المفضلة |
| POST | `/api/v1/wishlist/{product_id}` | إضافة للمفضلة |
| DELETE | `/api/v1/wishlist/{product_id}` | حذف من المفضلة |

### 👑 Admin Dashboard
| Method | Endpoint | الوصف |
|--------|----------|-------|
| GET | `/api/v1/admin/dashboard` | إحصائيات عامة |
| GET | `/api/v1/admin/dashboard/revenue-chart` | رسم بياني للإيرادات |
| GET | `/api/v1/admin/dashboard/top-products` | أكثر المنتجات مبيعاً |
| GET | `/api/v1/admin/orders` | كل الطلبات |
| PUT | `/api/v1/admin/orders/{id}/status` | تحديث حالة طلب |
| GET | `/api/v1/admin/users` | كل المستخدمين |
| PUT | `/api/v1/admin/users/{id}/toggle-status` | تفعيل/إيقاف مستخدم |
| PUT | `/api/v1/admin/users/{id}/role` | تغيير صلاحيات |
| GET | `/api/v1/admin/coupons` | الكوبونات |
| POST | `/api/v1/admin/coupons` | إنشاء كوبون |
| DELETE | `/api/v1/admin/coupons/{id}` | حذف كوبون |
| GET | `/api/v1/admin/reviews` | كل التقييمات |
| PUT | `/api/v1/admin/reviews/{id}/approve` | اعتماد تقييم |
| DELETE | `/api/v1/admin/reviews/{id}` | حذف تقييم |

---

## 🔑 الأدمن الافتراضي

```
Email: admin@wadielkarma.com
Password: Admin@123456
```

---

## 📖 Swagger Docs

بعد التشغيل افتح:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 💳 إعداد Stripe

1. اعمل حساب على [stripe.com](https://stripe.com)
2. خد الـ `Secret Key` من الـ Dashboard
3. حطه في الـ `.env`:
   ```
   STRIPE_SECRET_KEY=sk_test_xxxxx
   STRIPE_WEBHOOK_SECRET=whsec_xxxxx
   ```
4. للـ Webhook في التطوير استخدم [Stripe CLI](https://stripe.com/docs/stripe-cli):
   ```bash
   stripe listen --forward-to localhost:8000/api/v1/payments/webhook
   ```
