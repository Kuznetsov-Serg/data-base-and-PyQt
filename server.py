"""Программа-сервер"""

import socket
import sys
import argparse
import json
import logging
import select
import time
import threading
import logs.config_server_log
from errors import IncorrectDataRecivedError
from common.variables import *
from common.utils import add_default_in_arg_parser, MessageHandle
from decos import log_class, log_func
from descrptrs import Port
from metaclasses import ServerMaker
from server_db_decl import ServerDB


"""Класс-сервер"""
@log_class
class Server(MessageHandle, metaclass=ServerMaker):
    port = Port()   # Дескриптор для контроля корректности

    def __init__(self, listen_address, listen_port, database):
        '''
        Параметры командной строки, если нет параметров, то задаём значения по умоланию.
        Сначала обрабатываем порт:
        server.py -p 8888 -a 127.0.0.1
        :return:
        '''
        # threading.Thread.__init__(self)
        # super(Server, self).__init__()
        # База данных сервера
        self.database = database

        # Инициализация логирования сервера.
        self.LOGGER = logging.getLogger('server')

        self.port = listen_port
        self.addr = listen_address

        # список клиентов и очередь сообщений на отправку
        self.clients = []
        self.messages = []
        # Словарь, содержащий имена пользователей и соответствующие им сокеты.
        self.names = {}

    def init_socket(self):
        self.LOGGER.info(
            f'Запущен сервер, порт для подключений: {self.port}, '
            f'адрес с которого принимаются подключения: {self.addr}. '
            f'Если адрес не указан, принимаются соединения с любых адресов.')
        # Готовим сокет
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        transport.bind((self.addr, self.port))
        transport.settimeout(0.5)

        # Начинаем слушать сокет.
        self.sock = transport
        self.sock.listen(MAX_CONNECTIONS)


    def start(self):
        """ Run server in listen mode """
        self.init_socket()

        # Основной цикл программы сервера
        while True:
            # Ждём подключения, если таймаут вышел, ловим исключение.
            try:
                client, client_address = self.sock.accept()
            except OSError:
                pass
            else:
                self.LOGGER.info(f'Установлено соедение с ПК {client_address}')
                self.clients.append(client)

            recv_data_lst = []
            send_data_lst = []
            err_lst = []

            # Проверяем на наличие ждущих клиентов
            try:
                if self.clients:
                    recv_data_lst, send_data_lst, err_lst = select.select(self.clients, self.clients, [], 0)
            except OSError:
                pass
    
            # принимаем сообщения и если там есть сообщения,
            # кладём в словарь, если ошибка, исключаем клиента.
            if recv_data_lst:
                for client_with_message in recv_data_lst:
                    try:
                        self.process_client_message(self.get_message(client_with_message), client_with_message)
                    except Exception:
                        # self.LOGGER.info(f'Клиент ??? отключился от сервера.')
                        self.LOGGER.info(f'Клиент {client_with_message.getpeername()} отключился от сервера.')
                        self.clients.remove(client_with_message)
    
            # Если есть сообщения для отправки и ожидающие клиенты, отправляем им сообщение.
            for message in self.messages:
                try:
                    self.process_message(message, send_data_lst)
                except Exception:
                    self.LOGGER.info(f'Связь с клиентом с именем {message[DESTINATION]} была потеряна')
                    self.clients.remove(self.names[message[DESTINATION]])
                    self.database.user_logout(self.names[message[ACCOUNT_NAME]])
                    del self.names[message[DESTINATION]]
            self.messages.clear()


    def process_client_message(self, message, client):
        """
        Обработчик сообщений от клиентов, принимает словарь - сообщение от клиента,
        проверяет корректность, отправляет словарь-ответ в случае необходимости.
        :param message:
        :param client:
        :return:
        """
        self.LOGGER.debug(f'Разбор сообщения от клиента : {message}')
        # Если это сообщение о присутствии, принимаем и отвечаем
        if ACTION in message and message[ACTION] == PRESENCE and \
                TIME in message and USER in message:
            # Если такой пользователь ещё не зарегистрирован,
            # регистрируем, иначе отправляем ответ и завершаем соединение.
            if message[USER][ACCOUNT_NAME] not in self.names.keys():
                self.names[message[USER][ACCOUNT_NAME]] = client
                client_ip, client_port = client.getpeername()
                self.database.user_login(message[USER][ACCOUNT_NAME], client_ip, client_port)
                self.send_message(client, RESPONSE_200)
            else:
                response = RESPONSE_400
                response[ERROR] = 'Имя пользователя уже занято.'
                self.send_message(client, response)
                self.clients.remove(client)
                client.close()
            return
        # Если это сообщение, то добавляем его в очередь сообщений.
        # Ответ не требуется.
        elif ACTION in message and message[ACTION] == MESSAGE and \
                DESTINATION in message and TIME in message \
                and SENDER in message and MESSAGE_TEXT in message:
            self.messages.append(message)
            return
        # Если клиент выходит
        elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in message:
            self.database.user_logout(message[ACCOUNT_NAME])
            self.clients.remove(self.names[message[ACCOUNT_NAME]])
            self.names[message[ACCOUNT_NAME]].close()
            del self.names[message[ACCOUNT_NAME]]
            return
        # Иначе отдаём Bad request
        else:
            response = RESPONSE_400
            response[ERROR] = 'Запрос некорректен.'
            self.send_message(client, response)
            return


    def process_message(self, message, listen_socks):
        """
        Функция адресной отправки сообщения определённому клиенту. Принимает словарь сообщение,
        и слушающие сокеты. Ничего не возвращает.
        :param message:
        :param listen_socks:
        :return:
        """
        if message[DESTINATION] in self.names and self.names[message[DESTINATION]] in listen_socks:
            self.send_message(self.names[message[DESTINATION]], message)
            self.LOGGER.info(f'Отправлено сообщение пользователю {message[DESTINATION]} '
                        f'от пользователя {message[SENDER]}.')
        elif message[DESTINATION] in self.names and self.names[message[DESTINATION]] not in listen_socks:
            raise ConnectionError
        else:
            self.LOGGER.error(
                f'Пользователь {message[DESTINATION]} не зарегистрирован на сервере, '
                f'отправка сообщения невозможна.')


    def close(self):
        self.sock.close()


    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def print_help():
    print('Поддерживаемые комманды:')
    print('users - список известных пользователей')
    print('connected - список подключённых пользователей')
    print('loghist - история входов пользователя')
    print('exit - завершение работы сервера.')
    print('help - вывод справки по поддерживаемым командам')



def main():
    # Загрузка параметров командной строки, если нет параметров, то задаём значения по умоланию
    params = add_default_in_arg_parser({'-p': DEFAULT_PORT, '-a': ''})

    # Инициализация базы данных
    database = ServerDB()

    # Создание экземпляра класса - сервера и его запуск:
    server = Server(params.a, params.p, database)
    thread = threading.Thread(target=server.start, daemon=True)
    thread.start()
    # так не работает
    # server.daemon = True
    # server.start()

    # Печатаем справку:
    print_help()

    # Основной цикл сервера:
    while True:
        command = input('Введите команду: ')
        if command == 'help':
            print_help()
        elif command == 'exit':
            break
        elif command == 'users':
            for user in sorted(database.users_list()):
                print(f'Пользователь {user[0]}, последний вход: {user[1]}')
        elif command == 'connected':
            for user in sorted(database.active_users_list()):
                print(f'Пользователь {user[0]}, подключен: {user[1]}:{user[2]}, время установки соединения: {user[3]}')
        elif command == 'loghist':
            name = input('Введите имя пользователя для просмотра истории. '
                         'Для вывода всей истории, просто нажмите Enter: ')
            for user in sorted(database.login_history(name)):
                print(f'Пользователь: {user[0]} время входа: {user[1]}. Вход с: {user[2]}:{user[3]}')
        else:
            print('Команда не распознана.')



if __name__ == '__main__':
    main()
