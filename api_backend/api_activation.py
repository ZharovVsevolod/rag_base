import os
import time
import ast

import uvicorn

from fastapi import FastAPI, Header, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Annotated

import logging
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from typing import AsyncIterable
from fastapi.responses import StreamingResponse
from langchain.callbacks import AsyncIteratorCallbackHandler

from bairdotr.ollama_llm import get_all_in_one_rag, get_ollama_model

from bairdotr.llm_wrapper import(
    get_model_answer_rag, 
    clean_history, 
    cut_history,
    get_runnable_chain,
    make_config_for_chain
)
from bairdotr.tools import question_with_RAG
from bairdotr.database_management import(
    read_data_token,
    make_token,
    check_token,
    get_path_to_hot_history,
    read_hot_history,
    write_hot_history,
    write_to_cold_history,
    generate_hex,
    get_session_history_with_local_file
)

app = FastAPI()

#------------------------
# Для того, чтобы React мог связываться с FastApi, ему нужно открыть порты 
# через CORS. Подробнее тут: https://fastapi.tiangolo.com/tutorial/cors/#use-corsmiddleware
#------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# -----------------------

MODEL, VECTOR_STORE = get_all_in_one_rag()

class CommonHeaders(BaseModel):
    token: str

class ClearBody(BaseModel):
    session_id: str

class RequestBody(BaseModel):
    question: str
    session_id: str

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
def clear_history(headers: Annotated[CommonHeaders, Header()], body: ClearBody) -> dict:
    """Очистить историю и начать новый диалог"""
    token = headers.token
    # token = get_token(token)["token"]

    if check_token(token):
        path = get_path_to_hot_history(body.session_id)
        if os.path.isfile(path):
            os.remove(path)
        return {"response": 200, "status": "history cleaned"}

    else:
        return {"response": 401, "text": "Такого токена не существует. Попробуйте завести новый или обновить текущий"}

@app.post("/chat/completions")
def model_answer(headers: Annotated[CommonHeaders, Header()], body: RequestBody) -> dict:
    """Получение ответа от модели. История подгружается согласно токену"""
    token = headers.token
    # token = get_token(token)["token"]

    if check_token(token):
        time_question = int(time.time())

        session_id = body.session_id

        history = read_hot_history(session_id)

        answer, history = get_model_answer_rag(
            human_message = body.question,
            model = MODEL,
            vector_store = VECTOR_STORE,
            history = history
        )

        history = clean_history(history)
        history = cut_history(history)
        
        write_hot_history(session_id, history)
        write_to_cold_history(session_id, body.question, time_question, answer)

        return {"response": 200, "question": body.question, "answer": answer}

    else:
        return {"response": 401, "text": "Такого токена не существует. Попробуйте завести новый или обновить текущий"}

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
	exc_str = f'{exc}'.replace('\n', ' ').replace('   ', ' ')
	logging.error(f"{request}: {exc_str}")
	content = {'status_code': 10422, 'message': exc_str, 'data': None}
	return JSONResponse(content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

# -----------------------------
# Streaming
# -----------------------------

async def send_message(session_id: str, content: str) -> AsyncIterable[str]:
    callback = AsyncIteratorCallbackHandler()
    model = get_ollama_model(need_callback = [callback])

    runnable_with_history = get_runnable_chain(model)
    config = make_config_for_chain(session_id)

    message_with_rag_docs = question_with_RAG(
        question = content, 
        vector_store = VECTOR_STORE,
        model = model,
        history = get_session_history_with_local_file(session_id).messages
    )

    async for chunk in runnable_with_history.astream_events({'input': message_with_rag_docs}, version="v2", config=config):
            if chunk["event"] in ["on_parser_stream", "on_parser_end"]:
                if chunk["event"] == "on_parser_end":
                    yield "END_OF_STREAM"
                else:
                    yield chunk["data"]["chunk"]

@app.post("/stream_chat/")
async def stream_chat(message: RequestBody):
    generator = send_message(
        session_id = message.session_id, 
        content = message.question
    )
    return StreamingResponse(generator, media_type="text/plain")

@app.websocket("/ws/chat/")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    runnable_with_history = get_runnable_chain(MODEL)
    session_id = generate_hex()
    config = make_config_for_chain(session_id)

    while True:
        data = await websocket.receive_text()
        message = ast.literal_eval(data)["message"]

        print("Message", flush = True)
        print(message, flush = True)
        print(flush = True)

        # RAG system
        message_with_rag_docs = question_with_RAG(
            question = message, 
            vector_store = VECTOR_STORE,
            model = MODEL,
            history = get_session_history_with_local_file(session_id).messages
        )

        print("Rag", flush = True)
        print(message_with_rag_docs, flush = True)
        print(flush = True)

        async for chunk in runnable_with_history.astream_events({'input': message_with_rag_docs}, version="v2", config=config):
            if chunk["event"] in ["on_parser_start", "on_parser_stream"]:
                await websocket.send_json(chunk)

# -----------------------------
# -----------------------------
# -----------------------------


if __name__ == "__main__":
    uvicorn.run(app, host = "0.0.0.0", port = 1702)