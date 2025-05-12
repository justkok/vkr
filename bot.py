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

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO)
# Состояния для сбора информации
NAME, FOLLOWERS, UPDATE_FOLLOWERS, ADD_IDEA, ADD_TASK, BROADCAST, START_BROADCAST, WAIT_BROADCAST_MESSAGE = range(8)
SEND_BROADCAST_TEXT = 9

logging.basicConfig(level=logging.INFO)
import logging

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# ID администратора
ADMIN_ID = 700013214

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    # Создаем таблицу пользователей
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        name TEXT,
        followers INTEGER,
        registered_at TEXT
    )''')
    # Таблица идей
    cursor.execute('''CREATE TABLE IF NOT EXISTS ideas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        idea TEXT NOT NULL
    )''')
    # Таблица заданий
    cursor.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task TEXT NOT NULL
    )''')
    conn.commit()
    conn.close()

# Сохранение данных пользователя в базу данных
def save_user_to_db(user_id: int, name: str, followers: int):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    if cursor.fetchone():
        cursor.execute('''
            UPDATE users
            SET name = ?, followers = ?
            WHERE user_id = ?
        ''', (name, followers, user_id))
    else:
        cursor.execute('''
            INSERT INTO users (user_id, name, followers, registered_at)
            VALUES (?, ?, ?, datetime('now'))
        ''', (user_id, name, followers))
    conn.commit()
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
def get_random_idea():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT idea FROM ideas ORDER BY RANDOM() LIMIT 1')
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# Получение случайного задания
def get_random_task():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT task FROM tasks ORDER BY RANDOM() LIMIT 1')
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# Функция для начала диалога
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    user_input = update.message.text.strip()
    if not user_input.isalpha():
        await update.message.reply_text("❌ Имя должно содержать только буквы. Попробуйте снова:")
        return NAME
    context.user_data['name'] = user_input
    await update.message.reply_text("Отлично! Теперь укажите текущее количество подписчиков в Instagram:")
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
    save_user_to_db(user_id, context.user_data['name'], followers)
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
        f"Подписчики: {context.user_data.get('followers', 'Не указано')}"
    )
    if query.from_user.id == ADMIN_ID:
        profile_info += "\n👑 Вы администратор!"
    keyboard = [[InlineKeyboardButton("Назад", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=profile_info, reply_markup=reply_markup)

# Обработка кнопки "Добавить идею"
async def add_idea_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update  # update уже является CallbackQuery
    await query.answer()  # Подтверждаем запрос
    context.user_data['adding_idea'] = True  # Устанавливаем флаг добавления идеи
    await query.edit_message_text("Введите текст новой идеи:")
    return ADD_IDEA  # Возвращаем состояние ADD_IDEA


async def add_task_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update  # update уже является CallbackQuery
    await query.answer()  # Подтверждаем запрос
    context.user_data['adding_task'] = True  # Устанавливаем флаг добавления задания
    await query.edit_message_text("Введите текст нового задания:")
    return ADD_TASK  # Возвращаем состояние ADD_TASK





# Сохранение новой идеи

async def save_idea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idea = update.message.text.strip()
    print("=== Попытка сохранения идеи ===")
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO ideas (idea) VALUES (?)', (idea,))
        conn.commit()
        print(f"✅ Идея '{idea}' успешно добавлена в базу данных.")
    except Exception as e:
        print(f"❌ Ошибка при добавлении идеи в базу данных: {e}")
        await update.message.reply_text("❌ Произошла ошибка при добавлении идеи. Попробуйте позже.")
        return
    finally:
        conn.close()

    # Отправка уведомления администратору
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"✅ Новая идея добавлена: {idea}")
        print(f"✉️ Уведомление администратору отправлено: {idea}")
    except Exception as e:
        print(f"❌ Ошибка при отправке уведомления администратору: {e}")

    # Ответ пользователю
    keyboard = [[InlineKeyboardButton("Назад", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"✅ Идея добавлена: {idea}", reply_markup=reply_markup)

    # Возвращаемся в главное меню
    return await show_menu(update, context)


# Сохранение нового задания
async def save_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    task = update.message.text.strip()
    logger.info(f"=== Попытка сохранения задания ===")

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    try:
        # Добавление задания в базу данных
        cursor.execute('INSERT INTO tasks (task) VALUES (?)', (task,))
        conn.commit()
        logger.info(f"✅ Задание '{task}' успешно добавлено в базу данных.")
    except Exception as e:
        logger.error(f"❌ Ошибка при добавлении задания в базу данных: {e}")
        await update.message.reply_text("❌ Произошла ошибка при добавлении задания. Попробуйте позже.")
        return
    finally:
        conn.close()

    # Отправка уведомления администратору
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"✅ Новое задание добавлено: {task}"
        )
        logger.info(f"✉️ Уведомление администратору отправлено: {task}")
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке уведомления администратору: {e}")

    # Создаем кнопку "Назад"
    keyboard = [[InlineKeyboardButton("Назад", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Ответ пользователю с кнопкой "Назад"
    if isinstance(update, Update):
        await update.message.reply_text(f"✅ Задание добавлено: {task}", reply_markup=reply_markup)
    else:
        await update.edit_message_text(f"✅ Задание добавлено: {task}", reply_markup=reply_markup)

    # Возвращаемся в главное меню
    return await show_menu(update, context)



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
        await update.callback_query.edit_message_text(
            "Нажмите кнопку для отправки рассылки.", reply_markup=reply_markup
        )
# Начало рассылки
async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    context.user_data['broadcast'] = True
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("Введите текст для рассылки:")

# Обработка текста для рассылки
async def handle_broadcast_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'broadcast' not in context.user_data:
        return
    
    # Удаляем флаг рассылки
    context.user_data.pop('broadcast', None)
    
    broadcast_text = update.message.text.strip()
    if not broadcast_text:
        await update.message.reply_text("❌ Сообщение не может быть пустым. Попробуйте снова.")
        return
      # Удаляем флаг рассылки
    context.user_data.pop('broadcast', None)
    
    broadcast_text = update.message.text.strip()
    if not broadcast_text:
        await update.message.reply_text("❌ Сообщение не может быть пустым. Попробуйте снова.")
        return

    # Отправка сообщения всем пользователям
    try:
        users = await get_all_users()  # Получаем список всех пользователей
        for user_id in users:
            try:
                # Отправляем сообщение каждому пользователю с задержкой
                await context.bot.send_message(user_id, broadcast_text)
                await asyncio.sleep(0.1)  # небольшая задержка между сообщениями
            except Exception as e:
                logging.error(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
        
        await update.message.reply_text(f"✅ Сообщение отправлено всем пользователям!")
    except Exception as e:
        logging.error(f"Ошибка при рассылке: {e}")
        await update.message.reply_text("❌ Произошла ошибка при отправке сообщений.")

   
   

   
    





# Обработка текстовых сообщений
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # Проверка флага добавления идеи
    if context.user_data.get('adding_idea'):
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO ideas (idea) VALUES (?)', (text,))
            conn.commit()
            print(f"✅ Идея '{text}' успешно добавлена в базу данных.")
        except Exception as e:
            print(f"❌ Ошибка при добавлении идеи в базу данных: {e}")
            await update.message.reply_text("❌ Произошла ошибка при добавлении идеи. Попробуйте позже.")
            return
        finally:
            conn.close()

        # Отправка уведомления администратору
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"✅ Новая идея добавлена: {text}")

        # Ответ пользователю
        keyboard = [[InlineKeyboardButton("Назад", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("✅ Идея добавлена!", reply_markup=reply_markup)

        # Сброс флага
        context.user_data.pop('adding_idea', None)

    # Проверка флага добавления задания
    elif context.user_data.get('adding_task'):
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO tasks (task) VALUES (?)', (text,))
            conn.commit()
            print(f"✅ Задание '{text}' успешно добавлено в базу данных.")
        except Exception as e:
            print(f"❌ Ошибка при добавлении задания в базу данных: {e}")
            await update.message.reply_text("❌ Произошла ошибка при добавлении задания. Попробуйте позже.")
            return
        finally:
            conn.close()

        # Отправка уведомления администратору
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"✅ Новое задание добавлено: {text}")

        # Ответ пользователю
        keyboard = [[InlineKeyboardButton("Назад", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("✅ Задание добавлено!", reply_markup=reply_markup)

        # Сброс флага
        context.user_data.pop('adding_task', None)

    

# Обработка кнопки "Идеи для Reels"
async def ideas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update  # update уже является CallbackQuery
    await query.answer()
    idea = get_random_idea()
    if not idea:
        await query.edit_message_text("❌ Идеи пока недоступны. Попробуйте позже!")
        return
    keyboard = [[InlineKeyboardButton("Назад", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=f"💡 Вот идея для Reels:\n{idea}", reply_markup=reply_markup)

# Обработка кнопки "Задания"
async def tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update  # update уже является CallbackQuery
    await query.answer()
    task = get_random_task()
    if not task:
        await query.edit_message_text("❌ Задания пока недоступны. Попробуйте позже!")
        return
    keyboard = [[InlineKeyboardButton("Назад", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=f"📝 Вот ваше задание:\n{task}", reply_markup=reply_markup)





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
    await query.answer()  # Подтверждаем запрос

    if query.data == "profile":
        await show_profile(query, context)
    elif query.data == "back_to_menu":
        await show_menu(query, context)
    elif query.data == "ideas":
        await ideas(query, context)
    elif query.data == "tasks":
        await tasks(query, context)
    elif query.data == "support":
        keyboard = [[InlineKeyboardButton("Назад", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text="📞 Поддержка: свяжитесь с разработчиком.", reply_markup=reply_markup)
    elif query.data == "add_idea":
        await add_idea_button(query, context)
    elif query.data == "add_task":
        await add_task_button(query, context)
    elif query.data == "broadcast":
        if query.from_user.id == ADMIN_ID:
            await query.edit_message_text("Пожалуйста, напишите текст рассылки, который вы хотите отправить всем пользователям:")
            return SEND_BROADCAST_TEXT



            
# Основная функция
def main():
    init_db()  # Инициализация базы данных
    application = ApplicationBuilder().token("8183509798:AAGCGEol_j0wQ50pmm8-O6H0YJoBCJWmTCk").build()
    application.add_handler(CallbackQueryHandler(back_to_menu, pattern="back_to_menu"))


    # Создаем обработчик диалогов
    
    conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
        FOLLOWERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_followers)],
        UPDATE_FOLLOWERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_followers)],
        ADD_IDEA: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_idea)],
        ADD_TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_task)],
        SEND_BROADCAST_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast_text)]
        
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
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))  # Общий обработчик текста


    

    print("Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()