import os
import requests
from PIL import Image
from io import BytesIO
import telebot

with open("tg_token.txt") as f:
    token = f.read().strip()


bot = telebot.TeleBot(token)
session = requests.Session()

apis = [
    "api.rule34.xxx",
    "gelbooru.com",
    "safebooru.org"
]

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Какой датасет вы хотите собрать?")
    bot.register_next_step_handler(message, process_dataset_name_step)

def process_dataset_name_step(message):
    try:
        chat_id = message.chat.id
        dataset_name = message.text
        dataset_folder = f"./dataset/{dataset_name}"
        if not os.path.exists(dataset_folder):
            os.makedirs(dataset_folder)
        
        msg = bot.send_message(chat_id, 'Сколько изображений скачать?')
        bot.register_next_step_handler(msg, process_image_limit_step, dataset_folder)
    except Exception as e:
        bot.reply_to(message, 'oooops')

def process_image_limit_step(message, dataset_folder):
    try:
        chat_id = message.chat.id
        image_limit = int(message.text)
        
        msg = bot.send_message(chat_id, 'Введите триггер::')
        bot.register_next_step_handler(msg, process_tags_step, dataset_folder, image_limit)
    except Exception as e:
        bot.reply_to(message, 'Ошибка ввода. Попробуйте ввести число ещё раз.')
        bot.register_next_step_handler(message, process_image_limit_step, dataset_folder)

def process_tags_step(message, dataset_folder, image_limit):
    try:
        chat_id = message.chat.id
        tags = message.text.strip().replace(', ', '+').replace(' ', '_')
        bot.send_message(message.chat.id, "Собираю изображения...")
        images_downloaded = download_images(dataset_folder, tags, image_limit)
        bot.send_message(chat_id, f'Загружено {images_downloaded} изображений.')
    except Exception as e:
        bot.reply_to(message, 'oooops')
        print(repr(e))


def download_images(dataset_folder, tags, image_limit):
    global apis
    num_images_saved = 0
    page_number = 1
    while num_images_saved < image_limit:
        url = f"https://api.rule34.xxx/index.php?page=dapi&s=post&q=index&json=1&limit=100&tags={tags}&pid={page_number}&deleted=show"
        print(f"Page URL: {url}")
        response = session.get(url)
        posts = response.json()

        if not posts:
            break

        #if int(posts["@attributes"]["count"]) < image_limit:
        #    image_limit = int(posts["@attributes"]["count"])

        #if not "post" in posts.keys():
        #    break

        for post in posts:
            if num_images_saved >= image_limit:
                break
            
            image_url = post['file_url']
            if not image_url or not image_url.endswith(('.jpg', '.jpeg', '.png')):
                continue
            
            try:
                print(f"Image URL: {image_url}")
                response = session.get(image_url, stream=True)
                response.raise_for_status()

                with Image.open(BytesIO(response.content)) as img:
                    if img.format in ['JPEG', 'JPG']:
                        img = img.convert('RGB')
                    
                    num_images_saved += 1
                    filename = os.path.join(dataset_folder, f'{num_images_saved}.png')
                    img.save(filename, 'PNG')
                with open(os.path.join(dataset_folder, f"{num_images_saved}.txt"), "w") as f:
                    f.write(f"{tags}, {post['tags']}")

            except Exception as e:
                print(f"Could not download image. Error: {e}")

        page_number += 1
    
    return num_images_saved

bot.infinity_polling(timeout = 20, long_polling_timeout = 10)
