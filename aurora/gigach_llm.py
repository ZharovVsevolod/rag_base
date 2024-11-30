import os

from langchain_community.chat_models.gigachat import GigaChat
from langchain_community.embeddings.gigachat import GigaChatEmbeddings

from aurora.tools import AllToolsHandler, get_standard_tools, give_to_model_tools
from aurora.documents import FaissStoreHandler
from aurora.config import PATH_TO_VECTOR_STORE

from typing import Tuple

def get_all_in_one_rag(need_streaming: bool = False) -> Tuple[GigaChat, FaissStoreHandler]:
    """Общая функция для того, чтобы сразу начать.\n
    Возвращает модель и vector_store для RAG-системы"""
    model, embeddings = get_all_models_gigachat(need_streaming)
    vector_store = FaissStoreHandler(
        embeddings = embeddings,
        need_load = True,
        load_path = PATH_TO_VECTOR_STORE
    )
    return model, vector_store

def get_all_in_one_tools(need_streaming: bool = False) -> Tuple[GigaChat, AllToolsHandler]:
    """Общая функция для того, чтобы сразу начать.\n
    Возвращает модель с установленными tools и вспомогательный ToolsHandler в случае"""
    model, embeddings = get_all_models_gigachat(need_streaming)

    store_handler = FaissStoreHandler(
        embeddings = embeddings,
        need_load = True,
        load_path = PATH_TO_VECTOR_STORE
    )

    tools = get_standard_tools(vector_store = store_handler)
    tools_handler = AllToolsHandler()

    for tool in tools:
        tools_handler.append_tool(tool)
    
    model_with_tools = give_to_model_tools(model = model, tools = tools_handler.get_tools_list())

    return model_with_tools, tools_handler


def get_gigachat(need_streaming: bool = False, need_callback: list = None) -> GigaChat:
    """Получить модель гигачата через API"""
    if need_streaming:
        callbacks = []
        if need_callback is not None:
            callbacks = need_callback
        
        chat = GigaChat(
            model = os.environ["GIGACHAT_MODEL"],
            credentials = os.environ["GIGACHAIN_AUTH"], 
            scope = os.environ["GIGACHAT_SCOPE"],
            verify_ssl_certs = False,
            profanity_check = False,
            streaming = True,
            callbacks = callbacks,
            base_url = "https://gigachat-preview.devices.sberbank.ru/api/v1/"
        )

    else:
        chat = GigaChat(
            model = os.environ["GIGACHAT_MODEL"],
            credentials = os.environ["GIGACHAIN_AUTH"], 
            scope = os.environ["GIGACHAT_SCOPE"],
            verify_ssl_certs = False,
            profanity_check = False,
            base_url = "https://gigachat-preview.devices.sberbank.ru/api/v1/"
        )
    return chat

def get_gigachat_embeddings() -> GigaChatEmbeddings:
    """Получить эмбеддинги гигачата через API"""
    gigachat_embeddings = GigaChatEmbeddings(
        credentials = os.environ["GIGACHAIN_AUTH"],
        scope = os.environ["GIGACHAT_SCOPE"],
        verify_ssl_certs = False
    )
    return gigachat_embeddings

def get_all_models_gigachat(need_streaming: bool = False) -> Tuple[GigaChat, GigaChatEmbeddings]:
    """Функция, которая возвращает инстансы модели, эмбеддингов гигачата, именно в таком порядке"""
    chat = get_gigachat(need_streaming)
    gigachat_embeddings = get_gigachat_embeddings()
    return chat, gigachat_embeddings
