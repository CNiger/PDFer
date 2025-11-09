import os
import telebot
from flask import Flask, request
import threading
from PIL import Image, ImageOps
import io
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Получаем токен из переменных окружения Railway
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', "8204855927:AAE6WxvaZl-kqM3zbSRql1J_dr1l1NteYeA")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
user_sessions = {}

# Ваши существующие функции (без изменений)
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
"""
    bot.send_message(message.chat.id, help_text)

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
    else:
        bot.reply_to(message, "ℹ️ Нет фото для очистки")

@bot.message_handler(commands=['status'])
def show_status(message):
    user_id = message.from_user.id
    if user_id in user_sessions:
        photos_count = len(user_sessions[user_id]['photos'])
        format_type = user_sessions[user_id]['format']
        format_name = "PDF" if format_type == 'pdf' else "DOCX"
        status_text = f"📊 Статус:\n• Фото: {photos_count}\n• Формат: {format_name}"
        bot.reply_to(message, status_text)
    else:
        bot.reply_to(message, "ℹ️ Начни с /start")

# Flask маршруты для Railway
@app.route('/')
def home():
    return "🤖 Telegram Bot is running! Use /start in Telegram."

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        return 'Invalid content type', 403

# Функция для установки вебхука
def set_webhook():
    try:
        # Получаем URL приложения из переменных окружения Railway
        railway_url = os.environ.get('RAILWAY_STATIC_URL')
        if railway_url:
            webhook_url = f"{railway_url}/webhook"
            bot.remove_webhook()
            bot.set_webhook(url=webhook_url)
            print(f"✅ Webhook установлен: {webhook_url}")
        else:
            print("ℹ️ RAILWAY_STATIC_URL не найден, используем polling")
            # Запускаем polling в отдельном потоке
            threading.Thread(target=run_polling, daemon=True).start()
    except Exception as e:
        print(f"❌ Ошибка установки webhook: {e}")
        threading.Thread(target=run_polling, daemon=True).start()

def run_polling():
    print("🔄 Запускаем бота в режиме polling...")
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ Ошибка в polling: {e}")

# При запуске приложения
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting server on port {port}")
    
    # Пытаемся установить вебхук
    set_webhook()
    
    # Запускаем Flask
    app.run(host='0.0.0.0', port=port)
else:
    # Для запуска через Gunicorn
    set_webhook()
