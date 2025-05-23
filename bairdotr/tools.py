from langchain.schema import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.documents import Document

from bairdotr.documents import FaissStoreHandler
from bairdotr.config import (
    K_DOCUMENTS_FOR_RAG,
    ENABLE_EXTRA_STEPS,
    ENABLE_CONTEXT_PARAPHRASE,
    ENABLE_PARAPHRASE,
    ENABLE_STEPBACK,
    ENABNLE_HYDE,
    K_DOCUMENTS_FOR_EXTRA_STEPS
)
from bairdotr.blanks import (
    get_preprocess_message,
    get_hyde_message,
    get_prompt_with_context,
    get_paraphrase,
    get_general_question
)

import time
from collections import Counter
from typing import Union, List

def add_rag_docs_to_question(question: str, retriever_answer: list) -> str:
    """Добавление к промпту найденные RAGом документы"""
    answer = f"Вопрос пользователя: {question}\nОтрывок из документа, на который можно ориентироваться в случае, если в нём представлена релевантная вопросу пользователя информация (но ни в коем случае не упоминать о том, что документ был предоставлен):\nНАЧАЛО ДОКУМЕНТА\n"

    for i in range(K_DOCUMENTS_FOR_RAG):
        answer += retriever_answer[i].page_content
        answer += "\n"
    
    answer += "КОНЕЦ ДОКУМЕНТА\nНапоминаю, что **нельзя** упоминать, что тебе были предоставлены отрывки из документа"

    return answer

def merge_documents(retriever_answer: List[Document]) -> str:
    answer = "Отрывки из документов, найденные ретривером\n\n"

    for i in range(K_DOCUMENTS_FOR_RAG):
        answer += f"## Открывок {i + 1} из {retriever_answer[i].metadata["source"]}\n\n"
        answer += retriever_answer[i].page_content
        answer += "\n\n"
    
    return answer

def question_with_RAG(
        question: str, 
        vector_store: FaissStoreHandler, 
        model = None, 
        history = None,
        need_to_rag_docs_return: bool = False
) -> str:
    """Вызов RAG по вопросу пользователя"""
    if ENABLE_EXTRA_STEPS:
        extra_steps = MultipleCall(model, vector_store)
        retriever_answer = extra_steps.caller(question, history)
    
    else:
        retriever_answer = vector_store.similarity_search(question, k = K_DOCUMENTS_FOR_RAG)
    
    answer = add_rag_docs_to_question(question, retriever_answer)

    if need_to_rag_docs_return:
        docs = merge_documents(retriever_answer)
        return answer, docs
    
    return answer

#---------------------------------
#---------RAG extra steps---------
#---------------------------------

def get_top_unique_docs(doc_counts, initial_question_docs, top_n: int = 5):
    sorted_docs = sorted(
        doc_counts.items(),
        key = lambda x: (
            -x[1],
            x[0] not in initial_question_docs,
        ),  # Prioritize relevance in case of ties
    )

    # Extract the top-N document IDs
    top_documents = [doc for doc, _ in sorted_docs[:top_n]]

    return top_documents

def rearrange_docs(
        queries: List[str], 
        vector_store: FaissStoreHandler, 
        need_time_count: bool = False
) -> List[Document]:
    if need_time_count:
        time_start = time.time()
    
    initial_question = queries[0]
    extracted = []

    initial_retriever_answer = vector_store.similarity_search(
        initial_question, k=K_DOCUMENTS_FOR_EXTRA_STEPS
    )
    initial_ids = [doc.metadata["id"] for doc in initial_retriever_answer]

    extracted.extend(initial_retriever_answer)

    for question in queries[1:]:
        retriever_answer = vector_store.similarity_search(
            question, k=K_DOCUMENTS_FOR_EXTRA_STEPS
        )
        extracted.extend(retriever_answer)

    source_counts = Counter(doc.metadata["id"] for doc in extracted)

    top_docs_ids = get_top_unique_docs(source_counts, initial_ids)[:K_DOCUMENTS_FOR_RAG]

    final_result = []
    for i in extracted:
        if i.metadata["id"] in top_docs_ids:
            if i not in final_result:
                final_result.append(i)

    if need_time_count:
        time_finish = time.time()
        print(f"TIME FOR REARRANGEMENT: {time_finish - time_start}")
    
    return final_result

class MultipleCall:
    """Класс для реализации модификации вопроса пользователя для RAG-системы"""
    def __init__(self, model, vector_store: FaissStoreHandler) -> None:
        """Для работы модуля при инициации необходима модель для генерации и ретривер для получения документов"""
        self.model = model
        self.vectorstore = vector_store

    def hyde(self, query: str) -> dict:
        prompt = get_hyde_message()
        qa_no_context = prompt | self.model | StrOutputParser()
        hyde_chain = RunnablePassthrough.assign(hypothetical_document=qa_no_context)

        result = hyde_chain.invoke({"question": query})
        return result["hypothetical_document"]

    def generate_answer(
            self, 
            human_message: str, 
            system_m: SystemMessage, 
            history: list = None
    ) -> str:
        h_message = HumanMessage(content = human_message)

        if history is None:
            history = [system_m, h_message]
        else:
            history.append(h_message)
        
        answer = self.model.invoke(history)
        return answer.content

    def caller(
            self, 
            query: str, 
            history: Union[list, None] = None,
            need_time_count: bool = True
    ) -> List[Document]:
        """Создание модифицированных запросов для ретривера и возвращение чанков из базы знаний
        
        :params: - query: оригинальный вопрос пользователя\n
                 - history: история запросов к модели\n  
                 - need_time_count: debug-параметр, вывод времени, затраченного на модификацию вопроса

        :returns: Список чанков из базы знаний
        
        Настройка осуществляется через config:
        1) ENABLE_CONTEXT_PARAPHRASE: перефразирование вопроса пользователя с учётом контекста истории (если она есть)
        2) ENABLE_PARAPHRASE: перефразирование вопроса другими словами (на основе (1), если доступно)
        3) ENABNLE_HYDE: создание гипотетического отрыка, отвечающего на вопрос пользователя (на основе (1), если доступно)
        4) ENABLE_STEPBACK: генерация более общего вопроса на основе вопроса пользователя.
        """
        if need_time_count:
            time1_start = time.time()

        # Очистка от мусора
        query_itself = self.generate_answer(query, get_preprocess_message())

        # Генерация вопроса с учетом контекста (если он есть)
        if history and ENABLE_CONTEXT_PARAPHRASE:
            query_context = self.generate_answer(
                human_message = query_itself, 
                system_m = get_prompt_with_context(), 
                history=history
            )
        else:
            query_context = query_itself

        # Перефразирование другими словами
        if ENABLE_PARAPHRASE:
            query_paraphrase = self.generate_answer(
                human_message = query_context, 
                system_m = get_paraphrase()
            )

        # Гипотетический документ
        if ENABNLE_HYDE:
            query_hyde = self.hyde(query_context)

        # Общий вопрос по теме
        if ENABLE_STEPBACK:
            query_stepback = self.generate_answer(
                human_message = query_context, 
                system_m = get_general_question()
            )

        if need_time_count:
            time1_finish = time.time()
            print(f"QUESTION AUGMENTATIONS: {time1_finish-time1_start}")

        query_augments = [query_context, query_paraphrase, query_hyde, query_stepback]

        if need_time_count:
            print("Modified question:")
            for q in query_augments:
                print(q)
                print()

        final_k_docs = rearrange_docs(query_augments, self.vectorstore, need_time_count)

        return final_k_docs