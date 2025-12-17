from typing import Literal, Optional, Tuple, TypedDict

from app.config import SIGNS_RU
from app.services import media


class ProductInfo(TypedDict):
    kind: Literal["year", "month"]
    year: str
    month: Optional[str]
    sign: str


def parse_layout_choice(data: str) -> Optional[str]:
    if data == "mode:year":
        return "year"
    if data == "mode:month":
        return "month"
    return None


def parse_month_year_data(data: str) -> Optional[str]:
    if not data.startswith("m-year:"):
        return None
    year = data.split(":", maxsplit=1)[1]
    return year if media.is_valid_year(year) else None


def parse_month_data(data: str) -> Optional[str]:
    if not data.startswith("m-month:"):
        return None
    ym = data.split(":", maxsplit=1)[1]
    return ym if media.parse_year_month(ym) else None


def parse_month_sign_data(data: str) -> Optional[Tuple[str, str]]:
    if not data.startswith("m-sign:"):
        return None
    parts = data.split(":")
    if len(parts) != 3:
        return None
    _, ym, sign = parts
    if not media.parse_year_month(ym) or sign not in SIGNS_RU:
        return None
    return ym, sign


def parse_year_data(data: str) -> Optional[str]:
    if not data.startswith("y-year:"):
        return None
    year = data.split(":", maxsplit=1)[1]
    return year if media.is_valid_year(year) else None


def parse_year_sign_data(data: str) -> Optional[Tuple[str, str]]:
    if not data.startswith("y-sign:"):
        return None
    parts = data.split(":")
    if len(parts) != 3:
        return None
    _, year, sign = parts
    if not media.is_valid_year(year) or sign not in SIGNS_RU:
        return None
    return year, sign


def parse_pay_data(data: str) -> Optional[str]:
    if not data.startswith("pay:"):
        return None
    return data.split(":", maxsplit=1)[1]


def parse_invoice_payload(payload: str) -> Optional[Tuple[ProductInfo, int, Optional[str]]]:
    """
    Payload format: "<product_id>|<user_id>|<order_id?>"
    """
    parts = payload.split("|")
    if len(parts) not in (2, 3):
        return None
    product_raw, user_raw = parts[0], parts[1]
    order_id = parts[2] if len(parts) == 3 else None
    product = parse_product(product_raw)
    if not product:
        return None
    try:
        user_id = int(user_raw)
    except ValueError:
        return None
    return product, user_id, order_id


def parse_product(product_id: str) -> Optional[ProductInfo]:
    parts = product_id.split(":")
    if len(parts) != 3:
        return None
    kind, payload, sign = parts
    if sign not in SIGNS_RU:
        return None
    if kind == "month":
        match = media.parse_year_month(payload)
        if not match:
            return None
        return {
            "kind": "month",
            "year": match.group("year"),
            "month": match.group("month"),
            "sign": sign,
        }
    if kind == "year":
        if not media.is_valid_year(payload):
            return None
        return {"kind": "year", "year": payload, "month": None, "sign": sign}
    return None
