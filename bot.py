import os
import telebot
import requests
from itertools import cycle

with open("tg_token.txt") as f:
    token = f.read().strip()

bot = telebot.TeleBot(token)
session = requests.Session()

def get_free_proxies():
    proxy_api_url = "https://www.proxy-list.download/api/v1/get?type=http&anon=transparent"
    response = requests.get(proxy_api_url)
    # предполагаем, что ответ содержит список прокси в формате IP:PORT
    proxy_list = response.content..decode().strip().split("\n")
    return [{'http': f'http://{proxy}', 'https': f'http://{proxy}'} for proxy in proxy_list]

proxies = get_free_proxies()
proxy_pool = cycle(proxies)

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Привет! Введите имя датасета:")
    bot.register_next_step_handler(message, get_dataset_name)

def get_dataset_name(message):
    dataset_name = message.text
    bot.send_message(message.chat.id, "Введите триггер-тег:")
    bot.register_next_step_handler(message, get_trigger_tag, dataset_name)

def get_trigger_tag(message, dataset_name):
    trigger_tag = message.text
    bot.send_message(message.chat.id, "Введите теги для поиска (через запятую):")
    bot.register_next_step_handler(message, get_search_tags, dataset_name, trigger_tag)

def get_search_tags(message, dataset_name, trigger_tag):
    search_tags = message.text.split(",")
    search_tags = [tag.strip() for tag in search_tags]

    dataset_path = os.path.join("dataset", dataset_name)
    if not os.path.exists(dataset_path):
        os.makedirs(dataset_path)

    num_images_saved = download_images(dataset_path, search_tags, trigger_tag, 100)
    
    bot.send_message(message.chat.id, f"Датасет '{dataset_name}' собран. Найдено {num_images_saved} изображений.")

def download_images(dataset_path, search_tags, trigger_tag, dataset_limit):
    num_images_saved = 0
    page_number = 1
    current_proxy = next(proxy_pool)

    while num_images_saved < dataset_limit:
        try:
            url = f"https://danbooru.donmai.us/posts.json?limit=100&page={page_number}&tags={'+'.join(search_tags)}"
            response = session.get(url, proxies=current_proxy)
            response.raise_for_status()
            data = response.json()

            if not data:
                break

            for post in data:
                if trigger_tag not in post["tag_string"]:
                    continue

                image_url = post.get("file_url")
                if not image_url:
                    continue

                image_response = session.get(image_url, stream=True, proxies=current_proxy)
                if image_response.status_code == 200:
                    image_path = os.path.join(dataset_path, f"{num_images_saved}.png")
                    with open(image_path, 'wb') as f:
                        for chunk in image_response.iter_content(1024):
                            f.write(chunk)

                    tags = post["tag_string"].split()
                    tags_path = os.path.join(dataset_path, f"{num_images_saved}.txt")
                    with open(tags_path, "w") as f:
                        f.write(f"{trigger_tag}, {', '.join(tags)}".replace("_", " "))

                    num_images_saved += 1
                    if num_images_saved >= dataset_limit:
                        break

            page_number += 1
            if num_images_saved >= dataset_limit:
                break

        except requests.exceptions.RequestException as e:
            print(f'Error with proxy {current_proxy}, trying next one.')
            current_proxy = next(proxy_pool)

    return num_images_saved

bot.infinity_polling()
