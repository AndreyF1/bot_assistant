import logging
import os
import requests
from telegram import Bot
from dotenv import load_dotenv
import time


load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG)

console_handler = logging.StreamHandler()

PRACTICUM_TOKEN = os.getenv('YA_TOKEN')
TELEGRAM_TOKEN = os.getenv('T_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправка сообщения в телеграм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info('Сообщение в Telegram отправлено')
    except Exception as error:
        logging.error(f'Ошибка отправки сообщения: {error}')


def get_api_answer(current_timestamp):
    """Получаем ответ от API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code == 200:
        response = response.json()
    else:
        logging.error('Ошибка доступа для endpoint')
        bot = Bot(token=TELEGRAM_TOKEN)
        send_message(bot, 'Ошибка доступа для endpoint')
        raise requests.exceptions.ConnectionError
    return response


def check_response(response):
    """Проверяем ответ API."""
    try:
        response['homeworks']
    except Exception as error:
        logging.error(f'Нет ключа homeworks: {error}')
        bot = Bot(token=TELEGRAM_TOKEN)
        send_message(bot, 'Нет ключа homeworks')
    if type(response['homeworks']) != list:
        raise TypeError
    return response['homeworks']


def parse_status(homework):
    """Получаем статус работы для передачи сообщения."""
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except Exception as error:
        logging.error(f'Нет документированного статуса: {error}')
        bot = Bot(token=TELEGRAM_TOKEN)
        send_message(bot, 'Нет документированного статуса')
        raise error


def check_tokens():
    """Проверяем доступность переменных окружения."""
    if (PRACTICUM_TOKEN or TELEGRAM_TOKEN or TELEGRAM_CHAT_ID) is None:
        logging.critical('Одна или несколько переменных окружения отсутствует')
        return False
    return True


def main():
    """Основная логика работы бота."""
    check_tokens()
    homework = []
    status = 'Нет взятых в проверку работ'
    while True:
        bot = Bot(token=TELEGRAM_TOKEN)
        current_timestamp = int(time.time())
        response = get_api_answer(current_timestamp)
        if check_response(response) != homework:
            homework = check_response(response)
            status = parse_status(homework[0])
            send_message(bot, status)
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)
        elif status == 'Нет взятых в проверку работ':
            send_message(bot, status)
            status = ''
            time.sleep(RETRY_TIME)
        else:
            logging.debug('Нет новых статусов')
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
