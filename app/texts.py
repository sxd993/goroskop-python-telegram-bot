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


def admin_forbidden() -> str:
    return "У вас нет доступа к админ-панели."


def admin_menu() -> str:
    return "Админ-меню"


def admin_prompt_year() -> str:
    return "Введи год в формате YYYY"


def admin_invalid_year() -> str:
    return "Некорректный год. Попробуй еще раз."


def admin_invalid_month() -> str:
    return "Некорректный месяц."


def admin_choose_month(year: str) -> str:
    return f"Год {year}. Выбери месяц для загрузки:"


def admin_choose_sign(year: str, month: str) -> str:
    return f"{month}.{year}. Выбери знак зодиака:"


def admin_invalid_sign() -> str:
    return "Некорректный знак."


def admin_prompt_file(year: str, month: str, sign: str) -> str:
    sign_name = SIGNS_RU.get(sign, sign)
    return (
        f"{month}.{year}, {sign_name}. Отправь изображение знака (jpg/png/webp) "
        "файлом или фото."
    )


def admin_invalid_file() -> str:
    return "Нужно отправить изображение (jpg/png/webp)."


def admin_session_reset() -> str:
    return "Сессия сброшена. Запусти /admin заново."


def admin_save_failed() -> str:
    return "Не удалось сохранить файл. Попробуй еще раз."


def admin_save_success(year: str, month: str, sign: str) -> str:
    sign_name = SIGNS_RU.get(sign, sign)
    return f"Файл для {month}.{year}, {sign_name} сохранен."
