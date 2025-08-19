import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
import requests
import xmltodict
import re
from urllib.parse import urlencode
import os

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Функция для команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        'Привет! Я бот для отслеживания машин.\n'
        'Используй команды:\n'
        '/car <номер> - информация о машине\n'
        '/cars - список машин с координатами'
    )

# Функция для получения информации о машине
async def car_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text('Пожалуйста, укажи номер машины, например: /car 1729')
        return

    car_no = context.args[0]
    click_counter = str(int(context.job_queue.scheduler.time() * 1000))
    url = 'https://www.nyc2way.com/nyc2waymap/frmOneCarInfo.aspx'
    params = {
        'clickCounter': click_counter,
        'Carno': car_no,
        'Comp': '13',
        'ConfNo': '200'
    }
    headers = {'X-Requested-With': 'XMLHttpRequest'}

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        
        # Парсинг HTML-ответа
        html = response.text
        label_match = re.search(r'<span id="Label1".*?>(.*?)</span>', html, re.DOTALL)
        address_match = re.search(r'<input name="txtoAddress".*?value="(.*?)"', html)
        image_match = re.search(r'<img id="Image1" src="(.*?)"', html)

        if label_match and address_match:
            label = label_match.group(1).replace('</BR>', '\n').strip()
            address = address_match.group(1)
            image = f"https://www.nyc2way.com/nyc2waymap/{image_match.group(1)}" if image_match else None

            # Формируем ответ
            message = f"{label}\nАдрес: {address}"
            if image:
                await update.message.reply_photo(photo=image, caption=message)
            else:
                await update.message.reply_text(message)
        else:
            await update.message.reply_text('Не удалось получить информацию о машине.')
    except requests.RequestException as e:
        await update.message.reply_text(f'Ошибка при запросе: {str(e)}')

# Функция для получения списка машин
async def car_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    click_counter = str(int(context.job_queue.scheduler.time() * 1000))
    url = 'https://www.nyc2way.com/nyc2waymap/CarListXML.aspx'
    params = {
        'clickCounter': click_counter,
        'CarNo': '',
        'Comp': '0',
        'CarType': '0',
        'JobStat': '0',
        'JobType': '0'
    }
    headers = {'X-Requested-With': 'XMLHttpRequest'}

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()

        # Парсинг XML-ответа
        xml_data = xmltodict.parse(response.text)
        markers = xml_data['markers']['marker']
        
        # Формируем сообщение
        message = "Список машин:\n"
        keyboard = []
        for i, marker in enumerate(markers[:10]):  # Ограничиваем до 10 машин
            car_no = marker['@CarNo']
            lat = marker['@lat']
            lng = marker['@lng']
            car_type = marker['@CarType']
            message += f"Машина #{car_no}, Тип: {car_type}, Координаты: ({lat}, {lng})\n"
            
            # Добавляем кнопку для отображения на карте
            google_maps_url = f"https://www.google.com/maps?q={lat},{lng}"
            keyboard.append([InlineKeyboardButton(f"Машина #{car_no}", url=google_maps_url)])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, reply_markup=reply_markup)
    except requests.RequestException as e:
        await update.message.reply_text(f'Ошибка при запросе: {str(e)}')

# Функция обработки ошибок
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.warning('Update "%s" caused error "%s"', update, context.error)
    await update.message.reply_text('Произошла ошибка. Попробуй снова!')

async def main():
    # Инициализация бота с токеном
    token = os.getenv("TOKEN", "7841070383:AAGWXVdBMbn7sdlQFlLQWifEavIfU_coz0E")
    application = Application.builder().token(token).build()

    # Регистрируем команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("car", car_info))
    application.add_handler(CommandHandler("cars", car_list))
    application.add_error_handler(error_handler)

    # Настройка Webhook
    await application.bot.set_webhook(url=f"https://your-app-name.fly.dev/{token}")

    # Запуск приложения
    await application.run_webhook(
        listen="0.0.0.0",
        port=8443,
        url_path=token,
        webhook_url=f"https://your-app-name.fly.dev/{token}"
    )

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
