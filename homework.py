import logging
import os
import time

import requests
from dotenv import load_dotenv
from telegram import Bot
from http import HTTPStatus

import exceptions

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
    logging.info('Попытка отправить сообщение в Telegram')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        raise exceptions.SendMessageError(
            f'Ошибка отправки сообщения в Telegram. {error}')
    else:
        logging.info('Сообщение в Telegram отправлено')


def get_api_answer(current_timestamp):
    """Получаем ответ от API."""
    logging.info('Попытка получить ответ от API')
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    requests_params = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': params
    }
    try:
        response = requests.get(**requests_params)
    except Exception:
        raise exceptions.ApiNoAnswerError(
            f'Ошибка ответа API. Возможно проблема с {ENDPOINT}'
        )
    else:
        if response.status_code != HTTPStatus.OK:
            raise exceptions.ApiAnswerError(
                f'Неудачный ответ API. Запрос к {ENDPOINT}, ответ - {response}'
            )
        return response.json()


def check_response(response):
    """Проверяем ответ API."""
    logging.info('Проверяем ответ от API')
    if not isinstance(response, dict):
        raise TypeError(
            f'Ответ пришел не в виде словаря. Type: {type(response)}'
        )
    if 'homeworks' not in response:
        raise exceptions.MyResponseError(
            f'Нет ключа homeworks: {response.keys()}'
        )
    response_list = response['homeworks']
    if not isinstance(response_list, list):
        raise exceptions.MyResponseError(
            f'По ключу homeworks возвращается не список. '
            f'Type: {type(response_list)}'
        )
    return response_list


def parse_status(homework):
    """Получаем статус работы для передачи сообщения."""
    logging.info('Пробуем получить ответ по ключу для отправки сообщения')
    if not isinstance(homework, dict):
        raise TypeError(
            f'Ответ пришел не в виде словаря. Type: {type(homework)}'
        )
    if 'homework_name' not in homework:
        raise KeyError(
            f'Ключ homework_name не найден: {homework}'
        )
    if 'status' not in homework:
        raise KeyError(
            f'Ключ status не найден: {homework}'
        )
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES:
        raise exceptions.StatusError(
            f'Нет документированного статуса: {homework_status}. '
            f'{HOMEWORK_STATUSES.keys()}'
        )
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяем доступность переменных окружения."""
    logging.info('Проверяем переменные окружения')
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def main():
    """Основная логика работы бота."""
    if check_tokens() is False:
        raise SystemExit(
            'Ошибка в одной или нескольких переменных окружения: '
            'PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID'
        )
    message = ''
    while True:
        bot = Bot(token=TELEGRAM_TOKEN)
        current_timestamp = int(time.time())
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if len(homework) != 0:
                status = parse_status(homework[0])
            else:
                status = 'Нет взятых в проверку работ.'
            if status != message:
                send_message(bot, status)
                message = status
        except (exceptions.ApiAnswerError, exceptions.ApiNoAnswerError,
                exceptions.MyResponseError, TypeError, exceptions.StatusError,
                exceptions.SendMessageError) as error:
            logging.error(error)
            status = error.txt
        else:
            logging.info('Все ок!')
        finally:
            if status != message:
                send_message(bot, status)
                message = status
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
