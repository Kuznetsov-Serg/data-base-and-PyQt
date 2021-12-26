"""Утилиты"""

import argparse
import sys
import json

sys.path.append('../')
from common.variables import MAX_PACKAGE_LENGTH, ENCODING
from errors import IncorrectDataRecivedError, NonDictInputError
from decos import log_class, log_func



@log_func
def add_default_in_arg_parser(default_dict={}):
    """
    Парсер аргументов коммандной строки
    :param default_dict: дополняет строку параметрами по умолчанию из передаваемого словаря
    :return:
    """
    parser = argparse.ArgumentParser()
    for key, value in default_dict.items():
        if isinstance(value, int):
            parser.add_argument(key, default=value, type=int, nargs='?')
        else:
            parser.add_argument(key, default=value, nargs='?')
    # parser.add_argument('-p', default=7777, type=int, nargs='?')
    # parser.add_argument('-a', default='', nargs='?')
    return parser.parse_args(sys.argv[1:])


# @log_class
class MessageHandle:
    @staticmethod
    def get_message(client):
        '''
        Утилита приёма и декодирования сообщения
        принимает байты выдаёт словарь, если принято что-то другое, отдаёт ошибку значения
        :param client:
        :return:
        '''
        encoded_response = client.recv(MAX_PACKAGE_LENGTH)
        if isinstance(encoded_response, bytes):
            json_response = encoded_response.decode(ENCODING)
            response = json.loads(json_response)
            if isinstance(response, dict):
                return response
            raise IncorrectDataRecivedError
        raise IncorrectDataRecivedError


    @staticmethod
    def send_message(sock, message):
        '''
        Утилита кодирования и отправки сообщения
        принимает словарь и отправляет его
        :param sock:
        :param message:
        :return:
        '''
        if not isinstance(message, dict):
            raise NonDictInputError
        js_message = json.dumps(message)
        encoded_message = js_message.encode(ENCODING)
        sock.send(encoded_message)
