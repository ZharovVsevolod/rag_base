import os
import requests
import json
import re
from aurora.config import GOD_EYE_URL, DATA_FOLDER, EYE_PARSER_FOLDER

def is_phone_number(query):
    # Regular expression for validating international phone number formats
    pattern = r"^\+?\d{1,3}[\s\.-]?(\(?\d{1,5}\)?[\s\.-]?)?[\d\s\.-]{3,15}$"
    
    # Search the query for a phone number match
    if re.match(pattern, query):
        return True
    return False

def prepare_query(user_query: str) -> str:
    if is_phone_number(user_query):
        user_query = re.sub(r'[^0-9]', '', user_query)

        if user_query[0] == "7":
            user_query = "8" + user_query[1:]

        if len(user_query) == 10:
            user_query = "8" + user_query
    
    return user_query

def check_parser_folder(user_query: str) -> bool:
    """Проверка, был ли уже запрос с таким номером/почтой/номером машины etc"""
    path = DATA_FOLDER + "/" + EYE_PARSER_FOLDER + "/" + user_query + ".txt"
    return os.path.isfile(path)

def write_to_eye_database(user_query: str, eye_answer: str) -> None:
    """"Запись форматированного ответа от API в нашу базу, 
    чтобы кэшировать ответ и в следующий раз его не вызывать"""
    path = DATA_FOLDER + "/" + EYE_PARSER_FOLDER + "/" + user_query + ".txt"

    with open(path, "x") as file:
        file.write(eye_answer)

def read_from_eye_database(user_query: str) -> str:
    """Прочесть записанную информацию о личности"""
    path = DATA_FOLDER + "/" + EYE_PARSER_FOLDER + "/" + user_query + ".txt"
    with open(path, "r") as file:
        answer = file.read(None)

    return answer

def get_all_info(user_query: str):
    """Запрос по API к Глазу Бога и получение данных от него"""
    url = GOD_EYE_URL + str(user_query)

    client_id = os.environ["GOD_EYE_ID"]
    token = os.environ["GOD_EYE_TOKEN"]

    headers = {
        "Authorization": f"Bearer {token}",
        "X-ClientId": f"myClient-{client_id}"
    }

    response = requests.request("GET", url, headers=headers)

    return response.text

def one_or_multiple(answer_json, name):
    """Вспомогательная функция для форматирования ответа"""
    names = answer_json['items'][0][name]
    if len(names) == 0:
        return None
    
    if len(names) == 1:
        names = names[0]
    
    else:
        names = "\n- " + "\n- ".join(names)
    
    return names

def god_answer_format(eye_answer: str) -> str:
    """Форматирование ответа, полученного от API Глаза Бога. 
    Преобразовывает строку json-dict формата в читаемую строку.\n
    В случае, если информации не было предоставлено, то она в финальном ответе отображаться и не будет"""
    answer_json = json.loads(eye_answer)
    try:
        final_answer = f"Вот что мне удалось найти для {answer_json['query']}\n-----\n"

        temp_answer = one_or_multiple(answer_json, 'names')
        if temp_answer is not None:
            final_answer += f"Имена (никнеймы): {temp_answer}\n\n"
        
        temp_answer = one_or_multiple(answer_json, 'borns')
        if temp_answer is not None:
            final_answer += f"Дата рождения: {temp_answer}\n\n"
        
        temp_answer = one_or_multiple(answer_json, 'phones')
        if temp_answer is not None:
            final_answer += f"Абонентский номер: {temp_answer}\n\n"
        
        temp_answer = one_or_multiple(answer_json, 'phoneInfos')
        if temp_answer is not None:
            final_answer += f"Страна, регион, оператор сотовой связи: {temp_answer}\n\n"
        
        temp_answer = one_or_multiple(answer_json, 'emails')
        if temp_answer is not None:
            final_answer += f"Электронная почта: {temp_answer}\n\n"
        
        temp_answer = one_or_multiple(answer_json, 'adressess')
        if temp_answer is not None:
            final_answer += f"Адреса: {temp_answer}\n\n"
        
        temp_answer = one_or_multiple(answer_json, 'passwords')
        if temp_answer is not None:
            final_answer += f"Пароли: {one_or_multiple(answer_json, 'passwords')}\n\n"
        
        temp_answer = one_or_multiple(answer_json, 'snUrls')
        if temp_answer is not None:
            final_answer += f"Ссылки на страницы социальных сетей: {temp_answer}\n\n"
        
        temp_answer = one_or_multiple(answer_json, 'icQs')
        if temp_answer is not None:
            final_answer += f"Адреса ICQ: {temp_answer}\n\n"
        
        temp_answer = one_or_multiple(answer_json, 'skypes')
        if temp_answer is not None:
            final_answer += f"Адреса Skype: {temp_answer}\n\n"
        
        temp_answer = one_or_multiple(answer_json, 'telegrams')
        if temp_answer is not None:
            final_answer += f"Аккаунты в мессенджере Телеграм: {temp_answer}\n\n"
        
        temp_answer = one_or_multiple(answer_json, 'iPs')
        if temp_answer is not None:
            final_answer += f"IP адреса: {temp_answer}\n\n"
        
        temp_answer = one_or_multiple(answer_json, 'snScreenNames')
        if temp_answer is not None:
            final_answer += f"Никнеймы: {temp_answer}\n\n"
        
        temp_answer = one_or_multiple(answer_json, 'professionTypes')
        if temp_answer is not None:
            final_answer += f"Тип профессии: {temp_answer}\n\n"
        
        temp_answer = one_or_multiple(answer_json, 'professions')
        if temp_answer is not None:
            final_answer += f"Работа/профессия: {temp_answer}\n\n"
        
        temp_answer = one_or_multiple(answer_json, 'workAdresses')
        if temp_answer is not None:
            final_answer += f"Рабочий адрес: {temp_answer}\n\n"
        
        temp_answer = one_or_multiple(answer_json, 'passpCompiles')
        if temp_answer is not None:
            final_answer += f"Паспортные данные: {temp_answer}\n\n"
        
        temp_answer = one_or_multiple(answer_json, 'inns')
        if temp_answer is not None:
            final_answer += f"ИНН: {temp_answer}\n\n"
        
        temp_answer = one_or_multiple(answer_json, 'omses')
        if temp_answer is not None:
            final_answer += f"ОМС: {temp_answer}\n\n"
        
        temp_answer = one_or_multiple(answer_json, 'snilses')
        if temp_answer is not None:
            final_answer += f"СНИЛС: {temp_answer}\n\n"
        
        temp_answer = one_or_multiple(answer_json, 'carNs')
        if temp_answer is not None:
            final_answer += f"Гос. номер автомобиля: {temp_answer}\n\n"
        
        temp_answer = one_or_multiple(answer_json, 'carVins')
        if temp_answer is not None:
            final_answer += f"ВИН номер автомобля: {temp_answer}\n\n"
        
        temp_answer = one_or_multiple(answer_json, 'carModels')
        if temp_answer is not None:
            final_answer += f"Модель автомобиля: {temp_answer}\n\n"
        
        # Следующие два пункта были временно закомментированы, т.к. кидается много мусорной информации по парковкам автомобиля, 
        # базы данных которых часто оказывается слита, и в просто сообщениях в телеграме это всё смотрится ужасно. 
        # В будущем, когда у нас будет формироваться более адекватное форматирование ответа в телеграме 
        # или вообще условный html файл, то эту информацию можно будет включить в какое-нибудь примечание.
        # Но пока что - так

        # temp_answer = one_or_multiple(answer_json, 'carComments')
        # if temp_answer is not None:
        #     final_answer += f"Дополнительная информация по автомобилю: {temp_answer}\n\n"
        
        # temp_answer = one_or_multiple(answer_json, 'infoAddInfo')
        # if temp_answer is not None:
        #     final_answer += f"Дополнительная информация из базы по автомобилю: {temp_answer}\n\n"
        
        temp_answer = one_or_multiple(answer_json, 'infoStatuses')
        if temp_answer is not None:
            final_answer += f"Статус пользователя (для тех сайтов где он указывается): {temp_answer}\n\n"
        
        temp_answer = one_or_multiple(answer_json, 'infoApps')
        if temp_answer is not None:
            final_answer += f"Приложение пользователя через которое он получал доступ к сервису: {temp_answer}\n\n"
        
        temp_answer = one_or_multiple(answer_json, 'infoUserAgents')
        if temp_answer is not None:
            final_answer += f"Юзер агент браузера пользователя: {temp_answer}\n\n"
        
        temp_answer = one_or_multiple(answer_json, 'databaseInfo')
        if temp_answer is not None:
            final_answer += f"Информация о базе данных в которой была обнаружена информация: {temp_answer}\n\n"
    except:
        final_answer = eye_answer

    return final_answer