import re
from pathlib import Path
from typing import List, Optional

from app.config import ALLOWED_EXTENSIONS, MONTH_NAMES_RU, SIGNS_RU, YEAR_MONTH_PATTERN


_YEAR_MONTH_REGEX = re.compile(YEAR_MONTH_PATTERN)
_YEAR_DIRNAME = "year"
_MONTH_DIRNAME = "month"


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


def _root_dir(media_dir: Path, dirname: str) -> Path:
    return media_dir / dirname


def _available_years(root_dir: Path) -> List[str]:
    if not root_dir.exists():
        return []
    years = set()
    for path in root_dir.iterdir():
        if not path.is_dir():
            continue
        if is_valid_year(path.name):
            years.add(path.name)
    return sorted(years)


def available_yearly_years(media_dir: Path) -> List[str]:
    return _available_years(_root_dir(media_dir, _YEAR_DIRNAME))


def available_monthly_years(media_dir: Path) -> List[str]:
    return _available_years(_root_dir(media_dir, _MONTH_DIRNAME))


def months_for_year(media_dir: Path, year: str) -> List[str]:
    if not is_valid_year(year):
        return []
    month_root = _root_dir(media_dir, _MONTH_DIRNAME)
    if not month_root.exists():
        return []
    months: List[str] = []
    year_dir = month_root / year
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


def available_year_signs(media_dir: Path, year: str) -> List[str]:
    if not is_valid_year(year):
        return []
    target_dir = _root_dir(media_dir, _YEAR_DIRNAME) / year
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
    ordered = [sign for sign in SIGNS_RU if sign in signs]
    extras = sorted(signs.difference(SIGNS_RU))
    return ordered + extras


def available_month_signs(media_dir: Path, ym: str) -> List[str]:
    match = parse_year_month(ym)
    if not match:
        return []
    target_dir = _root_dir(media_dir, _MONTH_DIRNAME) / match.group("year") / match.group("month")
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
    ordered = [sign for sign in SIGNS_RU if sign in signs]
    extras = sorted(signs.difference(SIGNS_RU))
    return ordered + extras


def find_year_content_path(media_dir: Path, year: str, sign: str) -> Optional[Path]:
    if not is_valid_year(year) or sign not in SIGNS_RU:
        return None
    target_dir = _root_dir(media_dir, _YEAR_DIRNAME) / year
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


def find_month_content_path(media_dir: Path, ym: str, sign: str) -> Optional[Path]:
    match = parse_year_month(ym)
    if not match or sign not in SIGNS_RU:
        return None
    target_dir = _root_dir(media_dir, _MONTH_DIRNAME) / match.group("year") / match.group("month")
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


def _cleanup_empty_dir(path: Path) -> None:
    try:
        path.rmdir()
    except OSError:
        pass


def delete_month_content(media_dir: Path, ym: str, sign: str) -> bool:
    path = find_month_content_path(media_dir, ym, sign)
    if not path:
        return False
    try:
        path.unlink()
    except OSError:
        return False
    if path.parent.name == sign:
        _cleanup_empty_dir(path.parent)
    return True


def delete_year_content(media_dir: Path, year: str, sign: str) -> bool:
    path = find_year_content_path(media_dir, year, sign)
    if not path:
        return False
    try:
        path.unlink()
    except OSError:
        return False
    if path.parent.name == sign:
        _cleanup_empty_dir(path.parent)
    return True


def build_month_product_id(ym: str, sign: str) -> Optional[str]:
    if parse_year_month(ym) and sign in SIGNS_RU:
        return f"month:{ym}:{sign}"
    return None


def build_year_product_id(year: str, sign: str) -> Optional[str]:
    if is_valid_year(year) and sign in SIGNS_RU:
        return f"year:{year}:{sign}"
    return None
