from langchain.schema import HumanMessage
from aurora.tools import AllToolsHandler, question_with_RAG
from aurora.blanks import get_standard_start_message, get_stardard_system_message
from aurora.config import N_HISTORY, RUN_NAME
from aurora.documents import FaissStoreHandler
from typing import Tuple

from aurora.database_management import get_session_history_with_local_file
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.output_parsers import StrOutputParser

def get_model_answer_tools(
        human_message: str, 
        model, 
        history: list = None, 
        tools_handler: AllToolsHandler = None
    ) -> Tuple[str, list]:
    """Получить ответ модели\n
    Возвращает ответ модели и историю запросов"""
    h_message = HumanMessage(content = human_message)
    if history is None:
        s_message = get_stardard_system_message()
        start_message = get_standard_start_message()
        history = [s_message, start_message, h_message]
    else:
        history.append(h_message)
    
    answer = model.invoke(history)

    # Обработка, был ли вызов функции
    if tools_handler is not None and answer.content == "":
        tools = tools_handler.get_tools_dict()
        history.append(answer)
        
        for tool_call in answer.tool_calls:
            selected_tool = tools[tool_call["name"].lower()]
            tool_msg = selected_tool.invoke(tool_call)
            history.append(tool_msg)
        
        answer = model.invoke(history)
    
    history.append(answer)
    
    return answer.content, history

def get_model_answer_rag(
        human_message: str, 
        model, 
        vector_store: FaissStoreHandler,
        history: list = None
    ) -> Tuple[str, list]:
    """Получить ответ модели  с обязательным вызовом RAG\n
    Модель должна быть БЕЗ возможности вызывать tools\n
    Возвращает ответ модели и историю запросов"""
    q_rag = question_with_RAG(
        question = human_message, 
        vector_store = vector_store,
        model = model,
        history = history
    )

    h_message = HumanMessage(content = q_rag)
    if history is None:
        s_message = get_stardard_system_message()
        start_message = get_standard_start_message()
        history = [s_message, start_message, h_message]
    else:
        history.append(h_message)

    answer = model.invoke(history)
    
    history.append(answer)
    
    return answer.content, history

def clean_history(history: list) -> list:
    """Очистка от лишних вызовов для истории, остаётся только сообщения типа System, Human и ответы AI"""
    history_temp = []

    for single in history:
        signle_type = single.type
        if signle_type in ["system", "human"]:
            history_temp.append(single)
        if single.type == "ai" and single.content != "":
            history_temp.append(single)
        
    return history_temp

def cut_history(history: list) -> list:
    """Обрезка истории по количеству сообщений с сохранением системного промпта"""
    if len(history) > N_HISTORY:
            sys = history[:1]
            history_temp = history[-N_HISTORY:]
            history = sys + history_temp
    
    return history

# -------------------------
# Runnable with history. V2
# -------------------------

def get_runnable_chain(model):
    """Формат для вызова:\n
    - Если `есть` streaming:\n
    .. code-block:: python
        async for chunk in runnable_chain.astream_events(
            {'input': user_message}, version="v2", config=config
        ):
            if chunk["event"] in ["on_parser_start", "on_parser_stream"]:
                print(chunk)
    
    - Если `нет` streaming:
    .. code-block:: python
        runnable_chain.invoke({'input': user_message}, version="v2", config=config)

    config можно создать через функцию `make_config_for_chain`
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", get_stardard_system_message().content),
        ("placeholder", "{history}"),
        ("user", "{input}")
    ])

    str_parser = StrOutputParser()
    chain = prompt | model | str_parser.with_config({"run_name": RUN_NAME})

    runnable_with_history = RunnableWithMessageHistory(
        chain,
        get_session_history_with_local_file,
        input_messages_key="input",
        history_messages_key="history"
    )

    return runnable_with_history

def make_config_for_chain(session_id: str) -> dict:
    """Создание config для runnable_chain"""
    return {"configurable": {"session_id": session_id}}