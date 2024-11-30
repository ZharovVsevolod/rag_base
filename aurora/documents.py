from langchain_text_splitters import CharacterTextSplitter, RecursiveCharacterTextSplitter
from langchain_text_splitters.base import TextSplitter
from langchain_core.documents import Document
import faiss
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings
from uuid import uuid4
from langchain_community.docstore.in_memory import InMemoryDocstore
from typing import List, Literal, Union
import re

from aurora.config import CHUNK_SIZE_FOR_RECURSIVE, CHUNK_OVERLAP

def get_standard_splitter() -> CharacterTextSplitter:
    """Возвращает стандартный CharacterTextSplitter (для подготовленных по структуре заранее документов) со следующими характеристиками:\n
    - separator = 'двойной перенос строки',
    - chunk_size = 100,
    - chunk_overlap = 0"""
    text_splitter = CharacterTextSplitter(
        separator = "\n\n",
        chunk_size = 100,
        chunk_overlap = 0,
        length_function=len,
        is_separator_regex=False
    )

    return text_splitter

def get_recursive_splitter() -> RecursiveCharacterTextSplitter:
    """Возвращает RecursiveCharacterTextSplitter (для неподготовленных по структуре заранее документов)"""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE_FOR_RECURSIVE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        is_separator_regex=False,
    )

    return text_splitter

def load_and_split_file(
        path_to_file: str, 
        source_name: str, 
        splitter_type: Union[None, Literal["standard", "recursive"], TextSplitter] = None,
        need_to_cut_out_questions: bool = False
) -> List[Document]:
    """Загрузить и поделить на чанки документ\n
    `path_to_file`: путь до файла, который необходимо загрузить и поделить на чанки

    `source_name`: Имя документа - для метаданных

    `splitter_type` : тип разделителя

           - "standard" - CharacterTextSplitter по двойному переносу строки 
        (для документов, заранее подготовленных и разделённых по тематическим блокам через двойной перенос строки)
           - "recursive" - RecursiveCharacterTextSplitter с chunk_size = 420
        (для документов, книг, не подготовленных заранее)
            - (`!`) также можно указать любой другой разделитель текста, наследуемый от TextSplitter (из библиотеки langchain_text_splitters)
    По умолчанию (значение None) - устанавливаться тип "recursive" 
    
    `need_to_cut_out_questions`: если из текста нужно автоматически вырезать блоки с вопросами (актуально для учебников) - установить в значние True.
    По умолчанию - False"""
    if splitter_type is None:
        splitter_type = "recursive"
    
    match splitter_type:
        case "recursive":
            splitter = get_recursive_splitter()
        
        case "standard":
            splitter = get_standard_splitter()
        
        case _:
            splitter = splitter_type

    with open(path_to_file, encoding="utf8") as f:
        document_original = f.read()
    
    if splitter_type != "standard":
        document_original = preprocess_re(document_original)

    document_split = splitter.create_documents(
        texts = [document_original],
        metadatas = [{"source": source_name}]
    )

    for doc in document_split:
        doc.metadata["id"] = str(uuid4())

    if need_to_cut_out_questions:
        document_split = [
            i for i in document_split if "?" not in i.page_content
        ]

    return document_split

def preprocess_re(text: str) -> str:
    """Очистка текста в документе от всякого мусора"""
    cleaned_text = re.sub(r"[^а-яёА-Я-Z0-9.,\n \-:!;?\[\]\(\)]", "", text)
    cleaned_text = re.sub(r"[`*~{}=<>##§]", " ", cleaned_text)
    cleaned_text = re.sub(r"\/\/\.\.", " ", cleaned_text)
    cleaned_text = re.sub(r"([а-я])-\s+([а-я])", r"\1\2", cleaned_text)
    cleaned_text = re.sub(r"\n", " ", cleaned_text)
    cleaned_text = re.sub(r"\s+ ", " ", cleaned_text)

    return cleaned_text


class FaissStoreHandler():
    """Вспомогательный класс для хранения и использования faiss vector store"""
    def __init__(
            self, 
            embeddings: Embeddings, 
            need_load: bool = False, 
            load_path: str = None
    ) -> None:
        if need_load and load_path is not None:
            self.vector_store_faiss = FAISS.load_local(
                folder_path = load_path,
                embeddings = embeddings,
                allow_dangerous_deserialization = True
            )
            print("Faiss vector store loaded")
        else:
            self.vector_store_faiss = FAISS(
                embedding_function = embeddings,
                index = faiss.IndexFlatL2(len(embeddings.embed_query("Генрих Герц"))),
                docstore = InMemoryDocstore(),
                index_to_docstore_id = {},
            )
            print("Blank faiss vector store created")
    
    def add_documents(self, split_documents: List[Document]) -> None:
        """Добавление документов, на входе должен быть уже разделённый на чанки документ"""
        uuids = [str(uuid4()) for _ in range(len(split_documents))]
        self.vector_store_faiss.add_documents(documents = split_documents, ids = uuids)
        print("Document added to faiss vector store")
    
    def similarity_search(self, query: str, k: int) -> List[Document]:
        """Поиск чанков, наиболее релевантных запросу. k - количество документов"""
        results = self.vector_store_faiss.similarity_search(
            query = query,
            k = k
        )
        return results
    
    def save(self, path: str) -> None:
        """Сохранение Faiss vector store по указанному пути"""
        self.vector_store_faiss.save_local(path)
        print(f"Faiss vector store saved in {path}")
    
    def add_and_save_raw_files(
            self,
            path_to_file: str,
            source_name: str, 
            splitter: Union[None, Literal["standard", "recursive"], TextSplitter] = None,
            need_to_cut_out_questions: bool = False,
            path_to_new_file: Union[None, Literal["same"], str] = None
    ) -> None:
        """Добавление файлов (с возможным последующим сохранением) в Faiss vector store"""
        docs = load_and_split_file(
            path_to_file = path_to_file,
            source_name = source_name,
            splitter_type = splitter,
            need_to_cut_out_questions = need_to_cut_out_questions
        )

        self.add_documents(docs)

        if path_to_new_file is not None:
            if path_to_new_file == "same":
                self.save(path_to_file)
            
            else:
                self.save(path_to_new_file)