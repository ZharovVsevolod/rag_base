import os
import requests
import subprocess

def convert_audio_ffmpeg(path_file: str, save_path: str, delete_after: bool = True) -> None:
    """Конвертация аудиосообщения с одного формата на другой"""
    subprocess.run(["ffmpeg", "-y", "-i", path_file, save_path])
    if delete_after:
        os.remove(path_file)

def add_question_to_answer(question: str, answer_text: str) -> str:
    """Добавляет вопрос пользователя в начале ответа, чтобы можно было удостовериться в правильной транскрибации сообщения"""
    return f"Вопрос: {question}\n\n{answer_text}"

def get_token() -> str:
    """Получить токен для Salute Speech"""
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"

    auth = os.environ["SALUTE_AUTH"]
    rquid = os.environ['SALUTE_SECRET']
    scope = os.environ["SALUTE_SCOPE"]

    headers = {
        "Authorization": f"Basic {auth}",
        "RqUID": f"{rquid}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "scope": scope
    }

    r = requests.post(
        url = url,
        data = data,
        headers = headers,
        verify = False
    )

    return r.json().get("access_token")

def audio2text(path_to_audio: str, delete_after: bool = True, debug: bool = False) -> str:
    """Перевод аудио в текст. В данный момент поддерживает только *.mp3 файлы"""
    url = "https://smartspeech.sber.ru/rest/v1/speech:recognize"

    token = get_token()

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "audio/mpeg"
    }

    with open(file = path_to_audio, mode = "rb") as f:
        data = f.read()

    r = requests.post(
        url = url,
        data = data,
        headers = headers,
        verify = False
    )

    if debug:
        print(r.text)
    
    if delete_after:
        os.remove(path_to_audio)

    return r.json().get("result")[0]