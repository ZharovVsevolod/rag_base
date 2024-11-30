from telegram import Update
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    ContextTypes, 
    MessageHandler, 
    filters
)

from aurora.speech import audio2text, convert_audio_ffmpeg
from aurora.blanks import (
    get_standard_start_message,
    get_error_answer, 
    get_big_info, 
    get_eye_start_message,
    get_eye_block_message,
    get_eye_end_message,
    get_eye_wait_message
)
from aurora.database_management import save_telegram_chat_ids, check_eye
from aurora.god_api import (
    get_all_info, 
    god_answer_format,
    check_parser_folder,
    write_to_eye_database,
    read_from_eye_database,
    prepare_query
)

from utils.api_connection import get_answer, clear_history # type: ignore
from utils.config import AUDIO_SAVE_PATH, AUDIO_MP3_PATH, RANGE_LIMIT # type: ignore
from utils.some_telegram_functions import god_answer_split # type: ignore

import os
from dotenv import load_dotenv

import warnings
warnings.filterwarnings("ignore")

load_dotenv()

GOD_EYE: bool = False

async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Секретная функция /hello, и с тобой поздороваются по имени"""
    await update.message.reply_text(
        text = f"Привет, {update.effective_user.first_name}!",
        parse_mode = "Markdown"
    )

async def big_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Функция /info для отображения информации"""
    message = get_big_info()

    await update.message.reply_text(
        text = message,
        parse_mode = "Markdown"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Начальное обращение"""
    global GOD_EYE
    GOD_EYE = False

    chat_id = update.message.chat_id
    not_first_try = save_telegram_chat_ids(chat_id)

    if not_first_try:
        start_text = get_standard_start_message().content
        clear_history(
            session_id = chat_id
        )
    
    else:
        start_text = get_big_info()

    await update.message.reply_text(
        text = start_text,
        parse_mode = "Markdown"
    )

async def model_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Получить сообщение пользователя, получить ответ модели, обновить историю, отдать ответ модели в чат"""
    chat_id = update.message.chat_id
    save_telegram_chat_ids(chat_id)

    user_text = update.message.text
    user_voice = update.message.voice

    # В случае, если что-то пойдёт не так - сообщение об ошибке. В ином случае оно перезапишется
    answer = get_error_answer()

    try:
        global GOD_EYE
        if GOD_EYE:
            # Сообщение о том, что нужно немного подождать перед выводом информации
            await update.message.reply_text(text = get_eye_wait_message(), parse_mode = "Markdown")

            user_text = prepare_query(user_text)
            answer_god = god_answer(user_text)
            # Проверка, насколько длинный получился текст. 
            # Ибо он может быть больше, чем максимально возможный размер сообщения в телеге
            if len(answer_god) > RANGE_LIMIT:
                split_msg = god_answer_split(answer_god)

                for msg in split_msg:
                    await update.message.reply_text(text = msg)            
            
            else:
                await update.message.reply_text(text = answer_god)
            
            answer = get_eye_end_message()

        else:
            if user_voice is not None:
                new_file = await user_voice.get_file()
                await new_file.download_to_drive(AUDIO_SAVE_PATH)
                convert_audio_ffmpeg(path_file = AUDIO_SAVE_PATH, save_path = AUDIO_MP3_PATH)

                user_text = audio2text(AUDIO_MP3_PATH, delete_after = True)

                wait_message = f"Ваш вопрос: {user_text}\nСейчас подумаю над ним и отвечу!"
                await update.message.reply_text(
                    text = wait_message,
                    parse_mode = "Markdown"
                )
            
            answer = get_answer(
                user_question = user_text,
                session_id = chat_id,
                model_type = "gigachat"
            )

        try:
            await update.message.reply_text(
                text = answer,
                parse_mode = "Markdown"
            )
        except Exception as e:
            await update.message.reply_text(
                text = answer
            )
    
    except Exception as e:
        print("Error!")
        print(e)
        await update.message.reply_text(
            text = answer,
            parse_mode = "Markdown"
        )

async def eye(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Пробивка номера через Глаз Бога"""
    context.user_data["history"] = None

    chat_id = update.message.chat_id
    id_can_use = check_eye(chat_id)

    if id_can_use:
        start_text = get_eye_start_message()

        global GOD_EYE
        GOD_EYE = True

        await update.message.reply_text(
            text = start_text,
            parse_mode = "Markdown"
        )
    
    else:
        await update.message.reply_text(
            text = get_eye_block_message(),
            parse_mode = "Markdown"
        )

def god_answer(user_text) -> str:
    """Глаз Бога"""
    if check_parser_folder(user_text):
        answer_text = read_from_eye_database(user_text)
    
    else:
        answer_text = get_all_info(user_text)
        answer_text = god_answer_format(answer_text)
        write_to_eye_database(user_text, answer_text)

    global GOD_EYE
    GOD_EYE = False

    return answer_text

def main() -> None:
    """Основная функция"""
    app = ApplicationBuilder().token(os.environ["TELEGRAM_BOT_API"]).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("hello", hello))
    app.add_handler(CommandHandler("info", big_info))
    app.add_handler(CommandHandler("eye", eye))

    app.add_handler(MessageHandler(~filters.COMMAND, model_answer))
    
    print("The App has started and it is listening for your commands on Telegram")

    app.run_polling()

if __name__ == "__main__":
    main()