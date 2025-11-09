import os
import telebot
from flask import Flask, request
from PIL import Image, ImageOps
import io
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import tempfile
import threading

# Получаем токен из переменных окружения Railway
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', "8204855927:AAE6WxvaZl-kqM3zbSRql1J_dr1l1NteYeA")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
user_sessions = {}

# Ваш существующий код функций (оставляем без изменений)
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if user_id not in user_sessions:
        user_sessions[user_id] = {'photos': [], 'format': 'pdf'}

    current_format = user_sessions[user_id]['format']
    format_name = "PDF" if current_format == 'pdf' else "DOCX"

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_pdf = telebot.types.KeyboardButton('📄 PDF')
    btn_docx = telebot.types.KeyboardButton('📝 DOCX')
    btn_create = telebot.types.KeyboardButton('/create')
    btn_status = telebot.types.KeyboardButton('/status')
    markup.add(btn_pdf, btn_docx, btn_create, btn_status)

    bot.send_message(
        message.chat.id,
        f"📸 Привет! Я бот для создания PDF или DOCX из фото.\n\n"
        f"🎯 Текущий формат: {format_name}\n"
        f"📷 Фото: {len(user_sessions[user_id]['photos'])}\n\n"
        "Используй кнопки для управления:",
        reply_markup=markup
    )

@bot.message_handler(commands=['help'])
def help_cmd(message):
    help_text = """
📖 **Команды бота:**

/start - показать меню
/help - показать справку
/create - создать документ
/clear - очистить все фото
/status - показать статус
/reset - полный сброс

🖼️ **Как использовать:**
1. Выбери формат (PDF или DOCX)
2. Отправляй фото (по одному или группой)
3. Нажми /create для создания документа
4. Получи готовый файл!

💡 **Особенности форматов:**
• 📄 PDF - отлично сохраняет качество, универсальный
• 📝 DOCX - можно редактировать, добавлять текст
"""
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(commands=['format'])
def choose_format(message):
    user_id = message.from_user.id
    if user_id not in user_sessions:
        user_sessions[user_id] = {'photos': [], 'format': 'pdf'}

    current_format = user_sessions[user_id]['format']
    current_format_name = "PDF" if current_format == 'pdf' else "DOCX"

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_pdf = telebot.types.KeyboardButton('📄 PDF')
    btn_docx = telebot.types.KeyboardButton('📝 DOCX')
    btn_back = telebot.types.KeyboardButton('Назад')
    markup.add(btn_pdf, btn_docx, btn_back)

    bot.send_message(
        message.chat.id,
        f"🎯 Текущий формат: {current_format_name}\n\n"
        f"Выбери новый формат документа:",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: message.text in ['📄 PDF', '📝 DOCX', 'Назад'])
def handle_format_choice(message):
    user_id = message.from_user.id
    if user_id not in user_sessions:
        user_sessions[user_id] = {'photos': [], 'format': 'pdf'}

    if message.text == 'Назад':
        show_main_menu(message)
        return

    if message.text == '📄 PDF':
        user_sessions[user_id]['format'] = 'pdf'
        format_name = "PDF"
    else:
        user_sessions[user_id]['format'] = 'docx'
        format_name = "DOCX"

    show_main_menu(message, f"✅ Установлен формат: {format_name}")

def show_main_menu(message, additional_text=""):
    user_id = message.from_user.id
    if user_id not in user_sessions:
        user_sessions[user_id] = {'photos': [], 'format': 'pdf'}

    current_format = user_sessions[user_id]['format']
    format_name = "PDF" if current_format == 'pdf' else "DOCX"

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_pdf = telebot.types.KeyboardButton('📄 PDF')
    btn_docx = telebot.types.KeyboardButton('📝 DOCX')
    btn_create = telebot.types.KeyboardButton('/create')
    btn_status = telebot.types.KeyboardButton('/status')
    markup.add(btn_pdf, btn_docx, btn_create, btn_status)

    text = f"📸 Бот для создания документов из фото\n\n"
    if additional_text:
        text += f"{additional_text}\n\n"
    text += f"🎯 Текущий формат: {format_name}\n"
    text += f"📷 Фото: {len(user_sessions[user_id]['photos'])}\n\n"
    text += "Используй кнопки для управления:"

    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.from_user.id

    if user_id not in user_sessions:
        user_sessions[user_id] = {'photos': [], 'format': 'pdf'}

    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    user_sessions[user_id]['photos'].append(downloaded_file)
    count = len(user_sessions[user_id]['photos'])
    format_name = "PDF" if user_sessions[user_id]['format'] == 'pdf' else "DOCX"

    bot.reply_to(
        message,
        f"✅ Фото {count} получено!\n"
        f"Формат: {format_name}\n\n"
        f"Отправьте ещё фото или /create для создания документа"
    )

@bot.message_handler(commands=['create'])
def create_document(message):
    user_id = message.from_user.id

    if user_id not in user_sessions or not user_sessions[user_id]['photos']:
        bot.reply_to(message, "❌ Сначала отправьте фото!")
        return

    try:
        bot.send_message(message.chat.id, "🔄 Создаю документ...")

        format_type = user_sessions[user_id]['format']
        photos = user_sessions[user_id]['photos']

        if format_type == 'pdf':
            file_buffer = create_pdf(photos)
            file_name = "photos.pdf"
            caption = f"📄 Ваш PDF файл готов!\nСтраниц: {len(photos)}"
        else:
            file_buffer = create_docx(photos)
            file_name = "photos.docx"
            caption = f"📝 Ваш DOCX файл готов!\nСтраниц: {len(photos)}"

        bot.send_document(
            message.chat.id,
            file_buffer,
            visible_file_name=file_name,
            caption=caption
        )

        user_sessions[user_id]['photos'] = []

    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка при создании документа: {e}")

def create_pdf(photos_bytes):
    """Создает PDF из списка байтов фото"""
    images = []
    for photo_bytes in photos_bytes:
        image = Image.open(io.BytesIO(photo_bytes))

        try:
            image = ImageOps.exif_transpose(image)
        except:
            pass

        if image.mode != 'RGB':
            image = image.convert('RGB')
        images.append(image)

    pdf_buffer = io.BytesIO()

    if len(images) == 1:
        images[0].save(pdf_buffer, format='PDF', quality=95)
    else:
        images[0].save(
            pdf_buffer,
            format='PDF',
            save_all=True,
            append_images=images[1:],
            quality=95
        )

    pdf_buffer.seek(0)
    return pdf_buffer

def create_docx(photos_bytes):
    """Создает DOCX документ из списка байтов фото с заполнением всей страницы"""
    doc = Document()

    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(0.5)
        section.right_margin = Inches(0.5)

    content_width = 7.5
    content_height = 10.0

    for i, photo_bytes in enumerate(photos_bytes):
        image_stream = io.BytesIO(photo_bytes)

        with Image.open(image_stream) as img:
            try:
                img = ImageOps.exif_transpose(img)
            except:
                pass

            img_width, img_height = img.size
            aspect_ratio = img_height / img_width
            page_aspect_ratio = content_height / content_width

            if aspect_ratio > page_aspect_ratio:
                calculated_height = Inches(content_height)
                calculated_width = Inches(content_height / aspect_ratio)
            else:
                calculated_width = Inches(content_width)
                calculated_height = Inches(content_width * aspect_ratio)

        image_stream.seek(0)

        paragraph = doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER

        run = paragraph.add_run()
        run.add_picture(image_stream, width=calculated_width, height=calculated_height)

        if i < len(photos_bytes) - 1:
            doc.add_page_break()

    doc_buffer = io.BytesIO()
    doc.save(doc_buffer)
    doc_buffer.seek(0)

    return doc_buffer

@bot.message_handler(commands=['clear'])
def clear_photos(message):
    user_id = message.from_user.id
    if user_id in user_sessions and user_sessions[user_id]['photos']:
        count = len(user_sessions[user_id]['photos'])
        user_sessions[user_id]['photos'] = []
        bot.reply_to(message, f"🗑️ Удалено {count} фото")
        show_main_menu(message)
    else:
        bot.reply_to(message, "ℹ️ Нет фото для очистки")

@bot.message_handler(commands=['reset'])
def reset_session(message):
    user_id = message.from_user.id
    if user_id in user_sessions:
        count = len(user_sessions[user_id]['photos'])
        user_sessions[user_id] = {'photos': [], 'format': 'pdf'}
        bot.reply_to(message, f"🔄 Сессия сброшена! Удалено {count} фото")
        show_main_menu(message)
    else:
        user_sessions[user_id] = {'photos': [], 'format': 'pdf'}
        bot.reply_to(message, "🔄 Сессия создана!")

@bot.message_handler(commands=['status'])
def show_status(message):
    user_id = message.from_user.id
    if user_id in user_sessions:
        photos_count = len(user_sessions[user_id]['photos'])
        format_type = user_sessions[user_id]['format']
        format_name = "PDF" if format_type == 'pdf' else "DOCX"

        status_text = (
            f"📊 Статус:\n"
            f"• Фото: {photos_count}\n"
            f"• Формат: {format_name}\n"
        )

        if photos_count > 0:
            status_text += f"\n✅ Готов к созданию! Используй /create"
        else:
            status_text += f"\n📸 Отправь фото чтобы начать"

        bot.reply_to(message, status_text)
    else:
        bot.reply_to(message, "ℹ️ Начни с /start")

@bot.message_handler(func=lambda message: True)
def handle_other_messages(message):
    if message.text.startswith('/'):
        bot.reply_to(message, "❌ Неизвестная команда. Используй /help для справки")
    else:
        show_main_menu(message)

# Новый код для Railway
@app.route('/')
def home():
    return "🤖 Telegram Bot is running! Use /start in Telegram."

@app.route('/health')
def health():
    return "OK"

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        return 'Invalid content type', 403

def set_webhook():
    # Устанавливаем вебхук для Railway
    webhook_url = f"https://{os.environ.get('RAILWAY_STATIC_URL', '')}/webhook"
    if webhook_url.startswith('https://'):
        bot.remove_webhook()
        bot.set_webhook(url=webhook_url)
        print(f"Webhook set to: {webhook_url}")
    else:
        print("Using polling mode")

def run_bot():
    """Запускает бота в режиме polling (как запасной вариант)"""
    print("🚀 Бот запущен в режиме polling!")
    print("📸 Форматы: PDF и DOCX")
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ Ошибка в боте: {e}")

if __name__ == '__main__':
    # Пытаемся установить вебхук, если доступен URL
    set_webhook()
    
    # Запускаем Flask приложение
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port)
