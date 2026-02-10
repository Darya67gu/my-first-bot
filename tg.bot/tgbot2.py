import asyncio
import os
import json
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# Конфигурация
TOKEN = "8359184554:AAGbtfDrjt32k0BJ77OMHrentRhEnkXpjmE"
DATA_FILE = "schedules.json"
REMINDER_TIME_DELTA = timedelta(hours=1)  # Напоминать за час до события

# Структура для хранения расписаний
# {user_id: {date_time: {task_id: {"text": "текст задачи", "date_created": "дата создания"}}}}

class ScheduleManager:
    def __init__(self):
        self.schedules = self.load_schedules()
    
    def load_schedules(self):
        """Загружаем существующие расписания из файла."""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Ошибка загрузки расписаний: {e}")
                return {}
        return {}
    
    def save_schedules(self):
        """Сохраняем расписания в файл."""
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.schedules, f, ensure_ascii=False, indent=2)
    
    def add_schedule(self, user_id: int, date_time_str: str, schedule_text: str) -> int:
        """Добавляет новое событие в выбранную дату и время."""
        if str(user_id) not in self.schedules:
            self.schedules[str(user_id)] = {}
            
        if date_time_str not in self.schedules[str(user_id)]:
            self.schedules[str(user_id)][date_time_str] = {}
        
        # Генерируем уникальный id события
        next_id = 1
        existing_ids = set(map(int, self.schedules[str(user_id)][date_time_str].keys()))
        while next_id in existing_ids:
            next_id += 1
        
        self.schedules[str(user_id)][date_time_str][str(next_id)] = {
            "text": schedule_text,
            "date_created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.save_schedules()
        return next_id
    
    def get_schedules_by_date(self, user_id: int, date_time_str: str) -> dict:
        """Возвращает все события на указанную дату и время."""
        user_schedules = self.schedules.get(str(user_id), {})
        return user_schedules.get(date_time_str, {})
    
    def remove_schedule(self, user_id: int, date_time_str: str, schedule_id: str) -> bool:
        """Удаляет конкретное событие из выбранной даты и времени."""
        schedules = self.schedules.get(str(user_id), {}).get(date_time_str, {})
        if schedule_id in schedules:
            del schedules[schedule_id]
            self.save_schedules()
            return True
        return False
    
    def clear_schedules_on_date(self, user_id: int, date_time_str: str) -> bool:
        """Удаляет все события на заданную дату и время."""
        if str(user_id) in self.schedules and date_time_str in self.schedules[str(user_id)]:
            del self.schedules[str(user_id)][date_time_str]
            self.save_schedules()
            return True
        return False

# Менеджер расписаний
schedule_manager = ScheduleManager()

# Вспомогательные функции
def format_schedules(schedules: dict) -> str:
    """Форматирует список расписаний в читаемый вид."""
    result = []
    for schedule_id, data in sorted(schedules.items(), key=lambda x: int(x[0])):
        text = data["text"][:20] + ("..." if len(data["text"]) > 20 else "")
        created_at = data["date_created"].split()[1][:5]
        result.append(f"{schedule_id}. {text} ({created_at})")
    return '<br>'.join(result)

def build_main_menu():
    """Создает главное меню для быстрого доступа к командам."""
    return ReplyKeyboardMarkup([
        ['/today', '/tomorrow'],
        ['/calendar', '/add'],
        ['/delete', '/clear']
    ], resize_keyboard=True)

# Функция для отправки напоминания
async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    user_id = job.user_id
    event_text = job.event_text
    reminder_time = job.reminder_time
    
    await context.bot.send_message(chat_id=user_id, text=f"Напоминание: {event_text} в {reminder_time}", parse_mode='HTML')

# Команды бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствие и помощь по работе с ботом."""
    help_text = (
        "<b>Добро пожаловать в планировщик задач!</b>\n\n"
        "- Используй команду <code>/today</code>, чтобы увидеть расписание на сегодня.\n"
        "- Команда <code>/tomorrow</code> покажет расписание на завтра.\n"
        "- Посмотреть полный календарь можно командой <code>/calendar</code>.\n"
        "- Для добавления нового события введите текст прямо в чат формата \"ДАТА ЧАСОВ ТЕКСТ\""
    )
    await update.message.reply_html(help_text, reply_markup=build_main_menu())

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает расписание на сегодняшний день."""
    user_id = update.effective_user.id
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    schedules = schedule_manager.get_schedules_by_date(user_id, today_str)
    
    if not schedules:
        response = "Сегодня у вас нет запланированных событий 😊"
    else:
        formatted_schedules = format_schedules(schedules)
        response = f"<b>Ваше расписание на сегодня:</b><br>{formatted_schedules}"
    
    await update.message.reply_html(response, reply_markup=build_main_menu())

async def tomorrow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает расписание на завтра."""
    user_id = update.effective_user.id
    now = datetime.now()
    tomorrow_str = (now + timedelta(days=1)).strftime('%Y-%m-%d')
    schedules = schedule_manager.get_schedules_by_date(user_id, tomorrow_str)
    
    if not schedules:
        response = "Завтра у вас нет запланированных событий 😊"
    else:
        formatted_schedules = format_schedules(schedules)
        response = f"<b>Ваше расписание на завтра:</b><br>{formatted_schedules}"
    
    await update.message.reply_html(response, reply_markup=build_main_menu())

async def calendar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Предлагает выбор календаря для просмотра конкретных дат."""
    user_id = update.effective_user.id
    now = datetime.now()
    dates = [(now + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(-3, 7)]
    
    buttons = [[InlineKeyboardButton(d, callback_data=f'view_{d}')] for d in dates]
    await update.message.reply_html(
        "Выберите интересующую вас дату:", 
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def view_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отображает расписание на выбранную дату."""
    query = update.callback_query
    await query.answer()
    
    selected_date = query.data.replace('view_', '')
    user_id = update.effective_user.id
    schedules = schedule_manager.get_schedules_by_date(user_id, selected_date)
    
    if not schedules:
        response = f"В этот день у вас нет планов 😊"
    else:
        formatted_schedules = format_schedules(schedules)
        response = f"<b>Ваше расписание на {selected_date}:</b><br>{formatted_schedules}"
    
    await query.edit_message_text(response, parse_mode='HTML')

async def add_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ввод текста пользователем и добавляет новое событие."""
    user_id = update.effective_user.id
    input_data = update.message.text.strip()
    
    parts = input_data.split(maxsplit=2)
    if len(parts) != 3:
        await update.message.reply_html("<b>Формат ввода неверен.</b>\nПример: 2025-10-12 14:00 Встреча с другом")
        return
    
    date_str, time_str, event_text = parts
    try:
        event_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    except ValueError:
        await update.message.reply_html("<b>Неверный формат даты или времени.</b>\nПример: 2025-10-12 14:00")
        return
    
    # Проверяем наличие даты и времени в расписании
    date_time_str = event_datetime.strftime('%Y-%m-%d %H:%M')
    
    # Добавляем событие в расписание
    new_id = schedule_manager.add_schedule(user_id, date_time_str, event_text)
    
    # Устанавливаем напоминание за час до события
    reminder_time = event_datetime - REMINDER_TIME_DELTA
    context.job_queue.run_once(send_reminder, when=reminder_time, chat_id=user_id, user_id=user_id, event_text=event_text, reminder_time=event_datetime.strftime('%H:%M'))
    
    await update.message.reply_html(
        f"<b>Новое событие успешно добавлено!</b><br>"
        f"ID: {new_id}<br>"
        f"Дата и время: {date_time_str}<br>"
        f"Событие: {event_text}",
        reply_markup=build_main_menu()
    )

async def delete_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрашивает подтверждение перед удалением конкретного события."""
    user_id = update.effective_user.id
    message_parts = update.message.text.split()
    
    if len(message_parts) != 3 or message_parts[0] != '/delete':
        await update.message.reply_html("<b>Используйте:</b> /delete ДАТА-ВРЕМЯ ID_СОБЫТИЯ")
        return
    
    date_time_str = message_parts[1]
    event_id = message_parts[2]
    
    success = schedule_manager.remove_schedule(user_id, date_time_str, event_id)
    
    if success:
        await update.message.reply_html(f"<b>Событие с ID {event_id} на {date_time_str} удалено.</b>", reply_markup=build_main_menu())
    else:
        await update.message.reply_html(f"<b>Не удалось найти событие с указанным ID.</b>", reply_markup=build_main_menu())

async def delete_all_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаляет все события на указанную дату и время."""
    user_id = update.effective_user.id
    message_parts = update.message.text.split()
    
    if len(message_parts) != 2 or message_parts[0] != '/clear':
        await update.message.reply_html("<b>Используйте:</b> /clear ДАТА-ВРЕМЯ")
        return
    
    date_time_str = message_parts[1]
    success = schedule_manager.clear_schedules_on_date(user_id, date_time_str)
    
    if success:
        await update.message.reply_html(f"<b>Все события на {date_time_str} удалены.</b>", reply_markup=build_main_menu())
    else:
        await update.message.reply_html(f"<b>У вас нет событий на эту дату и время.</b>", reply_markup=build_main_menu())

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кликов по кнопкам."""
    query = update.callback_query
    await query.answer()
    
    action = query.data
    
    if action.startswith('view_'):
        await view_schedule(update, context)

def main():
    """Главная функция приложения."""
    app = Application.builder().token(TOKEN).build()
    
    # Регистрация обработчиков команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("tomorrow", tomorrow))
    app.add_handler(CommandHandler("calendar", calendar))
    app.add_handler(CommandHandler("delete", delete_event))
    app.add_handler(CommandHandler("clear", delete_all_events))
    
    # Обработчик текстовых сообщений (добавление новых событий)
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), add_event))
    
    # Обработчик inline-кнопок
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Запуск бота
    print("Бот запущен...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()