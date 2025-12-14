from typing import Optional, Tuple

from app.config import SIGNS_RU
from app.services import media


def parse_month_data(data: str) -> Optional[str]:
    if not data.startswith("month:"):
        return None
    ym = data.split(":", maxsplit=1)[1]
    return ym if media.parse_year_month(ym) else None


def parse_year_data(data: str) -> Optional[str]:
    if not data.startswith("year:"):
        return None
    year = data.split(":", maxsplit=1)[1]
    return year if media.is_valid_year(year) else None


def parse_sign_data(data: str) -> Optional[Tuple[str, str]]:
    if not data.startswith("sign:"):
        return None
    parts = data.split(":")
    if len(parts) != 3:
        return None
    _, ym, sign = parts
    if not media.parse_year_month(ym) or sign not in SIGNS_RU:
        return None
    return ym, sign


def parse_pay_data(data: str) -> Optional[str]:
    if not data.startswith("pay:"):
        return None
    return data.split(":", maxsplit=1)[1]


def parse_product(product_id: str) -> Optional[Tuple[str, str]]:
    parts = product_id.split(":")
    if len(parts) != 2:
        return None
    ym, sign = parts
    if not media.parse_year_month(ym) or sign not in SIGNS_RU:
        return None
    return ym, sign
