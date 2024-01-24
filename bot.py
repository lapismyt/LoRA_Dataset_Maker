# Импортируем необходимые модули
import telebot # pyTelegramBotAPI
import os # для работы с файлами и папками
import requests # для отправки и получения запросов
import zipfile # для создания zip-архива
import shutil # для удаления папки

with open("tg_token.txt") as f:
    token = f.read().strip()

with open("imagga_key.txt") as f:
    imagga_key = f.read().strip()

with open("imagga_secret.txt") as f:
    imagga_secret = f.read().strip()

# Создаем экземпляр бота с токеном, полученным от BotFather
bot = telebot.TeleBot(token)

# Объявляем глобальные переменные для хранения информации о датасете
dataset_name = None # название датасета
trigger_tags = None # триггер-теги
image_count = 0 # счетчик картинок
image_tags = {} # словарь для хранения тегов для каждой картинки
image_index = 0

# Функция для генерации тегов для картинки с помощью бесплатного API
def gen_tags(image_path):
    # Здесь можно использовать любое API, которое принимает изображение и возвращает теги
    # Например, можно использовать Imagga API: https://docs.imagga.com/
    # Для этого нужно получить API ключ и секрет на сайте https://imagga.com/
    api_key = imagga_key
    api_secret = imagga_secret
    # Формируем запрос с изображением и отправляем его на сервер
    response = requests.post(
        'https://api.imagga.com/v2/tags',
        auth=(api_key, api_secret),
        files={'image': open(image_path, 'rb')})
    # Получаем ответ в формате JSON и извлекаем теги
    data = response.json()
    tags = data["result"]["tags"]
    # Составляем строку с тегами, разделенными запятыми
    tag_string = ", ".join([tag["tag"]["en"] for tag in tags[:12]])
    # Возвращаем строку с тегами
    return tag_string

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start(message):
    # Обнуляем все глобальные переменные
    global dataset_name, trigger_tags, image_count, image_tags
    dataset_name = None
    trigger_tags = None
    image_count = 0
    image_tags = {}
    image_index = 1
    # Отправляем приветственное сообщение и просим ввести название датасета
    bot.send_message(message.chat.id, "Привет! Я бот, который поможет тебе создать датасет для LoRA Stable Diffusion. Давай начнем. Как ты хочешь назвать свой датасет? Если в названии есть пробелы, я заменю их на \"_\".")

# Обработчик текстовых сообщений
@bot.message_handler(content_types=['text'])
def text(message):
    # Используем глобальные переменные
    global dataset_name, trigger_tags, image_count, image_tags, image_index
    # Проверяем, ввел ли пользователь название датасета
    if dataset_name is None:
        # Присваиваем переменной dataset_name введенный текст, заменив пробелы на "_"
        dataset_name = message.text.replace(" ", "_")
        # Создаем папку с названием датасета в папке dataset
        os.makedirs(f"dataset/{dataset_name}")
        # Отправляем сообщение с подтверждением названия и просим ввести триггер-теги
        bot.send_message(message.chat.id, f"Хорошо, твой датасет будет называться {dataset_name}. Теперь введи триггер-теги, которые будут добавляться в начало каждого описания картинки. Триггер-теги должны быть разделены запятыми.")
    # Проверяем, ввел ли пользователь триггер-теги
    elif trigger_tags is None:
        # Присваиваем переменной trigger_tags введенный текст
        trigger_tags = message.text
        # Отправляем сообщение с подтверждением тегов и просим отправить картинки
        bot.send_message(message.chat.id, f"Хорошо, твои триггер-теги: {trigger_tags}. Теперь можешь отправлять мне картинки, которые ты хочешь включить в датасет. Я буду сохранять их в папке dataset/{dataset_name}. Когда закончишь, отправь команду /done.")
    # Проверяем, отправил ли пользователь команду /done
    elif message.text == "/done":
        # Проверяем, есть ли хотя бы одна картинка в датасете
        if image_count > 0:
            # Отправляем сообщение с количеством картинок и начинаем обрабатывать их
            bot.send_message(message.chat.id, f"Окей, ты отправил мне {image_count} картинок. Теперь я буду генерировать теги для каждой картинки и просить тебя их проверить или отредактировать. Начнем с первой картинки.")
            # Вызываем функцию для обработки первой картинки
            process_image(message, 1)
        else:
            # Отправляем сообщение с ошибкой и просим отправить хотя бы одну картинку
            bot.send_message(message.chat.id, "Упс, ты не отправил мне ни одной картинки. Пожалуйста, отправь хотя бы одну картинку, прежде чем использовать команду /done.")
    elif message.text.lower() == "ok":
        image_index += 1
        image_tags[image_index] = f"{trigger_tags}, {image_tags[image_index]}"
        with open(f"dataset/{dataset_name}/{dataset_name}_{image_index}.txt", "w") as f:
            f.write(image_tags[image_index])
        process_image(message, image_index)
    else:
        image_index += 1
        image_tags[image_index] = f"{trigger_tags}, {message.text}"
        with open(f"dataset/{dataset_name}/{dataset_name}_{image_index}.txt", "w") as f:
            f.write(image_tags[image_index])
        process_image(message, image_index)

# Обработчик изображений
@bot.message_handler(content_types=['photo'])
def photo(message):
    # Используем глобальные переменные
    global dataset_name, trigger_tags, image_count, image_tags, image_index
    # Проверяем, ввел ли пользователь название датасета и триггер-теги
    if dataset_name is not None and trigger_tags is not None:
        # Увеличиваем счетчик картинок на 1
        image_count += 1
        # Получаем файл изображения
        file_info = bot.get_file(message.photo[-1].file_id)
        # Скачиваем файл изображения
        downloaded_file = bot.download_file(file_info.file_path)
        # Формируем путь для сохранения файла в папке dataset
        image_path = f"dataset/{dataset_name}/{dataset_name}_{image_count}.jpg"
        # Открываем файл для записи в бинарном режиме
        with open(image_path, 'wb') as new_file:
            # Записываем содержимое скачанного файла в новый файл
            new_file.write(downloaded_file)
        # Отправляем сообщение с подтверждением сохранения файла
        bot.send_message(message.chat.id, f"Я сохранил твою картинку под именем {dataset_name}_{image_count}.jpg в папке dataset/{dataset_name}. Продолжай отправлять мне картинки или используй команду /done, когда закончишь.")
    else:
        # Отправляем сообщение с ошибкой и просим ввести название датасета и триггер-теги
        bot.send_message(message.chat.id, "Я не могу сохранить твою картинку, пока ты не введешь название датасета и триггер-теги. Пожалуйста, используй команду /start и следуй инструкциям.")

# Функция для обработки картинок и генерации тегов
def process_image(message, image_number):
    # Используем глобальные переменные
    global dataset_name, trigger_tags, image_count, image_tags, image_index
    # Проверяем, не превышает ли номер картинки количество картинок в датасете
    if image_number <= image_count:
        # Формируем путь к файлу картинки в папке dataset
        image_path = f"dataset/{dataset_name}/{dataset_name}_{image_number}.jpg"
        # Вызываем функцию для генерации тегов для картинки
        tag_string = gen_tags(image_path)
        # Сохраняем теги в словаре image_tags по номеру картинки
        image_tags[image_number] = tag_string
        # Открываем файл картинки в бинарном режиме
        with open(image_path, 'rb') as image_file:
            # Отправляем пользователю картинку и сгенерированные теги
            bot.send_photo(message.chat.id, image_file, caption=f"Вот теги, которые я сгенерировал для этой картинки: {tag_string}. Пожалуйста, проверь их и при необходимости отредактируй. Отправь мне исправленные теги или напиши \"ОК\", если ты согласен с тегами.")
    else:
        # Отправляем сообщение с уведомлением о завершении обработки всех картинок
        bot.send_message(message.chat.id, f"Я обработал все {image_count} картинок и сгенерировал теги для каждой из них. Теперь я создам zip-архив с файлами из папки dataset и отправлю тебе его.")
        # Вызываем функцию для создания и отправки zip-архива
        send_zip(message)

# Функция для создания и отправки zip-архива
def send_zip(message):
    # Используем глобальные переменные
    global dataset_name, trigger_tags, image_count, image_tags
    # Формируем путь к папке с датасетом
    folder_path = f"dataset/{dataset_name}"
    # Формируем путь к zip-файлу с датасетом
    zip_path = f"dataset/{dataset_name}.zip"
    # Создаем zip-архив
    zip_file = zipfile.ZipFile(zip_path, "w")
    # Добавляем в zip-архив все файлы из папки с датасетом
    for i in range(1, image_count + 1):
        # Формируем пути к файлам картинки и тегов
        image_path = f"{folder_path}/{dataset_name}_{i}.jpg"
        tag_path = f"{folder_path}/{dataset_name}_{i}.txt"
        # Добавляем файлы в zip-архив
        zip_file.write(image_path, os.path.basename(image_path))
        zip_file.write(tag_path, os.path.basename(tag_path))
    # Закрываем zip-архив
    zip_file.close()
    # Открываем zip-файл в бинарном режиме
    with open(zip_path, "rb") as zip_file:
        # Отправляем пользователю zip-файл
        bot.send_document(message.chat.id, zip_file, caption=f"Вот твой датасет {dataset_name}.zip. Надеюсь, он тебе пригодится.")
    # Удаляем папку и zip-файл с датасетом
    shutil.rmtree(folder_path)
    os.remove(zip_path)
    # Отправляем сообщение с благодарностью и предложением начать заново
    bot.send_message(message.chat.id, "Спасибо, что воспользовался моим сервисом. Если ты хочешь создать еще один датасет, используй команду /start.")

if __name__ == "__main__":
    bot.infinity_polling()
