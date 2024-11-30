# Длина контекста истории
N_HISTORY = 12

# Модель эмбеддингов
# EMBEDDINGS_NAME = "DiTy/bi-encoder-russian-msmarco"
EMBEDDINGS_NAME = "DeepPavlov/rubert-base-cased-sentence"

# RAG система
K_DOCUMENTS_FOR_RAG = 3
NEED_RAG_ALWAYS = True
PATH_TO_VECTOR_STORE = "data/dp_bert_faiss_index"
## RAG - дополнительные шаги модифицирования вопроса пользователя
ENABLE_EXTRA_STEPS = False # Мастер-рубильник доп. шагов
ENABLE_CONTEXT_PARAPHRASE = True
ENABLE_PARAPHRASE = True
ENABNLE_HYDE = True
ENABLE_STEPBACK = True
K_DOCUMENTS_FOR_EXTRA_STEPS = 5

# Переменные для web-интерфейса
RUN_NAME = "Bairdotr"
PATH_TO_NEW_HOT_HISTORY = "data/clients/new_hot_history/"

# Пути к базе данных по истории сообщений и пользователей
DATA_FOLDER = "data/clients"
CSV_TOKENS_NAME = "tokens.csv"
HISTORY_FILE_NAME = "history.csv"
HOT_HISTORY = "hot_history"
TELEGRAM_CHAT_IDS = "telegram_chat_ids.txt"

# Vector Store
PREPARED = "data/docs/cleaned_and_prepared"
JUST_CLEANED = "data/docs/just_cleaned"
CHUNK_SIZE_FOR_RECURSIVE = 600
CHUNK_OVERLAP = 80