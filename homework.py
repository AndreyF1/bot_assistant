import logging
import os
import time

import requests
from dotenv import load_dotenv
from telegram import Bot

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
        if response.status_code != 200:
            raise exceptions.ApiAnswerError(
                'Ответ API отличный от 200.'
            )
    except Exception as error:
        raise exceptions.ApiAnswerError(
            f'Нет ответа от API: {error}'
        )
    else:
        print(response.json())
        return response.json()


def check_response(response):
    """Проверяем ответ API."""
    logging.info('Проверяем ответ от API')
    if isinstance(response, dict):
        try:
            response['homeworks']
        except Exception as error:
            raise exceptions.MyResponseError(
                f'Нет ключа homeworks: {error}'
            )
        if isinstance(response['homeworks'], list):
            return response['homeworks']
        else:
            raise exceptions.MyResponseError(
                'По ключу homeworks возвращается не список.'
            )
    else:
        raise TypeError(
            'Ответ пришел не в виде словаря.'
        )


def parse_status(homework):
    """Получаем статус работы для передачи сообщения."""
    logging.info('Пробуем получить ответ по ключу для отправки сообщения')
    try:
        homework.get('homework_name')
        homework.get('status')
    except Exception as error:
        raise exceptions.StatusError(
            f'Ключ homework_name или status не найден: {error}'
        )
    else:
        homework_name = homework['homework_name']
        homework_status = homework['status']
    try:
        verdict = HOMEWORK_STATUSES[homework_status]
    except Exception as error:
        raise exceptions.StatusError(
            f'Нет документированного статуса: {error}'
        )
    else:
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяем доступность переменных окружения."""
    logging.info('Проверяем переменные окружения')
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def main():
    """Основная логика работы бота."""
    if check_tokens() is False:
        raise SystemExit('Ошибка в переменных окружения.')
    homework = []
    status = 'Нет взятых в проверку работ'
    while True:
        bot = Bot(token=TELEGRAM_TOKEN)
        current_timestamp = int(time.time())
        try:
            response = get_api_answer(current_timestamp)
            if check_response(response) != homework:
                homework = check_response(response)
                status = parse_status(homework[0])
                send_message(bot, status)
            elif status == 'Нет взятых в проверку работ':
                send_message(bot, status)
                status = ''
            else:
                logging.debug('Нет новых статусов')
        except exceptions.ApiAnswerError:
            logging.error('Ошибка доступа для endpoint')
            send_message(bot, 'Ошибка доступа для endpoint')
        except exceptions.MyResponseError:
            logging.error('Ошибка проверки полученного ответа от API.')
            send_message(bot, 'Ошибка проверки полученного ответа от API.')
        except TypeError:
            logging.error('Ответ пришел не в виде словаря.')
            send_message(bot, 'Ответ пришел не в виде словаря.')
        except exceptions.StatusError:
            logging.error('Ошибка получения статуса работы.')
            send_message(
                bot, 'Ошибка проверки полученного ответа от API.'
            )
        except exceptions.SendMessageError:
            logging.error('Ошибка отправки сообщения в Telegram.')
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
