import telebot
import requests
import psycopg2
import os
import linecache
import sys
import json
import time
import schedule
from threading import Thread
from datetime import datetime, timedelta


def validator():
    if os.environ.get('TOKEN') is None:
        print("Не найдена переменная 'TOKEN'. Завершение работы...")
        exit(0)
    if os.environ.get('DB_host') is None:
        print("Не найдена переменная 'DB_host'. Завершение работы...")
        exit(0)
    if os.environ.get('DB') is None:
        print("Не найдена переменная 'DB'. Завершение работы...")
        exit(0)
    if os.environ.get('DB_user') is None:
        print("Не найдена переменная 'DB_user'. Завершение работы...")
        exit(0)
    if os.environ.get('DB_port') is None:
        print("Не найдена переменная 'DB_port'. Завершение работы...")
        exit(0)
    if os.environ.get('DB_pass') is None:
        print("Не найдена переменная 'DB_pass'. Завершение работы...")
        exit(0)


validator()
bot = telebot.TeleBot("1074352529:AAEIKKcGDpFtQt-7NNm0EYnxZiau9oARZAo")
sm = "🤖"
group_list = []
admins_list = [496537969]
commands = ["сегодня", "завтра", "на неделю"]
day_dict = {"monday": "Понедельник",
            "tuesday": "Вторник",
            "wednesday": "Среда",
            "thursday": "Четверг",
            "friday": "Пятница",
            "saturday": "Суббота",
            "sunday": "Воскресенье"}
lesson_dict = {"9:": "1", "10": "2", "12": "3", "14": "4", "16": "5", "18": "6", "19": "7", "20": "8"}
time_dict = {"9:": "🕘", "10": "🕦", "12": "🕐", "14": "🕝", "16": "🕟", "18": "🕕", "19": "🕢", "20": "🕘"}
delimiter = "------------------------------------------------"
time_difference = 3
response = ""
print(bot.get_me())


def isAdmin(user_id):
    return True if user_id in admins_list else False


def db_connect():
    try:
        con = psycopg2.connect(
            host="ec2-52-203-27-62.compute-1.amazonaws.com",
            database="db62eo9863hsjs",
            user="vsuxnhiqqiiwfy",
            port="5432",
            password="86498c5bcccc94d6c10b6fc89e13b786138b3575e1d7a9d8def1c873c50d7743"
        )
        cur = con.cursor()
        return con, cur
    except Exception as er:
        print(er)
        return None, None


def create_tables():
    try:
        print("Создание таблиц...")
        connect, cursor = db_connect()
        if connect is None or cursor is None:
            print("Я потерял БД, кто найдет оставьте на охране (не получилось подключиться к бд)")
            return
        cursor.execute("CREATE TABLE IF NOT EXISTS users(username TEXT, first_name TEXT,"
                       "last_name TEXT, grp TEXT, ids BIGINT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS errors(reason TEXT)")
        cursor.execute("SELECT COUNT(ids) FROM users")
        print(f"Пользователей в базе {cursor.fetchone()[0]}")
        connect.commit()
        cursor.close()
        connect.close()
        print("Таблицы успешно созданы")
    except Exception as er:
        print(er)


def error_log(er):
    try:
        if "string indices must be integers" in str(er):
            return
        exc_type, exc_obj, tb = sys.exc_info()
        frame = tb.tb_frame
        linenos = tb.tb_lineno
        filename = frame.f_code.co_filename
        linecache.checkcache(filename)
        line = linecache.getline(filename, linenos, frame.f_globals)
        local_time = datetime.now() + timedelta(hours=3)
        if "line 1 column 1" in str(er):
            global response
            reason = f"{local_time} EXCEPTION IN ({filename}, LINE {linenos} '{line.strip()}'): {str(response)}"
        else:
            reason = f"{local_time} EXCEPTION IN ({filename}, LINE {linenos} '{line.strip()}'): {exc_obj}"
        connect, cursor = db_connect()
        temp_date = correctTimeZone()
        cursor.execute(f"INSERT INTO Errors VALUES($taG${reason}$taG$)")
        connect.commit()
        cursor.close()
        connect.close()
        print(f"{delimiter}\n{temp_date}\n{reason}\n")
    except Exception as er:
        print(f"{er} ошибка в обработчике ошибок. ЧТО?")


def log(message):
    try:
        local_time = correctTimeZone()
        msg = message.text
        if message.from_user.username is not None:
            name = f"{message.from_user.username}"
        else:
            name = f"{message.from_user.first_name} {message.from_user.last_name}"
        print(f"{delimiter}\n{local_time}\nСообщение от {name}, (id = {message.from_user.id})\nТекст - {msg}")
    except Exception as er:
        error_log(er)


def correctTimeZone():
    try:
        curr_time = datetime.now() + timedelta(hours=time_difference)
        return str(curr_time.strftime("%d.%m.%Y %H:%M:%S"))
    except Exception as er:
        error_log(er)


@bot.message_handler(commands=['users'])
def handler_db(message):
    sql_request = "COPY (SELECT * FROM users) TO STDOUT WITH CSV HEADER"
    if isAdmin(message.from_user.id):
        connect, cursor = db_connect()
        if connect is None or cursor is None:
            bot.send_message(message.from_user.id, f"{sm}Я потерял БД, кто найдет оставьте на охране и повторите "
                                                   f"попытку позже")
            return
        with open("temp/users.csv", "w") as output_file:
            cursor.copy_expert(sql_request, output_file)
        with open("temp/users.csv", "rb") as doc:
            bot.send_document(chat_id=message.from_user.id, data=doc)
        os.remove("temp/users.csv")
        connect.commit()
        cursor.close()
        connect.close()


@bot.message_handler(commands=['errors'])
def handler_errors(message):
    try:
        sql_request = "COPY (SELECT * FROM errors) TO STDOUT WITH CSV HEADER"
        if isAdmin(message.from_user.id):
            connect, cursor = db_connect()
            if connect is None or cursor is None:
                bot.send_message(message.from_user.id, f"{sm}Я потерял БД, кто найдет оставьте на охране и повторите "
                                                       f"попытку позже")
                return
            with open("temp/errors.csv", "w") as output_file:
                cursor.copy_expert(sql_request, output_file)
            with open("temp/errors.csv", "rb") as doc:
                bot.send_document(chat_id=message.from_user.id, data=doc)
            os.remove("temp/errors.csv")
            cursor.execute("DELETE FROM errors")
            connect.commit()
            isolation_level = connect.isolation_level
            connect.set_isolation_level(0)
            cursor.execute("VACUUM FULL")
            connect.set_isolation_level(isolation_level)
            connect.commit()
            cursor.close()
            connect.close()
    except Exception as er:
        error_log(er)


@bot.message_handler(commands=['start'])
def handler_start(message):
    user_id = message.from_user.id if message.chat.type == "private" else message.chat.id
    print(f"{user_id} {message.from_user.username} {message.text}")
    try:
        user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
        user_markup.row("сегодня", "завтра", "на неделю")
        text = f"<b>{sm}Камнями кидаться <a href='t.me/delivery_klad'>СЮДА</a></b>\n" \
               f"/group (+группа если бот в беседе)- установить/изменить группу\n" \
               f"/today - расписание на сегодня\n" \
               f"/tomorrow - расписание на завтра\n" \
               f"/week - расписание на неделю\n" \
               f"/next_week - расписание на следующую неделю\n" \
               f"/weeknum номер недели - получить расписание на неделю по ее номеру"
        if message.chat.type == "private":
            bot.send_message(message.from_user.id, text, reply_markup=user_markup, parse_mode="HTML",
                             disable_web_page_preview=True)
        else:
            bot.send_message(message.chat.id, text, parse_mode="HTML",
                             disable_web_page_preview=True)
    except Exception as er:
        error_log(er)
        try:
            bot.send_message(user_id, f"{sm}А ой, ошиб04ка")
        except Exception as err:
            error_log(err)


@bot.message_handler(commands=['group'])
def handler_group(message):
    user_id = message.from_user.id if message.chat.type == "private" else message.chat.id
    print(f"{user_id} {message.from_user.username} {message.text}")
    try:
        if message.chat.type == "private":
            if message.from_user.id not in group_list:
                try:
                    group = message.text.split(" ", 1)[1]
                    set_group(message, message.from_user.id, group.upper())
                    return
                except IndexError:
                    group_list.append(message.from_user.id)
            bot.send_message(message.from_user.id, f"{sm}Напишите вашу группу")
        else:
            try:
                group = message.text.split(" ", 1)[1]
                set_group(message, message.chat.id, group.upper())
            except IndexError:
                bot.send_message(message.chat.id, f"{sm}/group (группа)")
    except Exception as er:
        error_log(er)
        try:
            bot.send_message(user_id, f"{sm}А ой, ошиб04ка")
        except Exception as err:
            error_log(err)


def cache():
    print("Caching schedule...")
    failed, local_groups = 0, 0
    try:
        os.mkdir("cache")
    except FileExistsError:
        pass
    try:
        connect, cursor = db_connect()
        if connect is None or cursor is None:
            bot.send_message(admins_list[0], f"{sm}Я потерял БД, кто найдет оставьте на охране и повторите попытку позже")
            return
        cursor.execute("SELECT DISTINCT grp FROM users")
        local_groups = cursor.fetchall()
        for i in local_groups:
            res = requests.get(f"https://schedule-rtu.rtuitlab.dev/api/schedule/{i[0]}/week")
            if res.status_code != 200:
                failed += 1
                print(f"Caching failed {res} Group '{i[0]}'")
            else:
                print(f"Caching success {res} Group '{i[0]}'")
                lessons = res.json()
                with open(f"cache/{i[0]}.json", "w") as file:
                    json.dump(lessons, file)
                time.sleep(0.1)
        bot.send_message(admins_list[0], f"Caching success! \n{failed}/{len(local_groups)} failed")
        try:
            with open("cache/ИКБО-08-18.json", "rb") as doc:
                bot.send_document(admins_list[0], doc)
        except Exception as er:
            error_log(er)
    except Exception as er:
        error_log(er)
    if failed == len(local_groups):
        time.sleep(3600)
        cache()


def sort_days(days):
    temp, day = [], ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for i in days:
        temp.append(day.index(i))
    temp.sort()
    days, index = [], 10
    for i in temp:
        days.append(day[i])
    return days


def number_of_lesson(lsn):
    global lesson_dict
    try:
        return f"{lesson_dict[lsn[:2]]} пара"
    except KeyError:
        return "? пара"


def get_teacher_icon(name):
    try:
        symbol = name.split(' ', 1)[0]
        return "👩‍🏫" if symbol[len(symbol) - 1] == "а" else "👨‍🏫"
    except IndexError:
        return ""


def get_time_icon(local_time):
    global time_dict
    try:
        return time_dict[local_time[:2]]
    except Exception as er:
        error_log(er)
        return "🕐"


def set_group(message, user_id, group):
    try:
        connect, cursor = db_connect()
        valid_group = group.split("-")
        if len(valid_group) < 3:
            bot.send_message(user_id, f"{sm}Неверный формат группы")
            return
        if not valid_group[1].isnumeric() and not valid_group[2].isnumeric():
            bot.send_message(user_id, f"{sm}Неверный формат группы")
            return
        if connect is None or cursor is None:
            bot.send_message(user_id, f"{sm}Я потерял БД, кто найдет оставьте на охране и повторите попытку позже")
            return
        cursor.execute(f"SELECT count(ids) FROM users WHERE ids={user_id}")
        res = cursor.fetchall()[0][0]
        if res == 0:
            cursor.execute(
                f"INSERT INTO users VALUES($taG${message.from_user.username}$taG$,"
                f"$taG${message.from_user.first_name}$taG$, $taG${message.from_user.last_name}$taG$, "
                f"$taG${group}$taG$, {user_id})")
        else:
            cursor.execute(f"UPDATE users SET grp=$taG${group}$taG$ WHERE ids={user_id}")
        connect.commit()
        cursor.close()
        connect.close()
        bot.send_message(user_id, f"{sm}Я вас запомнил")
        try:
            group_list.pop(group_list.index(user_id))
        except Exception as er:
            if "is not in list" not in str(er):
                error_log(er)
    except Exception as er:
        error_log(er)
        bot.send_message(user_id, f"{sm}А ой, ошиб04ка")


@bot.message_handler(commands=['which_week'])
def get_week(message):
    try:
        week = int((datetime.now() + timedelta(hours=time_difference)).strftime("%V"))
        if week < 39:
            week -= 5
        else:
            week -= 38
        bot.send_message(message.chat.id, f"<b>{week}</b> неделя", parse_mode="HTML")
    except Exception as er:
        error_log(er)


def get_schedule(day, group, title):
    global response
    res = requests.get(f"https://schedule-rtu.rtuitlab.dev/api/schedule/{group}/{day}")
    response = res
    lessons = res.json()
    group_schedule = title
    for i in lessons:
        j, o = i['lesson'], i['time']
        try:
            group_schedule += f"<b>{number_of_lesson(o['start'])} (<code>{j['classRoom']}</code>" \
                              f"{get_time_icon(o['start'])}{o['start']} - {o['end']})</b>\n{j['name']} " \
                              f"({j['type']})\n{get_teacher_icon(j['teacher'])} {j['teacher']}\n\n"
        except TypeError:
            pass
        except Exception as er:
            error_log(er)
    return group_schedule


def get_week_schedule(user_id, week, group):
    global response
    day = datetime.today().weekday()
    res = requests.get(f"https://schedule-rtu.rtuitlab.dev/api/schedule/{group}/{week}")
    response = str(res)
    try:
        lessons = res.json()
    except Exception as er:
        if "line 1 column 1" in str(er):
            text = "Сегодня воскресенье" if day == 6 else "Не удается связаться с API\nПроверяю кэшированное расписание"
            bot.send_message(user_id, f"{sm}<b>{text}</b>", parse_mode="HTML")
    if res.status_code == 503:
        try:
            print(f"Поиск кэшированного расписания для группы '{group}'")
            with open(f"cache/{group}.json") as file:
                lessons = json.load(file)
        except FileNotFoundError:
            bot.send_message(user_id, f"{sm}Кэшированое расписание для вашей группы не найдено")
            return
    rez, days = "", []
    try:
        for i in lessons:
            days.append(i)
        days = sort_days(days)
        for i in days:
            rez += f"<b>{day_dict[i]}\n</b>"
            for k in lessons[i]:
                j, o = k['lesson'], k['time']
                try:
                    rez += f"<b>{number_of_lesson(o['start'])} (<code>{j['classRoom']}</code>" \
                           f"{get_time_icon(o['start'])}{o['start']} - {o['end']})</b>\n{j['name']} " \
                           f"({j['type']})\n{get_teacher_icon(j['teacher'])} {j['teacher']}\n\n"
                except TypeError:
                    pass
                except Exception as er:
                    error_log(er)
            rez += "------------------------\n"
    except Exception as er:
        error_log(er)
        try:
            bot.send_message(user_id, f"{sm}А ой, ошиб04ка")
        except Exception as err:
            error_log(err)
    if len(rez) > 50:
        bot.send_message(user_id, rez, parse_mode="HTML")
    else:
        bot.send_message(user_id, f"{sm}<b>Пар не обнаружено</b>", parse_mode="HTML")


@bot.message_handler(content_types=['text'])
def handler_text(message):
    print(f"{message.from_user.id} {message.from_user.username} {message.text}")
    group = ""
    try:
        if message.from_user.id in group_list:
            if "/" in message.text or message.text in commands:
                bot.send_message(message.from_user.id, f"{sm}НАПИШИТЕ ВАШУ ГРУППУ")
                return
            set_group(message, message.from_user.id, message.text.upper())
        elif message.text[0] == "/" or message.text.lower() in commands:
            day = datetime.today().weekday()
            user_id = message.from_user.id if message.chat.type == "private" else message.chat.id
            text = "/group" if message.chat.type == "private" else "/group (группа)"
            try:
                connect, cursor = db_connect()
                if connect is None or cursor is None:
                    bot.send_message(admins_list[0],
                                     f"{sm}Я потерял БД, кто найдет оставьте на охране и повторите попытку позже")
                    return
                cursor.execute(f"SELECT grp FROM users WHERE ids={user_id}")
                try:
                    group = cursor.fetchone()[0]
                    cursor.close()
                    connect.close()
                except TypeError:
                    bot.send_message(user_id, f"{sm}У вас не указана группа\n{text}, чтобы указать группу")
                    return
                except Exception as er:
                    error_log(er)
            except Exception as er:
                error_log(er)
                try:
                    bot.send_message(user_id, f"{sm}Не удается получить вашу группу\n{text}, чтобы указать группу")
                except Exception as err:
                    error_log(err)
                return
            if "today" in message.text.lower() or commands[0] in message.text.lower():
                try:
                    group_schedule = get_schedule("today", group, "<b>Пары сегодня:\n</b>")
                    if len(group_schedule) > 50:
                        bot.send_message(user_id, group_schedule, parse_mode="HTML")
                    else:
                        bot.send_message(user_id, f"{sm}<b>Пар не обнаружено</b>", parse_mode="HTML")
                except Exception as er:
                    if "line 1 column 1" in str(er):
                        text = "Сегодня воскресенье" if day == 6 else "Не удается связаться с API\n/week - чтобы " \
                                                                      "посмотреть кэшированное расписание на " \
                                                                      "текущую неделю"
                        bot.send_message(user_id, f"{sm}<b>{text}</b>", parse_mode="HTML")
                    error_log(er)
            elif "tomorrow" in message.text.lower() or commands[1] in message.text.lower():
                try:
                    group_schedule = get_schedule("tomorrow", group, "<b>Пары завтра:\n</b>")
                    if len(group_schedule) > 50:
                        bot.send_message(user_id, group_schedule, parse_mode="HTML")
                    else:
                        bot.send_message(user_id, f"{sm}<b>Пар не обнаружено</b>", parse_mode="HTML")
                except Exception as er:
                    if "line 1 column 1" in str(er):
                        text = "Сегодня воскресенье" if day == 5 else "Не удается связаться с API\n/week - чтобы " \
                                                                      "посмотреть кэшированное расписание на " \
                                                                      "текущую неделю"
                        bot.send_message(user_id, f"{sm}<b>{text}</b>", parse_mode="HTML")
                    error_log(er)
            elif "next_week" in message.text.lower():
                try:
                    get_week_schedule(user_id, "next_week", group)
                except Exception as er:
                    if "line 1 column 1" in str(er):
                        text = "Сегодня воскресенье" if day == 6 else "Не удается связаться с API\n/week - чтобы " \
                                                                      "посмотреть кэшированное расписание на " \
                                                                      "текущую неделю"
                        bot.send_message(user_id, f"{sm}<b>{text}</b>", parse_mode="HTML")
                    error_log(er)
            elif "weeknum" in message.text.lower():
                try:
                    week = int(message.text.split()[1])
                    get_week_schedule(user_id, f"{week}/week_num", group)
                except Exception as er:
                    if "line 1 column 1" in str(er):
                        text = "Сегодня воскресенье" if day == 6 else "Не удается связаться с API\n/week - чтобы " \
                                                                      "посмотреть кэшированное расписание на " \
                                                                      "текущую неделю"
                        bot.send_message(user_id, f"{sm}<b>{text}</b>", parse_mode="HTML")
                    else:
                        bot.send_message(user_id, f"{sm}<b>Неверный ввод</b>", parse_mode="HTML")
                    error_log(er)
            elif "week" in message.text.lower() or commands[2] in message.text.lower():
                try:
                    get_week_schedule(user_id, "week", group)
                except Exception as er:
                    error_log(er)
        elif "week" in message.text.lower() or "неделя" in message.text.lower():
            get_week(message)
        else:
            if message.chat.type == "private":
                bot.send_message(message.from_user.id, f"{sm}<b>Я вас не понял</b>", parse_mode="HTML")
    except Exception as er:
        error_log(er)


def create_thread():
    while True:
        schedule.run_pending()


create_tables()
start_cache = Thread(target=cache)
start_cache.start()
schedule.every().day.at("23:45").do(cache)
cache_thread = Thread(target=create_thread)
print("Расписание кэширования создано!")
cache_thread.start()
print("Бот запущен!")
try:
    while True:
        try:
            bot.polling(none_stop=True, interval=0)
        except Exception as e:
            print(e)
except Exception as e:
    print(e)
