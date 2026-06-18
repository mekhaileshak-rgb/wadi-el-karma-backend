from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import Order, PaymentStatus, OrderStatus, OrderStatusHistory, User
from app.schemas.schemas import PaymentIntentCreate, PaymentIntentOut
from app.api.v1.deps import get_current_user
from app.core.config import settings
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/create-intent", response_model=PaymentIntentOut)
def create_payment_intent(
    data: PaymentIntentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = db.query(Order).filter(
        Order.id == data.order_id, Order.user_id == current_user.id
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="الطلب مش موجود")
    if order.payment_status == PaymentStatus.paid:
        raise HTTPException(status_code=400, detail="الطلب ده اتدفع خلاص")

    try:
        intent = stripe.PaymentIntent.create(
            amount=int(order.total * 100),  # Convert to cents
            currency="egp",
            metadata={
                "order_id": order.id,
                "order_number": order.order_number,
                "user_id": current_user.id,
            },
        )
        order.stripe_payment_intent_id = intent.id
        db.commit()

        return PaymentIntentOut(
            client_secret=intent.client_secret,
            payment_intent_id=intent.id,
        )
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"خطأ في الدفع: {str(e)}")


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    db: Session = Depends(get_db),
):
    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook")

    if event["type"] == "payment_intent.succeeded":
        intent = event["data"]["object"]
        order_id = intent["metadata"].get("order_id")
        if order_id:
            order = db.query(Order).filter(Order.id == int(order_id)).first()
            if order:
                order.payment_status = PaymentStatus.paid
                order.status = OrderStatus.confirmed
                db.add(OrderStatusHistory(
                    order_id=order.id,
                    status=OrderStatus.confirmed,
                    note="تم الدفع بنجاح عبر Stripe"
                ))
                db.commit()

    elif event["type"] == "payment_intent.payment_failed":
        intent = event["data"]["object"]
        order_id = intent["metadata"].get("order_id")
        if order_id:
            order = db.query(Order).filter(Order.id == int(order_id)).first()
            if order:
                order.payment_status = PaymentStatus.failed
                db.commit()

    return {"status": "ok"}


@router.get("/order/{order_id}/status")
def get_payment_status(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = db.query(Order).filter(
        Order.id == order_id, Order.user_id == current_user.id
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="الطلب مش موجود")
    return {
        "order_id": order.id,
        "order_number": order.order_number,
        "payment_status": order.payment_status,
        "order_status": order.status,
    }
