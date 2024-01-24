import os
import zipfile
import requests
import telebot
import json

with open("tg_token.txt") as f:
    tg_token = f.read().strip()

with open("imagga_key.txt") as f:
    imagga_key = f.read().strip()

with open("imagga_secret.txt") as f:
    imagga_secret = f.read().strip()

bot = telebot.TeleBot(tg_token)

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Привет! Добро пожаловать в бот для создания датасета для LoRA Stable Diffusion.")

    bot.send_message(message.chat.id, "Пожалуйста, введите название датасета:")
    bot.register_next_step_handler(message, get_dataset_name)

def get_dataset_name(message):
    dataset_name = message.text.replace(" ", "_")

    bot.send_message(message.chat.id, "Пожалуйста, введите триггер-теги:")
    bot.register_next_step_handler(message, get_trigger_tags, dataset_name)


def get_trigger_tags(message, dataset_name):
    trigger_tags = message.text

    bot.send_message(message.chat.id, "Отправьте мне картинки для датасета.\nКогда закончите, отправьте команду /done.")
    bot.register_next_step_handler(message, get_images, dataset_name, trigger_tags, 1)

def get_images(message, dataset_name, trigger_tags, image_number):
    if message.content_type == "photo":
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        image_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"
        image_path = f"dataset/{dataset_name}_{image_number:02}.jpg"
        with open(image_path, 'wb') as image_file:
            image_file.write(requests.get(image_url).content)
        bot.send_message(message.chat.id, f"Изображение {image_number:02} сохранено! Пришлите следующее или команду /done.")
        image_number += 1
        bot.register_next_step_handler(message, get_images, dataset_name, trigger_tags, image_number)
    elif hasattr(message, "text"):
        if message.text == "/done":
            image_count = image_number
            process_images(message, dataset_name, trigger_tags, 1, image_count)

def process_images(message, dataset_name, trigger_tags, image_number, image_count):
    if True:
        if image_number < image_count:
            image_path = f"dataset/{dataset_name}_{image_number:02}.jpg"
            # Генерируем теги
            tags = gen_tags(image_path)

            # Отправляем пользователю картинку и сгенерированные теги
            bot.send_photo(message.chat.id, open(image_path, 'rb'))
            bot.send_message(message.chat.id, f"Сгенерированные теги: `{tags}`", parse_mode="markdown")
            bot.send_message(message.chat.id, "Пожалуйста, отредактируйте теги или введите новые теги:")
            bot.register_next_step_handler(message, get_tags, dataset_name, trigger_tags, image_number, image_count)
        else:
            os.system(f"cp -r dataset /storage/emulated/0/{dataset_name}")
            for file_name in os.listdir("dataset"):
                os.remove(os.path.join("dataset", file_name))

            bot.send_message(message.chat.id, "Датасет готов!")
            bot.send_message(message.chat.id, "Вы можете создать новый датасет с помощью команды /start")
    else:
        bot.send_message(message.chat.id, "Пожалуйста, отправьте фото или команду /done.")

def get_tags(message, dataset_name, trigger_tags, image_number, image_count):
    if hasattr(message, "text"):
        caption_path = f"dataset/{dataset_name}_{image_number:02}.txt"
        with open(caption_path, "w") as f:
            f.write(f"{trigger_tags}, {message.text}")
        image_number += 1
        bot.send_message(message.chat.id, "Теги сохранены!")
        process_images(message, dataset_name, trigger_tags, image_number, image_count)

def gen_tags(image_path):
    global imagga_key, imagga_secret
    final_tags = []
    response = requests.post(
        'https://api.imagga.com/v2/tags',
        auth=(imagga_key, imagga_secret),
        files={'image': open(image_path, 'rb')})
    data = response.json()
    tags = data["result"]["tags"]
    for tag in tags:
        if tag["confidence"] >= 20:
            final_tags.append(tag["tag"]["en"])
    tag_string = ", ".join(final_tags)
    return tag_string


bot.infinity_polling()
