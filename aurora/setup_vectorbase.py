from aurora.documents import FaissStoreHandler
from aurora.gigach_llm import get_gigachat_embeddings
from aurora.config import PREPARED, JUST_CLEANED, PATH_TO_VECTOR_STORE

import os
from dotenv import load_dotenv

def main():
    print("Start to prepare vector store and new documents...")
    path_to_prepared_docs = PREPARED + "/"
    path_to_just_cleaned_docs = JUST_CLEANED + "/"

    prepared_docs = [doc.name for doc in os.scandir(path_to_prepared_docs)]
    just_cleaned_docs = [doc.name for doc in os.scandir(path_to_just_cleaned_docs)]

    print("Names of files that will be integrated in vector store with Character Splitter:")
    print(prepared_docs)
    print()
    print("Names of files that will be integrated in vector store with Recursive Splitter")
    print(just_cleaned_docs)
    print()

    print("Creating new blank vector store")
    vector_store = FaissStoreHandler(get_gigachat_embeddings())

    print("Adding cleaned and prepared docs...")
    for doc in prepared_docs:
        print(doc)
        doc_path = path_to_prepared_docs + doc
        vector_store.add_and_save_raw_files(
            path_to_file = doc_path,
            source_name = doc,
            splitter = "standard"
        )
        print()
    
    print("Addding just cleaned docs...")
    for doc in just_cleaned_docs:
        print(doc)
        doc_path = path_to_just_cleaned_docs + doc
        vector_store.add_and_save_raw_files(
            path_to_file = doc_path,
            source_name = doc,
            splitter = "recursive"
        )
        print()
    
    print("Saving...")
    vector_store.save(PATH_TO_VECTOR_STORE)

    print("New vector store build completed.")
    print(f"There is {len(prepared_docs) + len(just_cleaned_docs)} new documents")
    print(f"Path to actual vector store: {PATH_TO_VECTOR_STORE}")


if __name__ == "__main__":
    load_dotenv()
    main()