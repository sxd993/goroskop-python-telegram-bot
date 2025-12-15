import re
from pathlib import Path
from typing import List, Optional

from app.config import ALLOWED_EXTENSIONS, MONTH_NAMES_RU, SIGNS_RU, YEAR_MONTH_PATTERN


_YEAR_MONTH_REGEX = re.compile(YEAR_MONTH_PATTERN)


def is_valid_year(value: str) -> bool:
    return bool(re.fullmatch(r"\d{4}", value))


def parse_year_month(value: str) -> Optional[re.Match]:
    match = _YEAR_MONTH_REGEX.fullmatch(value)
    if not match:
        return None
    month = int(match.group("month"))
    if month < 1 or month > 12:
        return None
    return match


def available_years(media_dir: Path) -> List[str]:
    if not media_dir.exists():
        return []
    years = set()
    for path in media_dir.iterdir():
        if not path.is_dir():
            continue
        if is_valid_year(path.name):
            years.add(path.name)
    return sorted(years)


def months_for_year(media_dir: Path, year: str) -> List[str]:
    if not is_valid_year(year) or not media_dir.exists():
        return []
    months: List[str] = []
    year_dir = media_dir / year
    if not year_dir.is_dir():
        return []
    for path in year_dir.iterdir():
        if not path.is_dir():
            continue
        try:
            month_int = int(path.name)
        except ValueError:
            continue
        if 1 <= month_int <= 12:
            months.append(f"{year}-{month_int:02d}")
    return sorted(months)


def month_name_from_ym(ym: str) -> Optional[str]:
    match = parse_year_month(ym)
    if not match:
        return None
    return MONTH_NAMES_RU[int(match.group("month"))]


def build_product_id(ym: str, sign: str) -> Optional[str]:
    if parse_year_month(ym) and sign in SIGNS_RU:
        return f"{ym}:{sign}"
    return None


def available_signs(media_dir: Path, ym: str) -> List[str]:
    match = parse_year_month(ym)
    if not match:
        return []
    target_dir = media_dir / match.group("year") / match.group("month")
    if not target_dir.is_dir():
        return []
    signs = set()
    for ext in ALLOWED_EXTENSIONS:
        for file_path in target_dir.glob(f"*.{ext}"):
            sign = file_path.stem
            if sign in SIGNS_RU:
                signs.add(sign)
    for item in target_dir.iterdir():
        if item.is_dir() and item.name in SIGNS_RU:
            signs.add(item.name)
    # Keep zodiac order from Aries to Pisces; append any extras alphabetically.
    ordered = [sign for sign in SIGNS_RU if sign in signs]
    extras = sorted(signs.difference(SIGNS_RU))
    return ordered + extras


def find_content_path(media_dir: Path, ym: str, sign: str) -> Optional[Path]:
    match = parse_year_month(ym)
    if not match or sign not in SIGNS_RU:
        return None
    target_dir = media_dir / match.group("year") / match.group("month")
    if not target_dir.exists():
        return None
    for ext in ALLOWED_EXTENSIONS:
        candidate = target_dir / f"{sign}.{ext}"
        if candidate.is_file():
            return candidate
        nested = target_dir / sign / f"{sign}.{ext}"
        if nested.is_file():
            return nested
        nested_any = next((p for p in (target_dir / sign).glob(f"*.{ext}") if p.is_file()), None)
        if nested_any:
            return nested_any
    return None
