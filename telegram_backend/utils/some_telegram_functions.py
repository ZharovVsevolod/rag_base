from .config import RANGE_LIMIT
from typing import List

def god_answer_split(
        answer_god: str, 
        limit: int = RANGE_LIMIT
) -> List[str]:
    """Разделить одно большое сообщение на массив из нескольких маленьких"""
    list_of_cut_answers = []

    n_i = (len(answer_god) // limit) + 1

    split_answers = answer_god.split("\n")
    splt_n_i = len(split_answers) // n_i + 1

    for i in range(1, n_i+1):
        if i == 1:
            msg = "\n".join(split_answers[:splt_n_i])
        else:
            if i != (n_i - 1):
                msg = "\n".join(split_answers[splt_n_i * (i - 1):splt_n_i * i])
            else:
                msg = "\n".join(split_answers[splt_n_i * i:])
        
        list_of_cut_answers.append(msg)
    
    return list_of_cut_answers