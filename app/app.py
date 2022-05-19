from pathlib import Path
import re
import telebot
from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)
from configparser import ConfigParser
import yaml

parser = ConfigParser()
parser.read(Path('init.ini').absolute())
telegram_api_token = parser['telegram']['telegram_api_token']
omni_chat_id = parser['telegram']['omni_chat_id']
bot = telebot.TeleBot(token=telegram_api_token)
path: Path = Path(f"{Path.cwd()}/config.yaml").absolute()
with open(path, 'r') as stream:
    config = yaml.safe_load(stream)


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


@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, "'osstatus' для меню статуса сервисов")


@bot.message_handler(commands=['status'])
def status_message(message):
    keyboard = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
    service_types = config['platform'].keys()
    for type_service in service_types:
        button = KeyboardButton(text=type_service)
        keyboard.add(button)
    button = KeyboardButton(text="Отмена")
    keyboard.add(button)
    bot.send_message(message.chat.id, "Выберите тип сервисов", reply_markup=keyboard)
    bot.register_next_step_handler(message, service_type_status)


def service_type_status(message):
    if message.text.startswith("/"):
        bot.send_message(message.chat.id, "Неверное значение", reply_markup=ReplyKeyboardRemove())
        return 0
    if message.text == "Отмена":
        bot.send_message(message.chat.id, "Отменено", reply_markup=ReplyKeyboardRemove())
        return 0
    bot.send_message(message.chat.id, "Тип выбран", reply_markup=ReplyKeyboardRemove())
    buttons: list = generate_buttons(config['platform'][message.text]['services'])
    reply_markup = InlineKeyboardMarkup(build_menu(buttons, n_cols=3))
    bot.send_message(message.chat.id, "Статус сервисов", reply_markup=reply_markup)


@bot.message_handler(commands=['list'])
def list_message(message):
    print(message.chat.id)
    keyboard = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
    service_types = config['platform'].keys()
    for type_service in service_types:
        button = KeyboardButton(text=type_service)
        keyboard.add(button)
    button = KeyboardButton(text="Отмена")
    keyboard.add(button)
    bot.send_message(message.chat.id, "Выберите тип сервисов", reply_markup=keyboard)
    bot.register_next_step_handler(message, service_type_list)


def service_type_list(message):
    if message.text.startswith("/"):
        bot.send_message(message.chat.id, "Неверное значение", reply_markup=ReplyKeyboardRemove())
        return 0
    if message.text == "Отмена":
        bot.send_message(message.chat.id, "Отменено", reply_markup=ReplyKeyboardRemove())
        return 0
    bot.send_message(message.chat.id, "Тип выбран", reply_markup=ReplyKeyboardRemove())
    services_list = config['platform'][message.text]['services']
    str_service_list = '\n'.join(services_list)
    bot.send_message(message.chat.id, str_service_list)


@bot.message_handler(commands=['zni'])
def zni_message(message):
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
        number_zni=number_zni
    )


def zni_platform(message, number_zni):
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
        platform_zni=message.text
    )


def zni_system(message, number_zni, platform_zni):
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
        platform_zni=platform_zni,
        system_zni=message.text
    )


def zni_monitoring_influence(message, number_zni, platform_zni, system_zni):
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
        platform_zni=platform_zni,
        system_zni=system_zni,
        monitoring_influence_zni=message.text
    )


def zni_consumer_influence(message, number_zni, platform_zni, system_zni, monitoring_influence_zni):
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
        platform_zni=platform_zni,
        system_zni=system_zni,
        monitoring_influence_zni=monitoring_influence_zni,
        consumer_influence_zni=message.text
    )


def zni_description_of_the_work(message, number_zni, platform_zni, system_zni, monitoring_influence_zni, consumer_influence_zni):
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
    formatted_string = f"{platform_zni}\n" \
                       f"Начало работ по ЗНИ {number_zni}\n" \
                       f"Сервис: {system_zni}\n{description_of_the_work}"\
                       f"Влияние на мониторинг: {monitoring_influence_zni}\n" \
                       f"Влияние на потребителей: {consumer_influence_zni}\n" \
                       f"Ответственный: {message.chat.first_name} {message.chat.last_name} @{message.chat.username}"
    msg = bot.send_message(omni_chat_id, formatted_string, reply_markup=ReplyKeyboardRemove())
    omni_msg_id = msg.id
    buttons: list = [InlineKeyboardButton("Завершить работы", callback_data=f"ok_{omni_msg_id}_zni"),
                     InlineKeyboardButton("Завершить с ошибкой", callback_data=f"fail_{omni_msg_id}_zni")]
    keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=2))
    bot.send_message(
        message.chat.id,
        f"Готово",
        reply_markup=ReplyKeyboardRemove()
    )
    bot.send_message(
        message.chat.id,
        f"Сообщение отправлено в чат 'Поддержка Omni':\n{formatted_string}",
        reply_markup=keyboard
    )


@bot.message_handler(commands=['addservice'])
def add_service_message(message):
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


@bot.message_handler(commands=['survey'])
def survey_message(message):
    keyboard = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
    service_types = config['platform'].keys()
    for type_service in service_types:
        button = KeyboardButton(text=type_service)
        keyboard.add(button)
    button = KeyboardButton(text="Отмена")
    keyboard.add(button)
    bot.send_message(message.chat.id, "Выберите команду", reply_markup=keyboard)
    bot.register_next_step_handler(message, team_type_survey)


def team_type_survey(message):
    if message.text.startswith("/"):
        bot.send_message(message.chat.id, "Неверное значение", reply_markup=ReplyKeyboardRemove())
        return 0
    if message.text == "Отмена":
        bot.send_message(message.chat.id, "Отменено", reply_markup=ReplyKeyboardRemove())
        return 0
    bot.send_message(message.chat.id, "Команда выбрана", reply_markup=ReplyKeyboardRemove())
    button_list = generate_buttons(config['platform'][message.text]['users'], ok_text="Да", fail_text="Нет")
    reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=3))
    bot.send_message(message.chat.id, "Опрос", reply_markup=reply_markup)


@bot.callback_query_handler(func=lambda call: call.data.endswith('ok') or call.data.endswith('fail'))
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
    zni_status, msg_id, _ = call.data.split('_')
    if zni_status == "ok":
        bot.send_message(omni_chat_id, "Работы завершены успешно", reply_to_message_id=msg_id)
    else:
        bot.send_message(omni_chat_id, "Работы завершены с ошибками", reply_to_message_id=msg_id)
    bot.edit_message_text(
        text="Работы завершены. Не забудьте закрыть ЗНИ.",
        chat_id=call.message.chat.id,
        message_id=call.message.id,
        reply_markup=InlineKeyboardMarkup([])
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('generate_report'))
def query_handler(call):
    bot.answer_callback_query(callback_query_id=call.id, text='')
    report_message = generate_report(call.message.json['reply_markup']['inline_keyboard'])
    buttons = [InlineKeyboardButton("Изменить", callback_data=f"change"), ]
    reply_markup = InlineKeyboardMarkup(build_menu(buttons, n_cols=3))
    bot.edit_message_text(
        text=report_message,
        chat_id=call.message.chat.id,
        message_id=call.message.id,
        reply_markup=reply_markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('change'))
def query_handler(call):
    bot.answer_callback_query(callback_query_id=call.id, text='изменить')
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
            buttons.append(InlineKeyboardButton("Успешно", callback_data=f"{idx}_ok"))
            buttons.append(InlineKeyboardButton("Ошибки", callback_data=f"{idx}_fail"))
        elif status == '✅':
            buttons.append(InlineKeyboardButton("✅", callback_data=f"{idx}_status"))
            buttons.append(InlineKeyboardButton("Отмена", callback_data=f"{idx}_otm"))
        elif status == '❌':
            buttons.append(InlineKeyboardButton("❌", callback_data=f"{idx}_status"))
            buttons.append(InlineKeyboardButton("Отмена", callback_data=f"{idx}_otm"))
    buttons.append(InlineKeyboardButton("Сгенерировать отчет", callback_data=f"generate_report"))
    reply_markup = InlineKeyboardMarkup(build_menu(buttons, n_cols=3))
    bot.edit_message_text(
        text="Статус сервисов",
        chat_id=call.message.chat.id,
        message_id=call.message.id,
        reply_markup=reply_markup
    )


bot.infinity_polling()
