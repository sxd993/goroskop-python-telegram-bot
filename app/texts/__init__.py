from app.config import SIGNS_RU


def welcome() -> str:
    return (
        "✨ Добро пожаловать в «Твоя путеводная — гороскопы» ✨\n\n"
        "🔮 Здесь ты найдёшь точные и вдохновляющие гороскопы для всех знаков зодиака.\n"
        "Выбери действие на клавиатуре:"
    )


def start_menu_hint() -> str:
    return "Чтобы начать — нажми «Купить прогноз» на нижней панели."


def choose_forecast_kind() -> str:
    return "Выбери тип гороскопа:"


def no_content() -> str:
    return "Контент пока не готов. Загляни позже."


def referral_link_message(code: str, link: str | None, paid_referrals: int) -> str:
    discount_note = (
        "Скидка для друга:\n"
        "300 ₽ на годовой прогноз\n\n"
    )
    if link:
        return (
            "Твоя реферальная ссылка, которой ты можешь поделиться с друзьями:\n"
            f"{link}\n\n"
            f"{discount_note}"
            "Если код из ссылки не применился, то вот код, который твой друг должен ввести перед покупкой:\n"
            f"{code}\n\n"
            "Оплативших по твоему коду:\n"
            f"{paid_referrals}"
        )
    return (
        f"{discount_note}"
        "Твой пригласительный код:\n"
        f"{code}\n\n"
        "Оплативших по твоему коду:\n"
        f"{paid_referrals}"
    )


def referral_menu() -> str:
    return (
        "Реферальное меню:\n\n"
        "1) Ссылка — поделись с другом, скидка применится автоматически.\n"
        "2) Код — если друг вводит вручную перед покупкой.\n"
        "3) Статистика — сколько оплатили по твоему коду."
    )


def referral_link_only_message(link: str | None) -> str:
    if link:
        return (
            "Твоя реферальная ссылка:\n"
            f"{link}\n\n"
            "Скидка для друга:\n"
            "300 ₽ на годовой прогноз"
        )
    return "Не удалось получить ссылку."


def referral_code_only_message(code: str) -> str:
    return (
        "Твой пригласительный код:\n"
        f"{code}"
    )


def referral_stats_message(paid_referrals: int) -> str:
    return (
        "Оплативших по твоему коду:\n"
        f"{paid_referrals}"
    )


def referral_prompt() -> str:
    return (
        "Вы пришли по рекомендации?\n"
        "Если да — нажмите «Да» и введите пригласительный код."
    )


def referral_code_request() -> str:
    return "Введите пригласительный код."


def referral_code_invalid() -> str:
    return "Код не найден. Проверьте и попробуйте еще раз."


def referral_code_self() -> str:
    return "Нельзя использовать свой собственный код."


def referral_code_already_used() -> str:
    return "Вы уже использовали пригласительный код. Оформляем без скидки."


def referral_code_saved() -> str:
    return "Код сохранен. Скидка применится при оплате."


def referral_code_invalid_start() -> str:
    return "Код из ссылки не найден. Скидка не применена."


def invalid_year() -> str:
    return "Некорректный год."


def invalid_month() -> str:
    return "Некорректный месяц."


def invalid_sign() -> str:
    return "Некорректный выбор."


def invalid_choice() -> str:
    return "Некорректный выбор. Попробуй еще раз."


def temporary_error() -> str:
    return "Временно не получилось, попробуй позже."


def support_contact(link: str) -> str:
    return f"Если нужна помощь — пиши: {link}"


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
        f"{month}.{year}, {sign_name}. Отправь изображения (jpg/png/webp) "
        "файлом или фото. Можно одним альбомом (медиагруппой)."
    )


def admin_prompt_file_year(year: str, sign: str) -> str:
    sign_name = SIGNS_RU.get(sign, sign)
    return (
        f"{year} год, {sign_name}. Отправь изображения (jpg/png/webp) "
        "файлом или фото. Можно одним альбомом (медиагруппой)."
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


def admin_stats_choose_month(page: int) -> str:
    return f"Статистика продаж по месяцам (страница {page}). Выбери месяц:"


def admin_stats_choose_year(page: int) -> str:
    return f"Статистика продаж по годам (страница {page}). Выбери год:"


def admin_stats_month_title(month_name: str, year: str) -> str:
    return f"Статистика продаж за {month_name} {year} (оплаченные):"


def admin_stats_month_empty(month_name: str, year: str) -> str:
    return f"За {month_name} {year} пока нет оплаченных заказов."


def admin_stats_year_title(year: str) -> str:
    return f"Статистика продаж за {year} год (оплаченные):"


def admin_stats_year_empty(year: str) -> str:
    return f"За {year} год пока нет оплаченных заказов."


def admin_stats_total(count: int, total_rub: float) -> str:
    return f"Итого: {count} шт. / {total_rub:.0f} ₽"


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


def admin_upload_finished_month(year: str, month: str, sign: str) -> str:
    sign_name = SIGNS_RU.get(sign, sign)
    return f"Загрузка завершена для {month}.{year}, {sign_name}."


def admin_upload_finished_year(year: str, sign: str) -> str:
    sign_name = SIGNS_RU.get(sign, sign)
    return f"Загрузка завершена для {year} года, {sign_name}."


def review_prompt() -> str:
    return (
        "Спасибо, что купили прогноз на март 2026 года\n\n"
        "Если хотите получить финансовый обряд (тот самый, о котором я рассказывала), "
        "то просто оставьте отзыв.\n\n"
        "После этого вам придёт сообщение с инструкцией."
    )


def review_request() -> str:
    return (
        "Напиши отзыв (минимум 100 символов). Ответ увидим только мы.\n\n"
        "Если передумал(а) — нажми «Отмена»."
    )


def review_contact_request() -> str:
    return (
        "Чтобы мы могли связаться с тобой, нажми кнопку для того, чтобы поделиться номером."
        "Это обязательно для отзыва."
    )


def review_thanks() -> str:
    return "Спасибо за отзыв!"


def review_money_ritual() -> str:
    return (
        "Обряд на деньги:\n"
        "03.03 -04.03 в любое время,но лучше вечером,когда луна выйдет на небо.\n"
        "Понадобится :\n"
        "-купюра (500/1000₽,сколько не жалко НЕ ТРАТИТЬ) у меня лично была 1000\n"
        "-три желтые монеты (любые)\n"
        "-свечка церковная,в идеале зеленая ,можно церковную обкатать в корице или мяте(в аптеке можно купить!)\n"
        "-тарелочка\n"
        "-масло (подсолнечное) или мёд\n"
        "-Полотенце ручное белое  или желток желательно новое (фикс прайс)\n\n"
        "На подоконник на тарелку ,в центр ставим свечу ,зажигаем спичками\n"
        "На тарелку льем масло(масло прилипает ,притягивает деньги)\n"
        "(Можно и масло и мёд)\n"
        "В эту же тарелку треугольником вокруг свечи кладем монеты.\n"
        "Рядом купюру,на которой надо написать свой фин код.\n\n"
        "Зажигаем свечу и \n"
        "Говорим 1: \n\n"
        "Как свеча эта горит, так и достаток мой разгорается. Как монеты медные (или железные), "
        "так и доходы мои крепкие. Соединитесь, монеты, в единое богатство и всегда при мне "
        "оставайтесь. Огонь силу дает, воск бедность забирает. Да будет так.\n\n"
        "Потом берём купюру с кодом и говорим 2:\n\n"
        "Денежка-любушка, голуба голубушка, в дом прилетела, на окошко села. Будь моим пастушком, "
        "стереги овечек (другие купюры). От себя не отпускай, в обиду не давай. Кто тебя обидит  "
        "тому глаз вон, кто тебя украдет  тому глаз вон. Деньгам в доме водиться  не переводиться. Аминь.\n\n"
        "Оставляем на месте пока свеча не догорит\n\n"
        "Когда догорит,на утро купюру в чехол телефона или куда то чтобы всегда была с собой,не тратить!!!!!\n"
        "В идеале держать там,чем вы зарабатываете)\n\n"
        "И 3 берем  полотенце :\n\n"
        "Полотенце нужно сложить 12 раз. Складывая каждый слой, читайте заговор "
        "(можно шепотом, можно про себя, главное  четко проговаривать слова):\n\n"
        "Пойду, раб(а) Божий(ья) (Ваше Имя), перекрестясь, на четыре дороги поклонясь. Найду я реку "
        "Златицу, где вода золотая, песок золотой. Умоюсь я водой той, утрусь полотенцем этим. "
        "Руки вытираю  золото прибавляю, лицо вытираю  достаток призываю. Пусть в доме моем добро "
        "водится, деньги не переводятся. Ключ. Замок. Язык. Аминь.\n\n"
        "После того как полотенце сложено и наговорено 12 раз, разверните его, оботрите им лицо, шею "
        "и руки, а затем положите это полотенце в изголовье своей кровати (под подушку или под матрас "
        "с вашей стороны). Пусть лежит, притягивает энергию пока идет растущая луна.\n"
        "Потом просто приберите."
    )


def review_expired() -> str:
    return "Отзыв недоступен или уже оставлен."


def review_cancelled() -> str:
    return "Ок, отменил(а) написание отзыва."


def payment_success() -> str:
    return "Оплата прошла успешно 🎉"


def payment_duplicate() -> str:
    return "Оплата уже учтена. Если файл не пришел, напиши нам."


def payment_failed() -> str:
    return "Платеж не прошел. Попробуй еще раз или свяжись с поддержкой."


def admin_reviews_title() -> str:
    return "Последние отзывы:"


def admin_reviews_empty() -> str:
    return "Пока нет отзывов."


def admin_reviews_page_title(page: int) -> str:
    return f"Отзывы (страница {page}). Выбери отзыв:"


def admin_reviews_kind_prompt() -> str:
    return "Отзывы: выбери тип."


def admin_reviews_months_title(page: int) -> str:
    return f"Месячные отзывы (страница {page}). Выбери месяц:"


def admin_reviews_months_empty() -> str:
    return "Пока нет месячных отзывов."


def admin_reviews_filtered_title(title: str, page: int) -> str:
    return f"{title} (страница {page}). Выбери отзыв:"


def admin_review_detail(
    title: str,
    created: str,
    order_tag: str,
    user_id: int,
    status: str,
    text: str,
    contact_phone: str | None,
    contact_username: str | None,
) -> str:
    status_label = "Оставлен" if status == "submitted" else "Нет отзыва"
    contact_value = "-"
    if contact_username:
        contact_value = f"@{contact_username}"
    if contact_phone:
        contact_value = f"{contact_value} / {contact_phone}" if contact_value != "-" else contact_phone
    return (
        f"{title}\n"
        f"Дата: {created}\n"
        f"Заказ: {order_tag}\n"
        f"User: {user_id}\n"
        f"Контакт: {contact_value}\n"
        f"Статус: {status_label}\n\n"
        f"{text}"
    )


def review_reward_caption(sign: str) -> str:
    sign_name = SIGNS_RU.get(sign, sign)
    return f"Твой бонус за отзыв. \nКартинка, которая работает как магнит для удачи и щит от негатива."


# === Broadcasts ===


def admin_broadcasts_menu(audience_size: int) -> str:
    return (
        f"Аудитория рассылок: {audience_size}"
    )


def admin_broadcasts_list_title() -> str:
    return "Список рассылок: выбери рассылку для управления."


def admin_broadcast_item_detail(title: str) -> str:
    return (
        f"Рассылка «{title}»\n\n"
        "Выбери действие:"
    )


def admin_broadcast_body_detail(title: str, body: str) -> str:
    body_text = body.strip()
    if not body_text:
        body_text = "Текст рассылки пока пуст."
    return (
        f"Рассылка «{title}»\n\n"
        "Текст рассылки:\n"
        f"{body_text}"
    )


def admin_broadcast_deleted(title: str) -> str:
    return f"Рассылка «{title}» удалена."


def admin_broadcast_prompt_title() -> str:
    return "Введи название рассылки."


def admin_broadcast_prompt_body() -> str:
    return "Введи текст рассылки (он уйдет пользователям как есть)."


def admin_broadcast_prompt_interest_redirect() -> str:
    return (
        "Опиши, что будет после нажатия «🔥 Мне интересно»: "
    )


def admin_broadcast_created(title: str) -> str:
    return f"Рассылка «{title}» создана как черновик."


def admin_broadcasts_empty() -> str:
    return "Список рассылок пока пуст."


def admin_broadcast_responses_list_title(
    title: str,
    page: int,
    total_pages: int,
) -> str:
    return (
        f"Ответы по рассылке «{title}» (страница {page}/{total_pages}). "
        "Выбери пользователя:"
    )


def admin_broadcast_response_detail(title: str, response: dict) -> str:
    return (
        f"Рассылка «{title}»\n"
        f"User: {response['user_id']}\n"
        f"ФИО: {response.get('full_name') or '-'}\n"
        f"Дата: {response.get('birthdate') or '-'}\n"
        f"Телефон: {response.get('phone') or '-'}\n"
    )


def admin_broadcast_launch_started(title: str, audience_size: int) -> str:
    return f"Запускаю рассылку «{title}». Получателей: {audience_size}."


def admin_broadcast_launch_ack() -> str:
    return "Рассылка была запущена."


def admin_broadcast_launch_repeat_ack() -> str:
    return "Эта рассылка уже запускалась, запускаю повторно."


def admin_broadcast_launch_finished(sent: int, failed: int, interested: int, declined: int) -> str:
    return (
        "Рассылка завершена.\n"
        f"Отправлено: {sent}\n"
        f"Ошибки: {failed}\n"
        f"Интересно: {interested}\n"
        f"Отказались: {declined}"
    )


def admin_broadcast_responses_empty() -> str:
    return "Пока нет ответов."


def admin_broadcast_stats_summary(
    title: str,
    delivered: int,
    not_delivered: int,
) -> str:
    return (
        f"Статистика рассылки «{title}»:\n"
        f"Получили рассылку: {delivered}\n"
        f"Не получили рассылку: {not_delivered}"
    )


def campaign_offer(body: str) -> str:
    return body


def campaign_declined() -> str:
    return "Ок, больше не будем беспокоить в этой рассылке."


def campaign_interest_redirect() -> str:
    return (
        "Отлично! Если вас заинтересовало это предложение, перейдите в нашего другого бота "
        "@kseniya_malinovskaya_bot, чтобы записаться. Там можно сразу выбрать удобное время и написать, "
        "что вы пришли из этой рассылки."
    )
