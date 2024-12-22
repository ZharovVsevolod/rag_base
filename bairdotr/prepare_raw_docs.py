from langchain_unstructured import UnstructuredLoader
from collections import defaultdict
import re
import os

from typing import List
from langchain_core.documents.base import Document

from bairdotr.config import PREPARED, RAW_DOCS


def loader_choice(
        file_path: str,
        choice = "local",
        api = "spVH7W8Nwq4WSY0qICrABljuwZGqFm"
    ) -> UnstructuredLoader:
    """ Выбор использовать api, либо локальную загрузку.
    По умолчанию стоит local. В colab скорость local примерно в 5 раз меньше. Параметры:
        - file_path: путь до файла
        - choice: выбор загрузчика. "local" - локальный, "api" - через api, требует api)
        - api: api для unstructed_loader.
    """
    if(choice == "local"):
        loader = UnstructuredLoader(
        file_path=file_path,
        strategy="fast",)
    else:
        loader = UnstructuredLoader(
        file_path=file_path,
        strategy="hi_res",
        partition_via_api=True,
        coordinates=True,
        api_key=api)
    return loader


def delete_trash(docs: List[Document],inf_titul: bool) -> list[Document]:
    """Функция по удалению лишнего из документа.
    - inf_titul: True - удаляем титул, False - оставляем титул
    """

    # Проверка на то, если в документе информация о документе внизу страницы.
    # Если хотя бы на одной странице один шаблон совпадет, то мы будем удалять нижнюю часть каждой странице в документе
    inf_doc = False
    for doc in docs:
        if(re.search('стр. \d+ из \d+',doc.page_content)):
            inf_doc = True

    new_doc = []
    delete_page = []
    for doc in docs:
        delete = False

    # Удаление титульника, если нет условия inf_titul = False
    if((doc.metadata["page_number"]==1)and(not inf_titul)):
        delete = True

    # Удаление всего, что имеет категорию Image
    if(doc.metadata["category"]=="Image"):
        delete = True

    # Удаляем любой блок, который не содержит ни одной русской буквы
    match_rus = re.fullmatch('[^а-яА-ЯёЁ]+',doc.page_content)
    if match_rus:
        delete = True

    # Удаляем формы. Форма ищется через множественные _. Если они найдены, удаляем всю страницу
    # Если _ находится в нижней части документа, то это сноска, оставляем
    # Если _ находится в самой верхней части, то это примечение к документу, оставляем
    if((doc.metadata["coordinates"]["points"][1][1] < 1900)and(doc.metadata["coordinates"]["points"][1][1] > 400)):
        match_form = re.search('_{4,}',doc.page_content)
        if(match_form):
            delete_page.append(doc.metadata["page_number"])

    # Удаление нижней части каждой страницы документа, если информация о документе есть. Проверка inf_doc выше.
    if ((doc.metadata["coordinates"]["points"][1][1] > 2100)and(inf_doc)):
        delete = True

    # Если ни одним из средста, блок не был удален, сохраняем его
    if(not delete):
        new_doc.append(doc)

    # Удаление форм. Получаем только уникальные страницы на удаление
    delete_page = set(delete_page)

    # Удаляем всё на страницах, которые помечены, как формы.
    new_doc1 = []
    for doc in new_doc:
        if(doc.metadata["page_number"] not in delete_page):
            new_doc1.append(doc)
    return new_doc1


def div_into_butch(
        new_doc: List[Document],
        batch_size: int,
        split_in_batch: str,
        block_in_batch: int
    ) -> list[str]:
    """Объединение блоков в батчи. Параметры:
        - new_doc: получаемые блоки документа
        - batch_size: количество символов в блоке, после которого мы решаем, что это новый batch.
        - split_in_batch: как делим блоки в батче, пример " ".
        - block_in_batch: максимальное число блоков в батче. .
    """
    # Собираем блоки в батчи
    doc_dict = defaultdict(list)
    idx = 0
    for doc in new_doc:
        if((len(doc.page_content) < batch_size)and(len(doc_dict[idx]) < block_in_batch)):
            doc_dict[idx].append(doc.page_content)
        else:
            idx += 1
            doc_dict[idx].append(doc.page_content)

    # Собирвем batch в одну строку
    docs_fin = []
    for doc in doc_dict:
        docs_fin.append(split_in_batch.join(doc_dict[doc]))
    return docs_fin


def mirea_loader(
        download_path,
        final_path,
        choice_loader = "local",
        api = "spVH7W8Nwq4WSY0qICrABljuwZGqFm",
        inf_titul = True,
        batch_size = 300,
        split_in_batch = "\n",
        block_in_batch = 10,
    ) -> None:
    """Загрузчик. Параметры:
    - download_path - путь, где лежат необработанные документы
    - final_path - путь, куда грузить обработанные документы
    - choice_loader - выбор загрузчика. "api" или "local". По умолчанию local
    - api - api для unstracted_loader. По умолчанию стоит рабочий, но он дан на 2 недели.
    - inf_titul - есть ли в титуле важный текст. Если да, ставить inf_titul = False. 
    Такие документы стоит объединить и обрабоать отдельно от остальных

    - batch_size - количество символов в блоке, после которого мы решаем, что это новый batch. По умолчанию 300
    - split_in_batch - как делим блоки в батче. По умолчанию "\n"
    - block_in_batch - максимальное число блоков в батче. По умолчанию 10
    """
    # Просмотр папки с доками
    docs_paths = os.listdir(download_path)

    for document in docs_paths:
        path = os.path.join(download_path,document)

        # Выбор загрузчика
        loader = loader_choice(path,choice_loader,api)

        docs = []
        for doc in loader.lazy_load():
            docs.append(doc)

        new_docs = delete_trash(docs,inf_titul)
        fin_doc = div_into_butch(new_docs,batch_size,split_in_batch,block_in_batch)

        final_path_doc = final_path + "/" + document[:-3] + "txt"
        with open(final_path_doc, 'w') as f:
            for i in fin_doc:
                print(i+"\n\n", file=f)

        # Лог загрузки
        print("Документ " + document + " обработан")



if __name__ == "__main__":
    mirea_loader(
        download_path = RAW_DOCS,
        final_path = PREPARED
    )