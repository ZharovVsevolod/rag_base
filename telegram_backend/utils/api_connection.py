import requests
import json
import ast

from .config import (
    API_GIGACHAT_URL_GET_ANSWER, 
    TOKEN, API_GIGACHAT_URL_CLEAR, 
    API_GIGACHAT_URL_GET_TOKEN
)

from typing import Literal

def match_model_type(
        model_type: Literal["gigachat", "gemma2"],
        request_type: Literal["get_token", "get_answer", "clear_history"]
) -> str:
    """Функция для получения url из config в соответствии с типом модели и типом запроса"""
    match model_type:
        case "gigachat":
            match request_type:
                case "get_token":
                    url =  API_GIGACHAT_URL_GET_TOKEN
                case "get_answer":
                    url =  API_GIGACHAT_URL_GET_ANSWER
                case "clear_history":
                    url =  API_GIGACHAT_URL_CLEAR
        
        case "gemma2":
            print("There is no gemma 2 support yet")
            url = -1
    
    return url


def get_token(
        session_id: str,
        model_type: Literal["gigachat", "gemma2"] = "gigachat"
) -> str:
    """Получение токена по id"""
    url = match_model_type(model_type, request_type = "get_token")
    
    query = {"user_id": session_id}
    
    response = requests.request(
        method = "GET",
        url = url,
        params = query
    )
    
    message = ast.literal_eval(response.text)["token"]

    return message
    

def get_answer(
        user_question: str,
        session_id: str,
        model_type: Literal["gigachat", "gemma2"] = "gigachat"
) -> str:
    """Связь с API Aurora_Gigachat"""
    url = match_model_type(model_type, request_type = "get_answer")

    token = get_token(session_id = TOKEN, model_type = model_type)
    
    body = json.dumps({
        "question" : user_question,
        "session_id": f"{session_id}"
    })

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Token": f"{token}"
    }

    response = requests.request(
        method = "POST",
        url = url,
        headers = headers,
        data = body
    )

    message = ast.literal_eval(response.text)["answer"]

    return message


def clear_history(
        session_id: str,
        model_type: Literal["gigachat", "gemma2"] = "gigachat"
) -> bool:
    """Очистка истории сообщений при /start"""
    url = match_model_type(model_type, request_type = "clear_history")
    token = get_token(session_id = TOKEN, model_type = model_type)

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Token": f"{token}"
    }
    
    body = json.dumps({"session_id": f"{session_id}"})

    _ = requests.request(
        method = "POST",
        url = url,
        headers = headers,
        data = body
    )

    return True