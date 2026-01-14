import os
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
DATA_FILE = "tasks.json"

# Структура для хранения задач
# {user_id: {task_id: {"text": "текст задачи", "date": "дата создания"}}}

class TaskManager:
    def __init__(self):
        self.tasks = self.load_tasks()
    
    def load_tasks(self):
        """Загрузить задачи из файла"""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_tasks(self):
        """Сохранить задачи в файл"""
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.tasks, f, ensure_ascii=False, indent=2)
    
    def add_task(self, user_id: int, task_text: str) -> int:
        """Добавить задачу и вернуть её ID"""
        if str(user_id) not in self.tasks:
            self.tasks[str(user_id)] = {}
        
        # Генерируем новый ID
        task_id = 1
        if self.tasks[str(user_id)]:
            task_id = max(map(int, self.tasks[str(user_id)].keys())) + 1
        
        self.tasks[str(user_id)][str(task_id)] = {
            "text": task_text,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.save_tasks()
        return task_id
    
    def get_tasks(self, user_id: int) -> dict:
        """Получить все задачи пользователя"""
        return self.tasks.get(str(user_id), {})
    
    def delete_task(self, user_id: int, task_id: str) -> bool:
        """Удалить задачу по ID"""
        user_tasks = self.tasks.get(str(user_id))
        if user_tasks and task_id in user_tasks:
            del user_tasks[task_id]
            self.save_tasks()
            return True
        return False
    
    def clear_all_tasks(self, user_id: int) -> bool:
        """Удалить все задачи пользователя"""
        if str(user_id) in self.tasks:
            self.tasks[str(user_id)] = {}
            self.save_tasks()
            return True
        return False

# Инициализация менеджера задач
task_manager = TaskManager()

# Команды бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    welcome_text = (
        "📝 *Бот для управления задачами*\n\n"
        "Доступные команды:\n"
        "/start - Начало работы\n"
        "/add - Добавить новую задачу\n"
        "/list - Показать все задачи\n"
        "/delete - Удалить задачу\n"
        "/clear - Удалить все задачи\n\n"
        "Просто отправьте текст, чтобы добавить задачу!"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /add"""
    await update.message.reply_text(
        "📝 Отправьте текст новой задачи:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel_add")]
        ])
    )

async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /list"""
    user_id = update.effective_user.id
    tasks = task_manager.get_tasks(user_id)
    
    if not tasks:
        await update.message.reply_text("📭 Список задач пуст!")
        return
    
    # Формируем список задач
    tasks_list = ["📋 *Ваши задачи:*\n"]
    for task_id, task_info in tasks.items():
        task_text = task_info['text']
        task_date = task_info['date']
        tasks_list.append(f"🔹 *{task_id}.* {task_text}")
        tasks_list.append(f"   📅 Создано: {task_date}\n")
    
    # Разбиваем на сообщения, если список слишком длинный
    full_text = "\n".join(tasks_list)
    if len(full_text) > 4000:
        chunks = [full_text[i:i+4000] for i in range(0, len(full_text), 4000)]
        for chunk in chunks:
            await update.message.reply_text(chunk, parse_mode='Markdown')
    else:
        await update.message.reply_text(full_text, parse_mode='Markdown')

async def delete_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /delete"""
    user_id = update.effective_user.id
    tasks = task_manager.get_tasks(user_id)
    
    if not tasks:
        await update.message.reply_text("📭 Нет задач для удаления!")
        return
    
    # Создаем кнопки для удаления задач
    keyboard = []
    row = []
    for task_id, task_info in tasks.items():
        # Обрезаем текст задачи для отображения в кнопке
        short_text = task_info['text'][:20] + "..." if len(task_info['text']) > 20 else task_info['text']
        button = InlineKeyboardButton(
            f"❌ {task_id}. {short_text}",
            callback_data=f"delete_{task_id}"
        )
        row.append(button)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🗑 Удалить все", callback_data="delete_all")])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_delete")])
    
    await update.message.reply_text(
        "🗑 *Выберите задачу для удаления:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def clear_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /clear"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, удалить все", callback_data="confirm_clear"),
            InlineKeyboardButton("❌ Нет, отменить", callback_data="cancel_clear")
        ]
    ]
    
    await update.message.reply_text(
        "⚠️ *Вы уверены, что хотите удалить ВСЕ задачи?*\n"
        "Это действие нельзя отменить!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений (для добавления задач)"""
    user_id = update.effective_user.id
    task_text = update.message.text.strip()
    
    if not task_text:
        await update.message.reply_text("❌ Задача не может быть пустой!")
        return
    
    # Добавляем задачу
    task_id = task_manager.add_task(user_id, task_text)
    
    await update.message.reply_text(
        f"✅ *Задача добавлена!*\n"
        f"ID: {task_id}\n"
        f"Текст: {task_text}",
        parse_mode='Markdown'
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    callback_data = query.data
    
    # Обработка добавления задачи
    if callback_data == "cancel_add":
        await query.edit_message_text("❌ Добавление задачи отменено")
    
    # Обработка удаления задач
    elif callback_data.startswith("delete_"):
        if callback_data == "delete_all":
            # Удалить все задачи
            task_manager.clear_all_tasks(user_id)
            await query.edit_message_text("✅ Все задачи удалены!")
        else:
            # Удалить конкретную задачу
            task_id = callback_data.split("_")[1]
            if task_manager.delete_task(user_id, task_id):
                await query.edit_message_text(f"✅ Задача {task_id} удалена!")
            else:
                await query.edit_message_text(f"❌ Задача {task_id} не найдена!")
    
    elif callback_data == "cancel_delete":
        await query.edit_message_text("❌ Удаление отменено")
    
    # Обработка очистки всех задач
    elif callback_data == "confirm_clear":
        task_manager.clear_all_tasks(user_id)
        await query.edit_message_text("✅ Все задачи удалены!")
    
    elif callback_data == "cancel_clear":
        await query.edit_message_text("❌ Очистка отменена")

def main():
    """Основная функция запуска бота"""
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_task))
    application.add_handler(CommandHandler("list", list_tasks))
    application.add_handler(CommandHandler("delete", delete_task))
    application.add_handler(CommandHandler("clear", clear_tasks))
    
    # Регистрируем обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Регистрируем обработчик callback-запросов от кнопок
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Запускаем бота
    print("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()