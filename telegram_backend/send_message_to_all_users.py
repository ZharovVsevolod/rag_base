import asyncio
from telegram import Bot
from bairdotr.config import DATA_FOLDER, TELEGRAM_CHAT_IDS_EYE
import os
from dotenv import load_dotenv

load_dotenv()

bot = Bot(token = os.environ["TELEGRAM_BOT_API"])

def read_all_saved_chat_id() -> list:
    """Прочесть файл с сохранёнными chat_id и вернуть лист с ними"""
    filename = DATA_FOLDER + "/" + TELEGRAM_CHAT_IDS_EYE
    with open(filename) as file:
        ids = file.readlines()
    ids = [i[:-1] for i in ids] # убираем \n в конце

    return ids

def get_message() -> str:
    """Сообщение, которое надо массового разослать"""
    return """🌟 Уважаемые коллеги! 🌟

Мы рады сообщить вам о появлении новой функции — «Пробив физического лица»! 🎉 

Хотим заметить что фича доступна только узкому сегменту наших пользователей, одним из которых являетесь Вы! 🎉

Теперь можно легко и быстро проверять информацию о людях, что станет особенно полезным для сотрудников МДР. Эта функция поможет принимать более обоснованные решения и повысит эффективность работы.

Не упустите возможность использовать новые инструменты для достижения лучших результатов! 

Если у вас возникнут вопросы или потребуется помощь, не стесняйтесь обращаться! 🙌

С уважением,  
Ваша команда разработки🚀"""

async def send_messages():
    """Массовая рассылка сообщения"""
    print("Start sending messages...")

    msg = get_message()

    ids = read_all_saved_chat_id()

    async with bot:
        for chat_id in ids:
            print(chat_id)
            await bot.send_message(
                chat_id = chat_id,
                text = msg,
                parse_mode = "Markdown"
            )

    print("Messages have sended")


if __name__ == "__main__":
    asyncio.run(send_messages())