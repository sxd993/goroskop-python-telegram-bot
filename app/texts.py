from app.config import SIGNS_RU


def welcome() -> str:
    return (
        "✨ Добро пожаловать в «Твоя путеводная — гороскопы» ✨\n\n"
        "🔮 Здесь ты найдёшь точные и вдохновляющие гороскопы для всех знаков зодиака.\n"
        "Выбери гороскоп: на год или на месяц."
    )


def no_content() -> str:
    return "Контент пока не готов. Загляни позже."


def invalid_year() -> str:
    return "Некорректный год."


def invalid_month() -> str:
    return "Некорректный месяц."


def invalid_sign() -> str:
    return "Некорректный выбор."


def invalid_choice() -> str:
    return "Некорректный выбор. Попробуй еще раз."


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


def year_content_missing() -> str:
    return "Контент для этого года пока не готов."


def content_missing() -> str:
    return "Контент для выбранного гороскопа пока не готов."


def order_not_found() -> str:
    return "Заказ не найден."


def invalid_order() -> str:
    return "Некорректный заказ."


def invalid_product() -> str:
    return "Некорректный товар."


def year_section_empty() -> str:
    return "Годовые гороскопы пока недоступны."


def month_section_empty() -> str:
    return "Месячные гороскопы пока недоступны."


def choose_yearly_year() -> str:
    return "Выбери год для годового гороскопа:"


def choose_monthly_year() -> str:
    return "Выбери год, чтобы посмотреть месячные гороскопы:"


def price_caption_month(month_name: str, year: str, sign: str, price_rub: float) -> str:
    sign_name = SIGNS_RU.get(sign, sign)
    return f"{month_name} {year}, {sign_name}. Цена {price_rub:.0f} ₽"


def price_caption_year(year: str, sign: str, price_rub: float) -> str:
    sign_name = SIGNS_RU.get(sign, sign)
    return f"{year} год, {sign_name}. Цена {price_rub:.0f} ₽"


def month_prompt(month_name: str, year: str) -> str:
    return f"{month_name} {year}. Выбери знак:"


def year_prompt(year: str) -> str:
    return f"Год {year}. Выбери месяц:"


def year_sign_prompt(year: str) -> str:
    return f"Год {year}. Выбери знак:"


def file_missing_after_pay() -> str:
    return "Файл не найден. Напиши нам, мы вернем оплату."


def order_paid_message() -> str:
    return "Заказ уже оплачен, отправляю файл."


def admin_forbidden() -> str:
    return "У вас нет доступа к админ-панели."


def admin_menu() -> str:
    return "Админ-меню"


def admin_choose_type() -> str:
    return "Выбери тип гороскопа: годовой или месячный."


def admin_delete_start() -> str:
    return "Что удалить: годовой или месячный гороскоп?"


def admin_choose_year_delete_year() -> str:
    return "Выбери год, который нужно удалить (годовой гороскоп):"


def admin_choose_year_delete_month() -> str:
    return "Выбери год с месячными гороскопами для удаления:"


def admin_delete_no_years() -> str:
    return "Нет загруженных годовых гороскопов для удаления."


def admin_delete_no_month_years() -> str:
    return "Нет загруженных месячных гороскопов для удаления."


def admin_delete_no_months(year: str) -> str:
    return f"Для {year} года нет месяцев для удаления."


def admin_delete_no_signs() -> str:
    return "Нет файлов этого типа для удаления."


def admin_prompt_year() -> str:
    return "Введи год в формате YYYY"


def admin_invalid_year() -> str:
    return "Некорректный год. Попробуй еще раз."


def admin_invalid_month() -> str:
    return "Некорректный месяц."


def admin_choose_month(year: str) -> str:
    return f"Год {year}. Выбери месяц для загрузки:"


def admin_choose_month_delete(year: str) -> str:
    return f"Год {year}. Выбери месяц для удаления:"


def admin_choose_sign_year(year: str) -> str:
    return f"{year} год. Выбери знак зодиака:"


def admin_choose_sign(year: str, month: str) -> str:
    return f"{month}.{year}. Выбери знак зодиака:"


def admin_choose_sign_delete_year(year: str) -> str:
    return f"{year} год. Выбери знак для удаления:"


def admin_choose_sign_delete_month(year: str, month: str) -> str:
    return f"{month}.{year}. Выбери знак для удаления:"


def admin_invalid_sign() -> str:
    return "Некорректный знак."


def admin_invalid_type() -> str:
    return "Некорректный тип гороскопа."


def admin_prompt_file_month(year: str, month: str, sign: str) -> str:
    sign_name = SIGNS_RU.get(sign, sign)
    return (
        f"{month}.{year}, {sign_name}. Отправь изображение знака (jpg/png/webp) "
        "файлом или фото."
    )


def admin_prompt_file_year(year: str, sign: str) -> str:
    sign_name = SIGNS_RU.get(sign, sign)
    return (
        f"{year} год, {sign_name}. Отправь изображение знака (jpg/png/webp) "
        "файлом или фото."
    )


def admin_invalid_file() -> str:
    return "Нужно отправить изображение (jpg/png/webp)."


def admin_delete_missing() -> str:
    return "Файл не найден, нечего удалять."


def admin_delete_success_year(year: str, sign: str) -> str:
    sign_name = SIGNS_RU.get(sign, sign)
    return f"Удалил {year} год, {sign_name}."


def admin_delete_success_month(year: str, month: str, sign: str) -> str:
    sign_name = SIGNS_RU.get(sign, sign)
    return f"Удалил {month}.{year}, {sign_name}."


def admin_delete_confirm_year(year: str, sign: str) -> str:
    sign_name = SIGNS_RU.get(sign, sign)
    return f"Удалить {year} год, {sign_name}? Это действие нельзя отменить."


def admin_delete_confirm_month(year: str, month: str, sign: str) -> str:
    sign_name = SIGNS_RU.get(sign, sign)
    return f"Удалить {month}.{year}, {sign_name}? Это действие нельзя отменить."


def admin_delete_cancelled() -> str:
    return "Удаление отменено."


def admin_stats_title() -> str:
    return "Статистика продаж (оплаченные заказы):"


def admin_stats_empty() -> str:
    return "Пока нет оплаченных заказов."


def admin_session_reset() -> str:
    return "Сессия сброшена. Запусти /admin заново."


def admin_save_failed() -> str:
    return "Не удалось сохранить файл. Попробуй еще раз."


def admin_save_success_month(year: str, month: str, sign: str) -> str:
    sign_name = SIGNS_RU.get(sign, sign)
    return f"Файл для {month}.{year}, {sign_name} сохранен."


def admin_save_success_year(year: str, sign: str) -> str:
    sign_name = SIGNS_RU.get(sign, sign)
    return f"Файл для {year} года, {sign_name} сохранен."
