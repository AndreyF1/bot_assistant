class SendMessageError(Exception):
    """Класс-ошибка при отправке сообщения в Telegram."""

    def __init__(self, text):
        """Custom error text."""
        self.txt = text


class ApiAnswerError(Exception):
    """Класс-ошибка получения ответа API."""

    def __init__(self, text):
        """Custom error text."""
        self.txt = text


class MyResponseError(Exception):
    """Класс-ошибка ответа от API."""

    def __init__(self, text):
        """Custom error text."""
        self.txt = text


class StatusError(Exception):
    """Класс-ошибка получения статуса работы."""

    def __init__(self, text):
        """Custom error text."""
        self.txt = text
