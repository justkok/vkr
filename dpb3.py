from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
import sqlite3
from datetime import timedelta
import asyncio
import logging
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler
import aiosqlite
import sys
from telegram import CallbackQuery

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO)
# Состояния для сбора информации
NAME, FOLLOWERS, UPDATE_FOLLOWERS,BLOG_THEME, ADD_IDEA, ADD_TASK, BROADCAST, START_BROADCAST, WAIT_BROADCAST_MESSAGE = range(9)
SEND_BROADCAST_TEXT = 10

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_debug.log'),  # Запись в файл
        logging.StreamHandler()  # Вывод в консоль
    ]
)

# ID администратора
ADMIN_ID = 700013214

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
   # Создаем таблицу пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            followers INTEGER NOT NULL,
            blog_theme TEXT NOT NULL,
            registered_at TEXT NOT NULL
        )
    ''')
    # Таблица идей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ideas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idea TEXT NOT NULL,
            theme TEXT NOT NULL
        )
    ''')
    # Обновляем таблицу заданий
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            theme TEXT NOT NULL
        )              
    ''')
    conn.commit()
    conn.close()
    

def get_random_idea_by_theme(theme: str):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT idea FROM ideas WHERE theme = ? ORDER BY RANDOM() LIMIT 1', (theme,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def get_random_task_by_theme(theme: str):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT task FROM tasks WHERE theme = ? ORDER BY RANDOM() LIMIT 1', (theme,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None





async def debug_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info(f"Получено сообщение: {update.message.text}")

#меню тем при выборе добавлении задания и идеи
async def show_theme_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info(f"=== Показ меню тем ===")
    logging.info(f"Флаги: adding_idea={context.user_data.get('adding_idea')}, adding_task={context.user_data.get('adding_task')}")
    query = update.callback_query if hasattr(update, 'callback_query') else update
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Личный блог", callback_data="theme_personal")],
        [InlineKeyboardButton("Спорт", callback_data="theme_sports")],
        [InlineKeyboardButton("Психология", callback_data="theme_psychology")],
        [InlineKeyboardButton("Технологии", callback_data="theme_technology")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if context.user_data.get('adding_idea'):
        text = "Выберите тему для новой идеи:"
    elif context.user_data.get('adding_task'):
        text = "Выберите тему для нового задания:"
    else:
        text = "Выберите тему:"

    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup)
    except:
        await query.message.reply_text(text=text, reply_markup=reply_markup)

# получение случайной идеи и задания
async def send_random_idea(update: Update, context: ContextTypes.DEFAULT_TYPE, theme: str):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT idea FROM ideas WHERE theme = ? ORDER BY RANDOM() LIMIT 1', (theme,))
    result = cursor.fetchone()
    conn.close()
    if result:
        idea = result[0]
        await update.edit_message_text(f"💡 Вот идея для Reels:\n{idea}")
    else:
        await update.edit_message_text("❌ Идеи для этой темы пока недоступны.")

async def send_random_task(update: Update, context: ContextTypes.DEFAULT_TYPE, theme: str):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT task FROM tasks WHERE theme = ? ORDER BY RANDOM() LIMIT 1', (theme,))
    result = cursor.fetchone()
    conn.close()
    if result:
        task = result[0]
        await update.edit_message_text(f"📝 Вот ваше задание:\n{task}")
    else:
        await update.edit_message_text("❌ Задания для этой темы пока недоступны.")



# Сохранение данных пользователя в базу данных
def save_user_to_db(user_id: int, name: str, followers: int, blog_theme: str):
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        if cursor.fetchone():
            cursor.execute('''
                UPDATE users
                SET name = ?, followers = ?, blog_theme = ?
                WHERE user_id = ?
            ''', (name, followers, blog_theme, user_id))
        else:
            cursor.execute('''
                INSERT INTO users (user_id, name, followers, blog_theme, registered_at)
                VALUES (?, ?, ?, ?, datetime('now'))
            ''', (user_id, name, followers, blog_theme))
        conn.commit()
        logging.info(f"✅ Данные пользователя {user_id} сохранены в базу данных.")
    except Exception as e:
        logging.error(f"❌ Ошибка при сохранении данных пользователя: {e}")
    finally:
        conn.close()

# Загрузка данных пользователя из базы данных
def load_user_from_db(user_id: int):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name, followers, registered_at FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {
            'name': result[0],
            'followers': result[1],
            'registered_at': result[2]
        }
    return None

# Получение случайной идеи
def get_random_idea_by_theme(theme: str):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT idea FROM ideas WHERE theme = ? ORDER BY RANDOM() LIMIT 1', (theme,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# Получение случайного задания
def get_random_task_by_theme(theme: str):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT task FROM tasks WHERE theme = ? ORDER BY RANDOM() LIMIT 1', (theme,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

async def send_random_idea(query, context, theme):
    idea = get_random_idea_by_theme(theme)
    if idea:
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"💡 Вот идея для Reels:\n{idea}", reply_markup=reply_markup)
    else:
        await query.edit_message_text("❌ Идеи для этой темы пока недоступны.")
    context.user_data.pop('getting_idea', None)  # Сбрасываем флаг


# Функция для начала диалога
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("Функция start вызвана")
    user_id = update.effective_user.id
    user_data = load_user_from_db(user_id)
    if user_data:
        context.user_data.update(user_data)
        await update.message.reply_text(
            "Вы уже зарегистрированы! Вот ваш профиль:\n"
            f"Имя: {user_data['name']}\n"
            f"Подписчики: {user_data['followers']}"
        )
        return await show_menu(update, context)
    if user_id == ADMIN_ID:
        await update.message.reply_text(
            "Привет, администратор! Давайте начнем с заполнения информации о вашем блоге.\n\n"
            "Введите ваше имя:"
        )
    else:
        await update.message.reply_text(
            "Привет! Давайте начнем с заполнения информации о вашем блоге.\n\n"
            "Введите ваше имя:"
        )
    return NAME

# Сбор имени пользователя
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("Функция get_name вызвана")
    user_input = update.message.text.strip()

    # Проверяем, что сообщение не пустое
    if not user_input:
        logging.warning("Получено пустое сообщение")
        await update.message.reply_text("❌ Сообщение не может быть пустым. Попробуйте снова:")
        return NAME

    # Проверяем, что имя содержит только допустимые символы
    if not all(char.isalpha() or char.isspace() or char == '-' for char in user_input):
        logging.warning("Имя содержит недопустимые символы")
        await update.message.reply_text("❌ Имя должно содержать только буквы, пробелы или дефисы. Попробуйте снова:")
        return NAME

    # Сохраняем имя в контексте
    context.user_data['name'] = user_input
    logging.info(f"Имя пользователя сохранено: {user_input}")

    # Переходим к следующему шагу (выбор темы блога)
    keyboard = [
        [InlineKeyboardButton("Личный блог", callback_data="theme_personal")],
        [InlineKeyboardButton("Спорт", callback_data="theme_sports")],
        [InlineKeyboardButton("Психология", callback_data="theme_psychology")],
        [InlineKeyboardButton("Технологии", callback_data="theme_technology")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите тему вашего блога:", reply_markup=reply_markup)

    # Возвращаем следующее состояние
    return BLOG_THEME

async def get_blog_theme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Подтверждаем запрос

    # Получаем выбранную тему
    theme = query.data
    logging.info(f"Выбранная тема блога: {theme}")

    # Сохраняем тему в контекст
    context.user_data['blog_theme'] = theme

    # Отправляем сообщение о следующем шаге
    await query.edit_message_text("Отлично! Теперь укажите текущее количество подписчиков в Instagram:")
    return FOLLOWERS

# Сбор количества подписчиков при регистрации
async def get_followers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    if not user_input.isdigit():
        await update.message.reply_text("❌ Введите только цифры. Попробуйте снова:")
        return FOLLOWERS
    followers = int(user_input)
    context.user_data['followers'] = followers
    user_id = update.effective_user.id

    # Сохраняем данные пользователя в базу данных
    save_user_to_db(
        user_id,
        context.user_data['name'],
        followers,
        context.user_data.get('blog_theme', 'Не указано')  # Добавляем тему блога
    )
    logging.info(f"✅ Данные пользователя {user_id} сохранены в базу данных.")

    await update.message.reply_text("Спасибо! Информация сохранена.")
    return await show_menu(update, context)

# Обновление количества подписчиков
async def update_followers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    if not user_input.isdigit():
        await update.message.reply_text("❌ Введите только цифры. Попробуйте снова:")
        return UPDATE_FOLLOWERS
    new_followers = int(user_input)
    old_followers = context.user_data.get('followers', 0)
    difference = new_followers - old_followers
    if difference > 0:
        message = f"🎉 Поздравляем! За эту неделю вы набрали {difference} новых подписчиков! Так держать!"
    elif difference == 0:
        message = "💡 Количество подписчиков не изменилось. Не расстраивайтесь, продолжайте работать над контентом!"
    else:
        message = (
            f"💪 Не расстраивайтесь! У вас уменьшилось {abs(difference)} подписчиков. "
            "Это временное явление. Продолжайте создавать качественный контент, и ваши подписчики вернутся!"
        )
    context.user_data['followers'] = new_followers
    save_user_to_db(update.effective_user.id, context.user_data['name'], new_followers)
    await update.message.reply_text(message)
    return await show_menu(update, context)

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Профиль", callback_data="profile")],
        [InlineKeyboardButton("Идеи для Reels", callback_data="ideas")],
        [InlineKeyboardButton("Задания", callback_data="tasks")],
        [InlineKeyboardButton("Поддержка", callback_data="support")]
    ]
    if isinstance(update, Update):  # Если это объект Update
        user_id = update.effective_user.id
    else:  # Если это объект CallbackQuery или Message
        user_id = update.from_user.id if hasattr(update, 'from_user') else update.chat.id

    # Добавляем кнопки администратора
    if user_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("Добавить идею", callback_data="add_idea")])
        keyboard.append([InlineKeyboardButton("Добавить задание", callback_data="add_task")])
        keyboard.append([InlineKeyboardButton("Рассылка", callback_data="broadcast")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Редактируем сообщение
    if isinstance(update, Update):
        await update.message.reply_text("Главное меню:", reply_markup=reply_markup)
    else:
        await update.edit_message_text("Главное меню:", reply_markup=reply_markup)

    return ConversationHandler.END

# Просмотр профиля
async def show_profile(query: Update, context: ContextTypes.DEFAULT_TYPE):
    profile_info = (
        f"📋 Ваш профиль:\n"
        f"Имя: {context.user_data.get('name', 'Не указано')}\n"
        f"Подписчики: {context.user_data.get('followers', 'Не указано')}\n"
        f"Тема блога: {context.user_data.get('blog_theme', 'Не указана')}"  # Добавляем тему блога
    )
    if query.from_user.id == ADMIN_ID:
        profile_info += "\n👑 Вы администратор!"
    keyboard = [[InlineKeyboardButton("Назад", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=profile_info, reply_markup=reply_markup)
    
# Обработка кнопки "Добавить идею"
async def add_idea_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Подтверждаем запрос

    # Устанавливаем флаг добавления идеи
    context.user_data['adding_idea'] = True
    context.user_data.pop('adding_task', None)  # Сбрасываем флаг добавления задания

    # Показываем меню выбора темы
    await show_theme_menu(query, context)

# Обработка кнопки "Добавить задание"
async def add_task_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Подтверждаем запрос

    # Устанавливаем флаг добавления задания
    context.user_data['adding_task'] = True
    context.user_data.pop('adding_idea', None)  # Сбрасываем флаг добавления идеи

    # Показываем меню выбора темы
    await show_theme_menu(query, context)





# Сохранение новой идеи
async def save_idea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idea = update.message.text.strip()
    theme = context.user_data.get('selected_theme')
    logging.info(f"=== Попытка сохранения идеи ===")
    logging.info(f"Текущая тема: {context.user_data.get('selected_theme')}")
    logging.info(f"Текст сообщения: {update.message.text}")

    if not theme:
        logging.warning("Тема не выбрана")
        await update.message.reply_text("❌ Техническая ошибка. Попробуйте снова.")
        return

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO ideas (idea, theme) VALUES (?, ?)', (idea, theme))
        conn.commit()
        logging.info(f"Идея '{idea}' добавлена в тему '{theme}'")
    except Exception as e:
        logging.error(f"Ошибка при добавлении идеи: {e}")
        await update.message.reply_text("❌ Ошибка при добавлении идеи. Попробуйте позже.")
        return
    finally:
        conn.close()

    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("✅ Идея добавлена!", reply_markup=reply_markup)

    # Сбрасываем флаги
    context.user_data.pop('adding_idea', None)
    context.user_data.pop('selected_theme', None)
    await update.message.reply_text("✅ Идея добавлена!")
    return ConversationHandler.END

# Сохранение нового задания
async def save_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    task = update.message.text.strip()
    theme = context.user_data.get('selected_theme')
    logging.info(f"=== Попытка сохранения идеи ===")
    logging.info(f"Текущая тема: {context.user_data.get('selected_theme')}")
    logging.info(f"Текст сообщения: {update.message.text}")

    if 'selected_theme' not in context.user_data:
        await update.message.reply_text("❌ Сначала выберите тему!")
        return await show_theme_menu(update, context)

    if not theme:
        logging.warning("Тема не выбрана")
        await update.message.reply_text("❌ Техническая ошибка. Попробуйте снова.")
        return

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO tasks (task, theme) VALUES (?, ?)', (task, theme))
        conn.commit()
        logging.info(f"Задание '{task}' добавлено в тему '{theme}'")
    except Exception as e:
        logging.error(f"Ошибка при добавлении задания: {e}")
        await update.message.reply_text("❌ Ошибка при добавлении задания. Попробуйте позже.")
        return
    finally:
        conn.close()

    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("✅ Задание добавлено!", reply_markup=reply_markup)

    # Сбрасываем флаги
    context.user_data.pop('adding_task', None)
    context.user_data.pop('selected_theme', None)

    return ConversationHandler.END


## Функция для запуска рассылки

# Получение списка всех пользователей
async def get_all_users():
    async with aiosqlite.connect('users.db') as db:
        cursor = await db.execute('SELECT user_id FROM users')
        users = await cursor.fetchall()
        return [user[0] for user in users]

## Функция для рассылки сообщения всем пользователям
async def send_broadcast_message(message_text: str, context: ContextTypes.DEFAULT_TYPE):
    users = await get_all_users()  # Получаем список всех пользователей
    for user_id in users:
        try:
            # Отправляем сообщение каждому пользователю
            await context.bot.send_message(user_id, message_text)
        except Exception as e:
            logging.error(f"Не удалось отправить сообщение пользователю {user_id}: {e}")

# Обработка нажатия на кнопку "Рассылка"
async def broadcast_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        keyboard = [
            [InlineKeyboardButton("Отправить рассылку", callback_data="start_broadcast")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Используем edit_message_text, потому что это callback_query, а не обычное сообщение
        await update.callback_query.edit_message_text(
            "Нажмите кнопку для отправки рассылки.", reply_markup=reply_markup
        )

## Начало рассылки
async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    context.user_data['broadcast'] = True
    await update.callback_query.edit_message_text("Введите текст для рассылки:")

# Обработка текста для рассылки
async def handle_broadcast_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'broadcast' not in context.user_data:
        return

    broadcast_text = update.message.text.strip()
    if not broadcast_text:
        await update.message.reply_text("❌ Сообщение не может быть пустым. Попробуйте снова.")
        return

    # Отправка сообщения всем пользователям
    await send_broadcast_message(broadcast_text, context)  # Передаем context
    await update.message.reply_text(f"✅ Сообщение отправлено всем пользователям!")

    # Завершаем рассылку
    context.user_data.pop('broadcast', None)

   
   

   
    





# Обработка текстовых сообщений
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("Обработка текстового сообщения")
    user_id = update.effective_user.id
    text = update.message.text.strip()
    logging.info(f"Получен текст: {text}")

    # Проверка флага добавления идеи
    if context.user_data.get('adding_idea'):
        theme = context.user_data.get('theme')
        if not theme:
            logging.warning("Тема не выбрана")
            await update.message.reply_text("❌ Техническая ошибка. Попробуйте снова.")
            return

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO ideas (idea, theme) VALUES (?, ?)', (text, theme))
            conn.commit()
            logging.info(f"Идея '{text}' добавлена в тему '{theme}'")
        except Exception as e:
            logging.error(f"Ошибка при добавлении идеи: {e}")
            await update.message.reply_text("❌ Ошибка при добавлении идеи. Попробуйте позже.")
            return
        finally:
            conn.close()

        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("✅ Идея добавлена!", reply_markup=reply_markup)
        context.user_data.pop('adding_idea', None)
        context.user_data.pop('theme', None)
        return

    # Проверка флага добавления задания
    if context.user_data.get('adding_task'):
        theme = context.user_data.get('theme')
        if not theme:
            logging.warning("Тема не выбрана")
            await update.message.reply_text("❌ Техническая ошибка. Попробуйте снова.")
            return

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO tasks (task, theme) VALUES (?, ?)', (text, theme))
            conn.commit()
            logging.info(f"Задание '{text}' добавлено в тему '{theme}'")
        except Exception as e:
            logging.error(f"Ошибка при добавлении задания: {e}")
            await update.message.reply_text("❌ Ошибка при добавлении задания. Попробуйте позже.")
            return
        finally:
            conn.close()

        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("✅ Задание добавлено!", reply_markup=reply_markup)
        context.user_data.pop('adding_task', None)
        context.user_data.pop('theme', None)
        return

    # Если ни один флаг не установлен, выводим сообщение об ошибке
    await update.message.reply_text("❌ Неизвестная команда. Попробуйте снова.")



    

# Обработка кнопки "Идеи для Reels"
async def ideas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update  # update уже является CallbackQuery
    await query.answer()
    idea = get_random_idea_by_theme()
    if not idea:
        await query.edit_message_text("❌ Идеи пока недоступны. Попробуйте позже!")
        return show_menu
    keyboard = [[InlineKeyboardButton("Назад", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await show_theme_menu(query, context)  # Передаем query напрямую
    

# Обработка кнопки "Задания"
async def tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update  # update уже является CallbackQuery
    await query.answer()
    task = get_random_task_by_theme()
    if not task:
        await query.edit_message_text("❌ Задания пока недоступны. Попробуйте позже!")
        return show_menu
    keyboard = [[InlineKeyboardButton("Назад", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await show_theme_menu(query, context)  # Передаем query напрямую

# Еженедельный запрос обновления данных
async def weekly_update(context: ContextTypes.DEFAULT_TYPE):
    application = context.application
    logging.info("⏰ Запущена задача отправки сообщений всем пользователям")

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, name FROM users')
    users = cursor.fetchall()
    conn.close()

    for user in users:
        user_id, name = user
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"🌟 Привет, {name}! Напиши текущее количество подписчиков за эту неделю:"
            )
            logging.info("f✉️ Сообщение отправлено пользователю {user_id}")
            await asyncio.sleep(1)  # Задержка 1 секунда, чтобы избежать блокировки Telegram API
        except Exception as e:
            logging.error(f"❌ Ошибка при отправке сообщения пользователю {user_id}: {e}")


# Настройка еженедельной рассылки
def setup_weekly_updates(application):
    job_queue = application.job_queue
    if job_queue is None:
        raise ValueError("Job queue is not initialized.")
    
    job_queue.run_repeating(
        weekly_update,
        interval=7 * 24 * 60 * 60,  # Раз в неделю
        first=5  # Первый запуск через 5 секунд после старта
    )


async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Профиль", callback_data="profile")],
        [InlineKeyboardButton("Идеи для Reels", callback_data="ideas")],
        [InlineKeyboardButton("Задания", callback_data="tasks")],
        [InlineKeyboardButton("Поддержка", callback_data="support")]
    ]
    if isinstance(update, Update):  # Если это объект Update
        user_id = update.effective_user.id
    else:  # Если это объект CallbackQuery или Message
        user_id = update.from_user.id if hasattr(update, 'from_user') else update.chat.id

    if user_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("Добавить идею", callback_data="add_idea")])
        keyboard.append([InlineKeyboardButton("Добавить задание", callback_data="add_task")])
        keyboard.append([InlineKeyboardButton("Рассылка", callback_data="broadcast")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Редактируем сообщение
    

    

    try:
        await query.edit_message_text(text="📍 Главное меню", reply_markup=reply_markup)
    except:
        await query.message.reply_text(text="📍 Главное меню", reply_markup=reply_markup)
    return ConversationHandler.END



# Обработка нажатий на кнопки
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    logging.info(f"Нажата кнопка с callback_data: {query.data}")
    await query.answer()  # Подтверждаем запрос


    if query.data == "profile":
        await show_profile(query, context)
    elif query.data == "back_to_menu":
        await show_menu(query, context)
    elif query.data == "ideas":
        context.user_data['getting_idea'] = True  # Устанавливаем флаг получения идеи
        await show_theme_menu(query, context)  # Показываем меню выбора темы
    elif query.data == "tasks":
        context.user_data['getting_task'] = True  # Устанавливаем флаг получения задания
        await show_theme_menu(query, context)  # Показываем меню выбора темы

    elif query.data.startswith("theme_"):
        theme = query.data.split("_")[1]
        context.user_data['selected_theme'] = theme  # Сохраняем тему
    
    if context.user_data.get('adding_idea'):
        await query.edit_message_text("Введите текст новой идеи:")
        return ADD_IDEA  # Явно возвращаем состояние
        
    elif context.user_data.get('adding_task'):
        await query.edit_message_text("Введите текст нового задания:")
        return ADD_TASK  # Явно возвращаем состояние

    elif context.user_data.get('getting_idea'):
        idea = get_random_idea_by_theme(context.user_data['selected_theme'])
        if idea:
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"💡 Вот идея для Reels:\n{idea}", reply_markup=reply_markup)
        else:
            await query.edit_message_text("❌ Идеи для этой темы пока недоступны.")
        context.user_data.pop('getting_idea', None)  # Сбрасываем флаг

    elif context.user_data.get('getting_task'):
        task = get_random_task_by_theme(context.user_data['selected_theme'])
        if task:
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"📝 Вот ваше задание:\n{task}", reply_markup=reply_markup)
        else:
            await query.edit_message_text("❌ Задания для этой темы пока недоступны.")
        context.user_data.pop('getting_task', None)  # Сбрасываем флаг


    elif query.data == "support":
        keyboard = [[InlineKeyboardButton("Назад", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text="📞 Поддержка: свяжитесь с разработчиком.", reply_markup=reply_markup)
    elif query.data == "add_idea":
        # Устанавливаем флаг добавления идеи
        context.user_data['adding_idea'] = True
        context.user_data.pop('adding_task', None)  # Сбрасываем флаг добавления задания
        await show_theme_menu(query, context)  # Показываем меню выбора темы

    elif query.data == "add_task":
        # Устанавливаем флаг добавления задания
        context.user_data['adding_task'] = True
        context.user_data.pop('adding_idea', None)  # Сбрасываем флаг добавления идеи
        await show_theme_menu(query, context)  # Показываем меню выбора темы

    elif query.data == "broadcast":
        if query.from_user.id == ADMIN_ID:
            await query.edit_message_text("Пожалуйста, напишите текст рассылки, который вы хотите отправить всем пользователям:")
            return SEND_BROADCAST_TEXT
    else:
        logging.warning(f"Неизвестная кнопка с callback_data: {query.data}")
        await query.edit_message_text("❌ Неизвестная команда. Попробуйте снова.")   

    return ConversationHandler.END

            
# Основная функция
def main():
    init_db()  # Инициализация базы данных
    
    application = ApplicationBuilder().token("8183509798:AAGCGEol_j0wQ50pmm8-O6H0YJoBCJWmTCk").build()


    # Создаем обработчик диалогов
    
    conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
        BLOG_THEME: [CallbackQueryHandler(get_blog_theme)],
        FOLLOWERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_followers)],
        UPDATE_FOLLOWERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_followers)],
        ADD_IDEA: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_idea)],
        ADD_TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_task)],
        
    },
    fallbacks=[]
)



   
    
  # Обработчики команд
    application.add_handler(conv_handler)  # Сначала регистрируем ConversationHandler
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(back_to_menu, pattern="back_to_menu"))
    application.add_handler(CallbackQueryHandler(button_handler))  # Обработчик всех кнопок
    application.add_handler(CallbackQueryHandler(broadcast_button, pattern="broadcast"))
    application.add_handler(CallbackQueryHandler(start_broadcast, pattern="start_broadcast"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast_text))  # Текст для рассылки
    application.add_handler(MessageHandler(filters.ALL, debug_handler))  # Отладочный обработчик
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))  # Общий обработчик текста
    
    
   
    # Настройка еженедельной рассылки
    setup_weekly_updates(application)

    print("Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
     main()