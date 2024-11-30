from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_huggingface.embeddings import HuggingFaceEmbeddings

from bairdotr.tools import FaissStoreHandler
from bairdotr.config import PATH_TO_VECTOR_STORE, EMBEDDINGS_NAME

from typing import Tuple, Literal

def get_all_in_one_rag(model_name: Literal["gemma2"] = "gemma2") -> Tuple[ChatOllama, FaissStoreHandler]:
    """Общая функция для того, чтобы сразу начать.\n
    Возвращает модель и vector_store для RAG-системы"""
    model = get_ollama_model(model_name)
    embeddings = get_emdeddings(EMBEDDINGS_NAME)

    vector_store = FaissStoreHandler(
        embeddings = embeddings,
        need_load = True,
        load_path = PATH_TO_VECTOR_STORE
    )
    return model, vector_store

def get_emdeddings(embeddings_name: str, inside_container: bool = True):
    embeddings = HuggingFaceEmbeddings(model_name = embeddings_name)
    # if inside_container:
    #     embeddings = OllamaEmbeddings(
    #         model = embeddings_name,
    #         base_url = "http://ollama-container:11434"
    #     )
    
    # else:
    #     embeddings = OllamaEmbeddings(
    #         model = embeddings_name
    #     )
    
    return embeddings

def get_ollama_model(
        model_name: Literal["gemma2"] = "gemma2",
        need_callback = []
    ) -> ChatOllama:
    llm = ChatOllama(
        model = model_name,
        base_url = "http://ollama-container:11434",
        callbacks = need_callback
    )

    return llm