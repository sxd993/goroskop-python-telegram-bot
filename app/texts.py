from app.config import SIGNS_RU


def no_content() -> str:
    return "Контент пока не готов. Загляни позже."


def choose_year() -> str:
    return "Выбери год:"


def invalid_year() -> str:
    return "Некорректный год."


def invalid_month() -> str:
    return "Некорректный месяц."


def invalid_sign() -> str:
    return "Некорректный выбор."


def year_unavailable() -> str:
    return "Этот год недоступен."


def month_unavailable() -> str:
    return "Этот месяц недоступен."


def sign_unavailable() -> str:
    return "Этот знак недоступен."


def months_missing() -> str:
    return "Месяцы для этого года не найдены."


def month_content_missing() -> str:
    return "Контент для этого месяца пока не готов."


def content_missing() -> str:
    return "Контент для выбранного месяца пока не готов."


def order_not_found() -> str:
    return "Заказ не найден."


def invalid_order() -> str:
    return "Некорректный заказ."


def invalid_product() -> str:
    return "Некорректный товар."


def price_caption(month_name: str, year: str, sign: str, price_rub: float) -> str:
    sign_name = SIGNS_RU.get(sign, sign)
    return f"{month_name} {year}, {sign_name}. Цена {price_rub:.0f} ₽"


def month_prompt(month_name: str, year: str) -> str:
    return f"{month_name} {year}. Выбери знак:"


def year_prompt(year: str) -> str:
    return f"Год {year}. Выбери месяц:"


def file_missing_after_pay() -> str:
    return "Файл не найден. Напиши нам, мы вернем оплату."


def order_paid_message() -> str:
    return "Заказ уже оплачен, отправляю файл."
