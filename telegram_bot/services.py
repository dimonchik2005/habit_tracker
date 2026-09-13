import requests
from django.conf import settings


class TelegramAPIError(Exception):
    """Ошибка отправки сообщения в Telegram."""


def send_telegram_message(chat_id, text):
    token = settings.TELEGRAM_BOT_TOKEN

    if not token:
        raise TelegramAPIError("Не задан TELEGRAM_BOT_TOKEN.")

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    try:
        response = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": text,
            },
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException:
        raise TelegramAPIError(
            "Не удалось выполнить запрос к Telegram."
        ) from None

    try:
        data = response.json()
    except ValueError:
        raise TelegramAPIError(
            "Telegram вернул некорректный JSON."
        ) from None

    if not isinstance(data, dict) or data.get("ok") is not True:
        raise TelegramAPIError(
            "Telegram не подтвердил отправку сообщения."
        )

    return data