from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain_community.chat_message_histories.file import FileChatMessageHistory

from aurora.config import (
    DATA_FOLDER, 
    HISTORY_FILE_NAME, 
    CSV_TOKENS_NAME, 
    HOT_HISTORY, 
    TELEGRAM_CHAT_IDS, 
    TELEGRAM_CHAT_IDS_EYE,
    PATH_TO_NEW_HOT_HISTORY
)

import secrets
import pandas as pd
import time
import os
import re
from typing import Literal

def read_n_to_last_line(filename: str, n: int = 1) -> str:
    """Returns the nth before last line of a file (n=1 gives last line)"""
    num_newlines = 0
    with open(filename, 'rb') as f:
        try:
            f.seek(-2, os.SEEK_END)    
            while num_newlines < n:
                f.seek(-2, os.SEEK_CUR)
                if f.read(1) == b'\n':
                    num_newlines += 1
        except OSError:
            f.seek(0)
        last_line = f.readline().decode()
    return last_line

def decode_str(line: str, mode: Literal["to_file", "from_file"]) -> str:
    """Для записи в файл экранируем \\n, чтобы он записался нормально, при mode = to_file\n
    Так же убираем экранирование при mode = from_file"""
    match mode:
        case "from_file":
            line = re.sub(r"\\n", r"\n", line)

        case "to_file":
            line = re.sub(r"\n", r"\\n", line)

    return line

def write_to_cold_history(token: str, question: str, time_question: int, answer: str) -> None:
    """Запись в "холодную" историю сообщения пользователя и ответа модели"""
    filename = DATA_FOLDER + "/" + HISTORY_FILE_NAME

    question = decode_str(question, mode = "to_file")
    answer = decode_str(answer, mode = "to_file")

    time_answer = round(time.time())
    number = int(read_n_to_last_line(filename).split(";")[0])

    with open(filename, mode = "a+") as f:
        f.write(
            "\n" + str(number) + ";" + str(token) + ";" + str(time_question) + ";human;" + question + 
            "\n" + str(number + 1) + ";" + str(token) + ";" + str(time_answer) + ";ai;" + answer
        )

def raw_history_to_langchain_history(content: list[str]):
    """Перевод сырых данных из "горячей" истории в сообщения Langchain"""
    history = []

    for i in range(0, len(content), 2):
        try:
            msg_type = content[i]
            message = content[i + 1]
            message = decode_str(message, mode = "from_file")

            match msg_type:
                case "system":
                    history.append(SystemMessage(content = message))
                case "ai":
                    history.append(AIMessage(content = message))
                case "human":
                    history.append(HumanMessage(content = message))
        except:
            break
    
    return history

def get_path_to_hot_history(token: str) -> str:
    """Путь до хранения горячей истории"""
    return DATA_FOLDER + "/" + HOT_HISTORY + "/" + token + ".txt"

def read_hot_history(token: str):
    """Восстановление истории сообщений из "горячей" истории"""
    path = get_path_to_hot_history(token)
    if os.path.isfile(path):
        with open(path, "r") as file:
            content = file.readlines()
            content = [line[:-1] for line in content]
            history = raw_history_to_langchain_history(content)

            if history == []:
                return None
            else:
                return history
    else:
        return None

def write_hot_history(token: str, history: list) -> None:
    """Запись "ничисто" новой полной последней актуальной истории диалога с пользователем в "горячую" историю"""
    path = get_path_to_hot_history(token)

    with open(path, "w+") as file:
        for h in history:
            msg_type = h.type
            msg = h.content
            msg = decode_str(msg, mode = "to_file")

            file.writelines([msg_type, "\n", msg, "\n"])

def generate_hex() -> str:
    """Генерация нового токена"""
    return secrets.token_hex(16)

def make_token(user_id: str) -> str:
    """Создание токена и запись его в конец файла"""
    token = generate_hex()

    with open(DATA_FOLDER + "/" + CSV_TOKENS_NAME, mode = "a+") as f:
        f.write("\n" + user_id + ";" + token)

    return token

def read_data_token() -> pd.DataFrame:
    """Чтение БД токенов"""
    data = pd.read_csv(DATA_FOLDER + "/" + CSV_TOKENS_NAME, sep = ";", header = 0)
    data["id"] = data["id"].astype(str)
    data["token"] = data["token"].astype(str)
    return data

def check_token(token: str) -> bool:
    """Проверка наличия токена в БД"""
    data = read_data_token()
    true_token = False

    for user in data["token"]:
        if user == token:
            true_token = True
            break

    return true_token

def read_all_saved_chat_id() -> list:
    """Прочесть файл с сохранёнными chat_id и вернуть лист с ними"""
    filename = DATA_FOLDER + "/" + TELEGRAM_CHAT_IDS
    with open(filename) as file:
        ids = file.readlines()
    ids = [i[:-1] for i in ids] # убираем \n в конце

    return ids

def save_telegram_chat_ids(chat_id: str) -> bool:
    """Проверить, есть ли чат в базе, и занести его, если его там нет.\n
    Возвращает True, если он был в базе, и False, если нет"""
    filename = DATA_FOLDER + "/" + TELEGRAM_CHAT_IDS
    chat_id = str(chat_id)

    ids = read_all_saved_chat_id()

    if chat_id not in ids:
        with open(filename,"a+") as file:
            file.write(chat_id + "\n")
        return False

    return True

def check_eye(chat_id: str) -> bool:
    """Проверка, разрешено ли этому chat_id пользоваться функцией eye"""
    chat_id = str(chat_id)

    if save_telegram_chat_ids(chat_id):
        filename = DATA_FOLDER + "/" + TELEGRAM_CHAT_IDS_EYE

        with open(filename) as file:
            ids = file.readlines()
        ids = [i[:-1] for i in ids] # убираем \n в конце

        if chat_id in ids:
            return True

    return False

# -------------------------------
# Database v2 via langchain tools
# -------------------------------

def get_session_history_with_local_file(session_id) -> FileChatMessageHistory:
    fpath = PATH_TO_NEW_HOT_HISTORY + f"{session_id}.txt"
    return FileChatMessageHistory(file_path = fpath, encoding = "utf-8", ensure_ascii = False)
