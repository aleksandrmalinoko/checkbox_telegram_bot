import contextlib
import warnings
from pathlib import Path
import re
import datetime
import requests
import telebot
import urllib3
from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)
from configparser import ConfigParser
import yaml
import prometheus_client
from prometheus_client import Counter
import time
from urllib3.exceptions import InsecureRequestWarning
import logging

logging.basicConfig(filename="logs/os_check_list.log", level=logging.INFO)
using_bot_counter = Counter("using_bot_count", "request to the bot", ['method', 'user_id', 'username'])
parser = ConfigParser()
parser.read(Path('init.ini').absolute())
telegram_api_token = parser['telegram']['telegram_api_token']
omni_chat_id = parser['telegram']['omni_chat_id']
bot = telebot.TeleBot(token=telegram_api_token)
path: Path = Path(f"{Path.cwd()}/config.yaml").absolute()
with open(path, 'r') as stream:
    config = yaml.safe_load(stream)

urllib3.disable_warnings()
old_merge_environment_settings = requests.Session.merge_environment_settings


def escape_markdown(text):
    reparse = text.replace("\\", r"\\")
    reparse = reparse.replace(".", r"\.")
    reparse = reparse.replace("-", r"\-")
    reparse = reparse.replace("(", r"\(")
    reparse = reparse.replace(")", r"\)")
    reparse = reparse.replace("]", r"\]")
    reparse = reparse.replace("[", r"\[")
    reparse = reparse.replace("_", r"\_")
    reparse = reparse.replace("*", r"\*")
    reparse = reparse.replace("`", r"\`")
    reparse = reparse.replace("#", r"\#")
    reparse = reparse.replace("!", r"\!")
    return reparse


@contextlib.contextmanager
def no_ssl_verification():
    opened_adapters = set()

    def merge_environment_settings(self, url, proxies, stream, verify, cert):
        opened_adapters.add(self.get_adapter(url))
        settings = old_merge_environment_settings(self, url, proxies, stream, verify, cert)
        settings['verify'] = False
        return settings

    requests.Session.merge_environment_settings = merge_environment_settings
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', InsecureRequestWarning)
            yield
    finally:
        requests.Session.merge_environment_settings = old_merge_environment_settings
        for adapter in opened_adapters:
            try:
                adapter.close()
            except:
                pass


def build_menu(buttons, n_cols, header_buttons='', footer_buttons=''):
    menu = [buttons[item:item + n_cols] for item in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)
    return menu


def generate_buttons(names: list, ok_text="Успешно", fail_text="Ошибки") -> list:
    buttons: list = []
    idx = 0
    for name in names:
        idx += 1
        buttons.append(InlineKeyboardButton(name, callback_data=idx))
        buttons.append(InlineKeyboardButton(ok_text, callback_data=f"{idx}_ok"))
        buttons.append(InlineKeyboardButton(fail_text, callback_data=f"{idx}_fail"))
    buttons.append(InlineKeyboardButton("Сгенерировать отчет", callback_data=f"generate_report"))
    return buttons


def generate_buttons_from_keyboard(inline_keyboard) -> list:
    buttons: list = []
    for name in inline_keyboard:
        if name[0]['text'] != "Сгенерировать отчет":
            buttons.append(InlineKeyboardButton(name[0]['text'], callback_data=name[0]['callback_data']))
            buttons.append(InlineKeyboardButton(name[1]['text'], callback_data=name[1]['callback_data']))
            buttons.append(InlineKeyboardButton(name[2]['text'], callback_data=name[2]['callback_data']))
        else:
            buttons.append(InlineKeyboardButton("Сгенерировать отчет", callback_data=f"generate_report"))
    return buttons


def generate_report(inline_keyboard):
    report = ''
    inline_keyboard = inline_keyboard[:-1]
    for item in inline_keyboard:
        if item[2]['text'] == "Отмена":
            report += f"{item[0]['text']} -> {item[1]['text']}\n"
        else:
            report += f"{item[0]['text']} -> ?\n"
    return report


def update_buttons(inline_keyboard, change='', ok_text="Успешно", fail_text="Ошибки") -> list:
    buttons: list = generate_buttons_from_keyboard(inline_keyboard)
    element_name, element_change_status = change.split('_')
    if element_change_status == 'otm':
        for idx, service in enumerate(buttons):
            if service.callback_data == 'generate_report':
                buttons[idx] = InlineKeyboardButton("Сгенерировать отчет", callback_data=f"generate_report")
                continue
            if service.callback_data == f'{element_name}_status':
                buttons[idx] = InlineKeyboardButton(ok_text, callback_data=f"{element_name}_ok")
            if service.callback_data == f'{element_name}_otm':
                buttons[idx] = InlineKeyboardButton(fail_text, callback_data=f"{element_name}_fail")
        return buttons
    if element_change_status == 'ok':
        status = '✅'
    elif element_change_status == 'fail':
        status = '❌'
    else:
        return buttons
    for idx, service in enumerate(buttons):
        if service.callback_data == 'generate_report':
            buttons[idx] = InlineKeyboardButton("Сгенерировать отчет", callback_data=f"generate_report")
            continue
        if service.callback_data == f'{element_name}_ok':
            buttons[idx] = InlineKeyboardButton(status, callback_data=f"{element_name}_status")
        if service.callback_data == f'{element_name}_fail':
            buttons[idx] = InlineKeyboardButton("Отмена", callback_data=f"{element_name}_otm")
    return buttons


def do_markdown_syntax(input_string: str) -> str:
    return input_string.replace(r"_", r"\_")


@bot.message_handler(commands=['start'])
def start_message(message):
    using_bot_counter.labels(message.text, message.from_user.id, message.from_user.full_name).inc()
    bot.send_message(message.chat.id, "Доступные команды:\n\
/status - Меню статуса сервисов\n\
/list - Список сервисов\n\
/survey - Опрос сотрудников\n\
/zni - Отправить информирование о работах")


# @bot.message_handler(commands=['status'])
# def status_message(message):
#     using_bot_counter.labels(message.text, message.from_user.id, message.from_user.full_name).inc()
#     logging.info(f"{datetime.datetime.now().strftime('%d-%m-%Y %H:%M')}. "
#                  f"{message.text}, {message.from_user.id}, {message.from_user.full_name}")
#     keyboard = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, selective=True)
#     service_types = config['platform'].keys()
#     for type_service in service_types:
#         button = KeyboardButton(text=type_service)
#         keyboard.add(button)
#     button = KeyboardButton(text="Отмена")
#     keyboard.add(button)
#     bot.send_message(message.chat.id, "Выберите тип сервисов", reply_to_message_id=message.id, reply_markup=keyboard)
#     bot.register_next_step_handler(message, service_type_status)
#
#
# def service_type_status(message):
#     if message.text.startswith("/"):
#         bot.send_message(message.chat.id, "Неверное значение", reply_markup=ReplyKeyboardRemove())
#         return 0
#     if message.text == "Отмена":
#         bot.send_message(message.chat.id, "Отменено", reply_markup=ReplyKeyboardRemove())
#         return 0
#     bot.send_message(message.chat.id, "Тип выбран", reply_markup=ReplyKeyboardRemove())
#     buttons: list = generate_buttons(config['platform'][message.text]['services'])
#     reply_markup = InlineKeyboardMarkup(build_menu(buttons, n_cols=3))
#     bot.send_message(message.chat.id, "Статус сервисов", reply_markup=reply_markup)
#
#
# @bot.message_handler(commands=['list'])
# def list_message(message):
#     print(message.chat.id)
#     using_bot_counter.labels(message.text, message.from_user.id, message.from_user.full_name).inc()
#     logging.info(f"{datetime.datetime.now().strftime('%d-%m-%Y %H:%M')}. "
#                  f"{message.text}, {message.from_user.id}, {message.from_user.full_name}")
#     keyboard = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, selective=True)
#     service_types = config['platform'].keys()
#     for type_service in service_types:
#         button = KeyboardButton(text=type_service)
#         keyboard.add(button)
#     button = KeyboardButton(text="Отмена")
#     keyboard.add(button)
#     bot.send_message(message.chat.id, "Выберите тип сервисов", reply_to_message_id=message.id, reply_markup=keyboard)
#     bot.register_next_step_handler(message, service_type_list)
#
#
# def service_type_list(message):
#     if message.text.startswith("/"):
#         bot.send_message(message.chat.id, "Неверное значение", reply_markup=ReplyKeyboardRemove())
#         return 0
#     if message.text == "Отмена":
#         bot.send_message(message.chat.id, "Отменено", reply_markup=ReplyKeyboardRemove())
#         return 0
#     bot.send_message(message.chat.id, "Тип выбран", reply_markup=ReplyKeyboardRemove())
#     services_list = config['platform'][message.text]['services']
#     str_service_list = '\n'.join(services_list)
#     bot.send_message(message.chat.id, str_service_list)


@bot.message_handler(commands=['zni'])
def zni_message(message):
    using_bot_counter.labels(message.text, message.from_user.id, message.from_user.full_name).inc()
    logging.info(f"{datetime.datetime.now().strftime('%d-%m-%Y %H:%M')}. "
                 f"{message.text}, {message.from_user.id}, {message.from_user.full_name}")
    if message.chat.type != "private":
        bot.send_message(message.chat.id, "Используйте данную команду только в личных сообщениях боту")
        return 0
    keyboard = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    button = KeyboardButton(text="Отмена")
    keyboard.add(button)
    bot.send_message(message.chat.id, "Введите номер ЗНИ", reply_markup=keyboard)
    bot.register_next_step_handler(message, zni_number)


def zni_number(message):
    if message.text.startswith("/"):
        bot.send_message(message.chat.id, "Неверное значение", reply_markup=ReplyKeyboardRemove())
        return 0
    if message.text == "Отмена":
        bot.send_message(message.chat.id, "Отменено", reply_markup=ReplyKeyboardRemove())
        return 0
    regex_num = re.compile('\d{8}')
    number_zni = regex_num.findall(message.text)
    if number_zni:
        number_zni = f"C-{number_zni[0]}"
    else:
        bot.send_message(message.chat.id, "Номер не соответствует формату (C-XXXXXXXX), повторите попытку")
        bot.register_next_step_handler(message, zni_number)
        return 0
    keyboard = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    service_types = config['zni']['types']
    for type_service in service_types:
        button = KeyboardButton(text=type_service)
        keyboard.add(button)
    button = KeyboardButton(text="Отмена")
    keyboard.add(button)
    bot.send_message(message.chat.id, "Выберите тип ЗНИ", reply_markup=keyboard)
    bot.register_next_step_handler(
        message,
        zni_type,
        number_zni=number_zni
    )


def zni_type(message, number_zni):
    if message.text.startswith("/"):
        bot.send_message(message.chat.id, "Неверное значение", reply_markup=ReplyKeyboardRemove())
        return 0
    if message.text == "Отмена":
        bot.send_message(message.chat.id, "Отменено", reply_markup=ReplyKeyboardRemove())
        return 0
    keyboard = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    service_types = config['platform'].keys()
    for type_service in service_types:
        button = KeyboardButton(text=type_service)
        keyboard.add(button)
    button = KeyboardButton(text="Отмена")
    keyboard.add(button)
    bot.send_message(message.chat.id, "Выберите тип сервисов", reply_markup=keyboard)
    bot.register_next_step_handler(
        message,
        zni_platform,
        number_zni=number_zni,
        type_zni=message.text
    )


def zni_platform(message, number_zni, type_zni):
    if message.text.startswith("/"):
        bot.send_message(message.chat.id, "Неверное значение", reply_markup=ReplyKeyboardRemove())
        return 0
    if message.text == "Отмена":
        bot.send_message(message.chat.id, "Отменено", reply_markup=ReplyKeyboardRemove())
        return 0
    keyboard = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
    services_list = config['platform'][message.text]['services']
    for service_name in services_list:
        button = KeyboardButton(text=service_name)
        keyboard.add(button)
    button = KeyboardButton(text="Отмена")
    keyboard.add(button)
    bot.send_message(message.chat.id, "Выберите сервис", reply_markup=keyboard)
    bot.register_next_step_handler(
        message,
        zni_system,
        number_zni=number_zni,
        type_zni=type_zni,
        platform_zni=message.text
    )


def zni_system(message, number_zni, type_zni, platform_zni):
    if message.text.startswith("/"):
        bot.send_message(message.chat.id, "Неверное значение", reply_markup=ReplyKeyboardRemove())
        return 0
    if message.text == "Отмена":
        bot.send_message(message.chat.id, "Отменено", reply_markup=ReplyKeyboardRemove())
        return 0
    keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
    button = KeyboardButton(text="Да")
    keyboard.add(button)
    button = KeyboardButton(text="Нет")
    keyboard.add(button)
    button = KeyboardButton(text="Отмена")
    keyboard.add(button)
    bot.send_message(message.chat.id, "Оказывается ли влияние на мониторинг?", reply_markup=keyboard)
    bot.register_next_step_handler(
        message,
        zni_monitoring_influence,
        number_zni=number_zni,
        type_zni=type_zni,
        platform_zni=platform_zni,
        system_zni=message.text
    )


def zni_monitoring_influence(message, number_zni, type_zni, platform_zni, system_zni):
    if message.text.startswith("/"):
        bot.send_message(message.chat.id, "Неверное значение", reply_markup=ReplyKeyboardRemove())
        return 0
    if message.text == "Отмена":
        bot.send_message(message.chat.id, "Отменено", reply_markup=ReplyKeyboardRemove())
        return 0
    keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
    button = KeyboardButton(text="Да")
    keyboard.add(button)
    button = KeyboardButton(text="Нет")
    keyboard.add(button)
    button = KeyboardButton(text="Отмена")
    keyboard.add(button)
    bot.send_message(message.chat.id, "Оказывается ли влияние на потребителей?", reply_markup=keyboard)
    bot.register_next_step_handler(
        message,
        zni_consumer_influence,
        number_zni=number_zni,
        type_zni=type_zni,
        platform_zni=platform_zni,
        system_zni=system_zni,
        monitoring_influence_zni=message.text
    )


def zni_consumer_influence(message, number_zni, type_zni, platform_zni, system_zni, monitoring_influence_zni):
    if message.text.startswith("/"):
        bot.send_message(message.chat.id, "Неверное значение", reply_markup=ReplyKeyboardRemove())
        return 0
    if message.text == "Отмена":
        bot.send_message(message.chat.id, "Отменено", reply_markup=ReplyKeyboardRemove())
        return 0
    keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
    button = KeyboardButton(text=f"{message.chat.first_name} {message.chat.last_name}")
    keyboard.add(button)
    button = KeyboardButton(text="Отмена")
    keyboard.add(button)
    bot.send_message(message.chat.id, "Потвердите или укажите другое имя ответственного", reply_markup=keyboard)
    bot.register_next_step_handler(
        message,
        zni_responsible,
        number_zni=number_zni,
        type_zni=type_zni,
        platform_zni=platform_zni,
        system_zni=system_zni,
        monitoring_influence_zni=monitoring_influence_zni,
        consumer_influence_zni=message.text
    )


def zni_responsible(message, number_zni, type_zni, platform_zni, system_zni, monitoring_influence_zni,
                    consumer_influence_zni):
    if message.text.startswith("/"):
        bot.send_message(message.chat.id, "Неверное значение", reply_markup=ReplyKeyboardRemove())
        return 0
    if message.text == "Отмена":
        bot.send_message(message.chat.id, "Отменено", reply_markup=ReplyKeyboardRemove())
        return 0
    keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
    button = KeyboardButton(text="Без описания")
    keyboard.add(button)
    button = KeyboardButton(text="Отмена")
    keyboard.add(button)
    bot.send_message(message.chat.id, "Введите подробное описание работ", reply_markup=keyboard)
    bot.register_next_step_handler(
        message,
        zni_description_of_the_work,
        number_zni=number_zni,
        type_zni=type_zni,
        platform_zni=platform_zni,
        system_zni=system_zni,
        monitoring_influence_zni=monitoring_influence_zni,
        consumer_influence_zni=consumer_influence_zni,
        responsible_zni=message.text
    )


def zni_description_of_the_work(message, number_zni, type_zni, platform_zni, system_zni, monitoring_influence_zni,
                                consumer_influence_zni, responsible_zni):
    platform_zni = do_markdown_syntax(platform_zni)
    call_system_zni = f"{system_zni.split(' ')[0]}_{system_zni.split(' ')[1]}"
    if message.text.startswith("/"):
        bot.send_message(message.chat.id, "Неверное значение", reply_markup=ReplyKeyboardRemove())
        return 0
    if message.text == "Отмена":
        bot.send_message(message.chat.id, "Отменено", reply_markup=ReplyKeyboardRemove())
        return 0
    if message.text == "Без описания":
        description_of_the_work = ""
    else:
        description_of_the_work = f"Описание работ: {message.text}\n"
    if monitoring_influence_zni != "Нет":
        monitoring_influence_zni = f"_Влияние на мониторинг:_ *{escape_markdown(monitoring_influence_zni)}*\n"
    else:
        monitoring_influence_zni = ""
    if consumer_influence_zni != "Нет":
        consumer_influence_zni = f"*{escape_markdown(consumer_influence_zni)}*"
    if message.chat.username:
        responsible_username = f" @{escape_markdown(message.chat.username)}"
    else:
        responsible_username = ''
    formatted_string = f"\#{platform_zni}\n" \
                       f"Начало работ по ЗНИ *{escape_markdown(number_zni)}*\n" \
                       f"Тип ЗНИ: {type_zni.lower()}\n" \
                       f"_Сервис:_ *{system_zni}*\n\n{escape_markdown(description_of_the_work)}\n" \
                       f"{monitoring_influence_zni}" \
                       f"_Влияние на потребителей:_ {consumer_influence_zni}\n\n" \
                       f"_Ответственный:_ {escape_markdown(responsible_zni)}{responsible_username}\n"
    attempt_count = 0
    while True:
        try:
            attempt_count += 1
            msg = bot.send_message(omni_chat_id, formatted_string, reply_markup=ReplyKeyboardRemove(), parse_mode="MarkdownV2")
            logging.info(f"{datetime.datetime.now().strftime('%d-%m-%Y %H:%M')}. "
                         f"Уведомление о ЗНИ {number_zni} на сервисе {system_zni} отправлено")
            break
        except Exception as e:
            logging.error(f"{datetime.datetime.now().strftime('%d-%m-%Y %H:%M')}. "
                          f"user {message.chat.username} get error while sending message to Telegram: {e}")
            time.sleep(2)
            if attempt_count < 10:
                continue
            else:
                bot.send_message(
                    message.chat.id,
                    f"Сервер Telegram не ответил после 10 попыток. Попробуйте повторить запрос позже",
                )
                return -1
    omni_msg_id = msg.id
    call_number_zni = number_zni.split('-')[1]
    if platform_zni.find("Общие") != -1:
        call_platform_zni = 'OS'
    elif platform_zni.find("Служебные") != -1:
        call_platform_zni = 'SS'
    elif platform_zni.find("ЕПА") != -1:
        call_platform_zni = 'EPA'
    else:
        call_platform_zni = 'UIP'
    call_data_msg = f"{omni_msg_id}_{call_system_zni}_{call_number_zni}_{call_platform_zni}_zni"
    buttons: list = [InlineKeyboardButton("Завершено успешно",
                                          callback_data=f"ok_{call_data_msg}"),
                     InlineKeyboardButton("Завершено частично",
                                          callback_data=f"partially_{call_data_msg}"),
                     InlineKeyboardButton("Завершено с ошибкой",
                                          callback_data=f"fail_{call_data_msg}")]
    keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
    bot.send_message(
        message.chat.id,
        f"Готово",
        reply_markup=ReplyKeyboardRemove()
    )
    while True:
        try:
            bot.send_message(
                message.chat.id,
                f"Сообщение отправлено в чат 'Поддержка Omni':\n{formatted_string}",
                reply_markup=keyboard,
                parse_mode="MarkdownV2"
            )
            break
        except Exception as e:
            logging.error(f"{datetime.datetime.now().strftime('%d-%m-%Y %H:%M')}. "
                          f"user {message.chat.username} get error while sending message to Telegram: {e}")
            continue


@bot.message_handler(commands=['addservice'])
def add_service_message(message):
    using_bot_counter.labels(message.text, message.from_user.id, message.from_user.full_name).inc()
    logging.info(f"{datetime.datetime.now().strftime('%d-%m-%Y %H:%M')}. "
                 f"{message.text}, {message.from_user.id}, {message.from_user.full_name}")
    keyboard = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
    service_types = config['platform'].keys()
    for type_service in service_types:
        button = KeyboardButton(text=type_service)
        keyboard.add(button)
    button = KeyboardButton(text="Отмена")
    keyboard.add(button)
    bot.send_message(message.chat.id, "Выберите тип сервисов", reply_markup=keyboard)
    bot.register_next_step_handler(message, service_type_add)


def service_type_add(message):
    if message.text.startswith("/"):
        bot.send_message(message.chat.id, "Неверное значение", reply_markup=ReplyKeyboardRemove())
        return 0
    if message.text == "Отмена":
        bot.send_message(message.chat.id, "Отменено", reply_markup=ReplyKeyboardRemove())
        return 0
    bot.send_message(message.chat.id, "Тип выбран", reply_markup=ReplyKeyboardRemove())
    keyboard = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    button = KeyboardButton(text="Отмена")
    keyboard.add(button)
    bot.send_message(message.chat.id, "Название нового сервиса", reply_markup=keyboard)
    bot.register_next_step_handler(message, add_os, service_type=message.text)


def add_os(message, service_type):
    if message.text.startswith("/"):
        bot.send_message(message.chat.id, "Неверное значение", reply_markup=ReplyKeyboardRemove())
        return 0
    if message.text == "Отмена":
        bot.send_message(
            message.chat.id, "Добавление сервиса отменено",
            reply_markup=ReplyKeyboardRemove()
        )
        return 0
    config['platform'][service_type]['services'].append(message.text)
    with open(path, 'w', encoding='utf8') as outfile:
        yaml.dump(config, outfile, default_flow_style=False, allow_unicode=True)
    bot.send_message(message.chat.id, "Сервис добавлен", reply_markup=ReplyKeyboardRemove())


@bot.message_handler(commands=['deleteservice'])
def delete_os_message(message):
    using_bot_counter.labels(message.text, message.from_user.id, message.from_user.full_name).inc()
    logging.info(f"{datetime.datetime.now().strftime('%d-%m-%Y %H:%M')}. "
                 f"{message.text}, {message.from_user.id}, {message.from_user.full_name}")
    keyboard = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
    service_types = config['platform'].keys()
    for type_service in service_types:
        button = KeyboardButton(text=type_service)
        keyboard.add(button)
    button = KeyboardButton(text="Отмена")
    keyboard.add(button)
    bot.send_message(message.chat.id, "Выберите тип сервисов", reply_markup=keyboard)
    bot.register_next_step_handler(message, service_type_delete)


def service_type_delete(message):
    if message.text.startswith("/"):
        bot.send_message(message.chat.id, "Неверное значение", reply_markup=ReplyKeyboardRemove())
        return 0
    if message.text == "Отмена":
        bot.send_message(message.chat.id, "Отменено", reply_markup=ReplyKeyboardRemove())
        return 0
    bot.send_message(message.chat.id, "Тип выбран", reply_markup=ReplyKeyboardRemove())
    keyboard = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    services_list = config['platform'][message.text]['services']
    for service in services_list:
        button = KeyboardButton(text=service)
        keyboard.add(button)
    button = KeyboardButton(text="Отмена")
    keyboard.add(button)
    bot.send_message(message.chat.id, "Выберите сервис для удаления", reply_markup=keyboard)
    bot.register_next_step_handler(message, delete_os, service_type=message.text)


def delete_os(message, service_type):
    if message.text.startswith("/"):
        bot.send_message(message.chat.id, "Неверное значение", reply_markup=ReplyKeyboardRemove())
        return 0
    if message.text == "Отмена":
        bot.send_message(message.chat.id, "Удаление сервиса отменено", reply_markup=ReplyKeyboardRemove())
        return 0
    config['platform'][service_type]['services'].remove(message.text)
    with open(path, 'w', encoding='utf8') as outfile:
        yaml.dump(config, outfile, default_flow_style=False, allow_unicode=True)
    bot.send_message(message.chat.id, "Сервис удален", reply_markup=ReplyKeyboardRemove())


# @bot.message_handler(commands=['survey'])
# def survey_message(message):
#     using_bot_counter.labels(message.text, message.from_user.id, message.from_user.full_name).inc()
#     logging.info(f"{datetime.datetime.now().strftime('%d-%m-%Y %H:%M')}. "
#                  f"{message.text}, {message.from_user.id}, {message.from_user.full_name}")
#     keyboard = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
#     service_types = config['platform'].keys()
#     for type_service in service_types:
#         button = KeyboardButton(text=type_service)
#         keyboard.add(button)
#     button = KeyboardButton(text="Отмена")
#     keyboard.add(button)
#     bot.send_message(message.chat.id, "Выберите команду", reply_markup=keyboard)
#     bot.register_next_step_handler(message, team_type_survey)
#
#
# def team_type_survey(message):
#     if message.text.startswith("/"):
#         bot.send_message(message.chat.id, "Неверное значение", reply_markup=ReplyKeyboardRemove())
#         return 0
#     if message.text == "Отмена":
#         bot.send_message(message.chat.id, "Отменено", reply_markup=ReplyKeyboardRemove())
#         return 0
#     bot.send_message(message.chat.id, "Команда выбрана", reply_markup=ReplyKeyboardRemove())
#     button_list = generate_buttons(config['platform'][message.text]['users'], ok_text="Да", fail_text="Нет")
#     reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=3))
#     bot.send_message(message.chat.id, "Опрос", reply_markup=reply_markup)


@bot.callback_query_handler(
    func=lambda call: call.data.endswith('ok') or call.data.endswith('fail') or call.data.endswith('otm'))
def query_handler(call):
    bot.answer_callback_query(callback_query_id=call.id, text='')
    if call.message.html_text == "Статус сервисов":
        ok_text = "Успешно"
        fail_text = "Ошибки"
    else:
        ok_text = "Да"
        fail_text = "Нет"
    buttons: list = update_buttons(
        call.message.json['reply_markup']['inline_keyboard'],
        change=call.data,
        ok_text=ok_text,
        fail_text=fail_text
    )
    reply_markup = InlineKeyboardMarkup(build_menu(buttons, n_cols=3))
    bot.edit_message_text(
        text=call.message.html_text,
        chat_id=call.message.chat.id,
        message_id=call.message.id,
        reply_markup=reply_markup
    )


@bot.callback_query_handler(func=lambda call: call.data.endswith('zni'))
def query_handler(call):
    bot.answer_callback_query(callback_query_id=call.id, text='')
    zni_status, msg_id, system_zni, mnemo_system_zni, number_zni, platform_zni, _ = call.data.split('_')
    if platform_zni == 'OS':
        platform_zni = "#Общие_сервисы"
    elif platform_zni == 'SS':
        platform_zni = "Служебные_сервисы"
    elif platform_zni == 'EPA':
        platform_zni = "ЕПА"
    else:
        platform_zni = 'УИП'
    msg_text = f"{platform_zni}\nСервис {system_zni} {mnemo_system_zni}\nРаботы по ЗНИ C-{number_zni}"
    if zni_status == "ok":
        msg = bot.edit_message_text(
            text="Работы завершены. Не забудьте закрыть ЗНИ.",
            chat_id=call.message.chat.id,
            message_id=call.message.id,
            reply_markup=InlineKeyboardMarkup([])
        )
        bot.send_message(omni_chat_id, f"{msg_text} завершены успешно", reply_to_message_id=msg_id)
    elif zni_status == "partially":
        msg = bot.edit_message_text(
            text="Опишите причину",
            chat_id=call.message.chat.id,
            message_id=call.message.id,
            reply_markup=InlineKeyboardMarkup([])
        )
        msg_text = f"{msg_text} завершены частично"
        bot.register_next_step_handler(msg, reason_of_failed_work, msg_text=msg_text, msg_id=msg_id)
    else:
        msg = bot.edit_message_text(
            text="Опишите причину",
            chat_id=call.message.chat.id,
            message_id=call.message.id,
            reply_markup=InlineKeyboardMarkup([])
        )
        msg_text = f"{msg_text} завершены с ошибками"
        bot.register_next_step_handler(msg, reason_of_failed_work, msg_text=msg_text, msg_id=msg_id)


def reason_of_failed_work(message, msg_text, msg_id):
    bot.send_message(
        omni_chat_id,
        f"{msg_text}\nПричина: {message.text}",
        reply_to_message_id=msg_id
    )
    bot.send_message(message.chat.id, f"Работы завершены. Не забудьте закрыть ЗНИ.")


@bot.callback_query_handler(func=lambda call: call.data.startswith('generate_report'))
def query_handler(call):
    bot.answer_callback_query(callback_query_id=call.id, text='')
    report_message = generate_report(call.message.json['reply_markup']['inline_keyboard'])
    if call.message.json['text'] == "Опрос":
        change_type = 'survey'
    else:
        change_type = 'service'
    buttons = [InlineKeyboardButton("Изменить", callback_data=f"change_{change_type}"), ]
    reply_markup = InlineKeyboardMarkup(build_menu(buttons, n_cols=3))
    bot.edit_message_text(
        text=report_message,
        chat_id=call.message.chat.id,
        message_id=call.message.id,
        reply_markup=reply_markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('change'))
def query_handler(call):
    bot.answer_callback_query(callback_query_id=call.id, text='')
    _, change_type = call.data.split('_')
    if change_type == 'survey':
        ok_text = "Да"
        fail_text = "Нет"
        msg_text = "Опрос"
    else:
        ok_text = "Успешно"
        fail_text = "Ошибки"
        msg_text = "Статус сервисов"
    buttons: list = []
    idx = 0
    names = call.message.text.split('\n')
    for item in names:
        idx += 1
        name, status = item.split('->')
        name = name.rstrip()
        buttons.append(InlineKeyboardButton(name, callback_data=idx))
        status = status.lstrip()
        if status == "?":
            buttons.append(InlineKeyboardButton(ok_text, callback_data=f"{idx}_ok"))
            buttons.append(InlineKeyboardButton(fail_text, callback_data=f"{idx}_fail"))
        elif status == '✅':
            buttons.append(InlineKeyboardButton("✅", callback_data=f"{idx}_status"))
            buttons.append(InlineKeyboardButton("Отмена", callback_data=f"{idx}_otm"))
        elif status == '❌':
            buttons.append(InlineKeyboardButton("❌", callback_data=f"{idx}_status"))
            buttons.append(InlineKeyboardButton("Отмена", callback_data=f"{idx}_otm"))
    buttons.append(InlineKeyboardButton("Сгенерировать отчет", callback_data=f"generate_report"))
    reply_markup = InlineKeyboardMarkup(build_menu(buttons, n_cols=3))
    bot.edit_message_text(
        text=msg_text,
        chat_id=call.message.chat.id,
        message_id=call.message.id,
        reply_markup=reply_markup
    )


# prometheus_client.start_http_server(9300)
bot.infinity_polling()
