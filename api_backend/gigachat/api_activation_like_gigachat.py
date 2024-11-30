import os
import time

import uvicorn

from fastapi import FastAPI, Header, Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Annotated, Dict, List

from aurora.gigach_llm import get_all_in_one_rag, get_all_in_one_tools
from aurora.llm_wrapper import get_model_answer_tools, get_model_answer_rag, clean_history, cut_history
from aurora.config import NEED_RAG_ALWAYS
from aurora.database_management import(
    read_data_token,
    make_token,
    check_token,
    get_path_to_hot_history,
    read_hot_history,
    write_hot_history,
    write_to_cold_history
)

app = FastAPI()

token_url = "/token"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl = token_url)

if NEED_RAG_ALWAYS:
    MODEL, VECTOR_STORE = get_all_in_one_rag()
else:
    MODEL, TOOLS_HANDLER = get_all_in_one_tools()

class CommonHeaders(BaseModel):
    token: str

class RequestBody(BaseModel):
    temperature: float
    top_p: float
    repetition_penalty: float
    model: str
    messages: List[Dict[str, str]]


@app.get("/")
def read_root():
    """Проверка связи"""
    return {"connection": "good"}

@app.get("/registry")
def get_token(user_id: str) -> dict:
    """Получение существующего токена или создание нового при отсутствии записи"""
    data = read_data_token()
    create_token = True
    token = None

    for user in data["id"]:
        if user == user_id:
            create_token = False
            token = data.loc[data["id"] == user_id]["token"].item()
            break
    
    if create_token:
        token = make_token(user_id)

    return {"response": 200, "token": token}

@app.post("/chat/clear")
def clear_history(headers: Annotated[CommonHeaders, Header()]) -> dict:
    """Очистить историю и начать новый диалог"""
    if check_token(headers.token):
        path = get_path_to_hot_history(headers.token)
        os.remove(path)
        return {"response": 200, "status": "history cleaned"}

    else:
        return {"response": 401, "text": "Такого токена не существует. Попробуйте завести новый или обновить текущий"}

@app.post("/chat/completions")
def model_answer(
    body: RequestBody,
    token: str = Depends(oauth2_scheme),
    X_Clent_ID = Header(None),
    X_Request_ID = Header(None),
    X_Session_ID = Header(None)
) -> dict:
    """Получение ответа от модели. История подгружается согласно токену"""
    user_token = get_token(X_Session_ID)["token"]
    question = body.messages[-1]["content"]

    if check_token(user_token):
        time_question = int(time.time())

        history = read_hot_history(user_token)

        if NEED_RAG_ALWAYS:
            answer, history = get_model_answer_rag(
                human_message = question,
                model = MODEL,
                vector_store = VECTOR_STORE,
                history = history
            )
        else:
            answer, history = get_model_answer_tools(
                human_message = question,
                model = MODEL,
                history = history,
                tools_handler = TOOLS_HANDLER
            )

        history = clean_history(history)
        history = cut_history(history)
        
        write_hot_history(user_token, history)
        write_to_cold_history(user_token, question, time_question, answer)

        final_response = {
            "choices": [
                {
                    "message": {
                        "content": answer,
                        "role": "assistant"
                    },
                    "index": 0,
                    "finish_reason": "stop"
                }
            ],
            "created": round(time.time()),
            "model": "GigaChat-Pro-Aurora:0.0.8",
            "object": "chat.completion"
        }

        return JSONResponse(content = final_response)

    else:
        return {"response": 401, "text": "Такого токена не существует. Попробуйте завести новый или обновить текущий"}

if __name__ == "__main__":
    uvicorn.run(app, host = "0.0.0.0", port = 1702)