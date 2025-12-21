from typing import Optional, TypedDict


class User(TypedDict):
    user_id: int
    state: str
    last_order_id: Optional[str]
    created_at: str
    updated_at: str


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


class Payment(TypedDict):
    id: str
    order_id: str
    provider_tx_id: str
    status: str
    amount_kopeks: int
    currency: str
    payload: str
    created_at: str
    updated_at: str


class Campaign(TypedDict):
    id: str
    title: str
    body: str
    price_kopeks: int
    status: str
    created_at: str
    started_at: Optional[str]
    finished_at: Optional[str]


class CampaignAudience(TypedDict):
    campaign_id: str
    user_id: int
    status: str
    message_id: Optional[int]
    error: Optional[str]
    updated_at: str


class CampaignResponse(TypedDict):
    id: str
    campaign_id: str
    user_id: int
    full_name: Optional[str]
    birthdate: Optional[str]
    phone: Optional[str]
    raw_text: Optional[str]
    status: str
    created_at: str
    updated_at: str
