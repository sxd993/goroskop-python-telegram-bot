from typing import Optional, TypedDict


class Order(TypedDict):
    id: str
    user_id: int
    product_id: str
    amount_kopeks: int
    currency: str
    status: str
    created_at: str
    paid_at: Optional[str]
    delivered_at: Optional[str]
    telegram_charge_id: Optional[str]


class Review(TypedDict):
    id: str
    order_id: str
    user_id: int
    product_id: str
    status: str
    text: Optional[str]
    created_at: str
    answered_at: Optional[str]
