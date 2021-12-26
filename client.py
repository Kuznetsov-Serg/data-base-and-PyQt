import sys
import json
import socket
import threading
import time
import logging
# import logs.config_client_log
# from errors import ReqFieldMissingError
from common.variables import DEFAULT_PORT, DEFAULT_IP_ADDRESS, ACTION, \
    TIME, USER, ACCOUNT_NAME, SENDER, PRESENCE, RESPONSE, \
    ERROR, MESSAGE, MESSAGE_TEXT, DESTINATION, EXIT
from common.utils import add_default_in_arg_parser, MessageHandle
from errors import IncorrectDataRecivedError, ReqFieldMissingError, ServerError
from decos import log_class, log_func
from descrptrs import Port
from metaclasses import ClientMaker


"""Класс-клиент"""
@log_class
class Client(MessageHandle, metaclass=ClientMaker):
    my_username: ''
    server_port = Port()   # Дескриптор для контроля корректности

    def __init__(self, server_address=DEFAULT_IP_ADDRESS, server_port=DEFAULT_PORT, client_name=None):

        # Инициализация клиентского логера
        self.LOGGER = logging.getLogger('client')

        """Сообщаем о запуске"""
        print(f'Консольный месседжер. Клиентский модуль. Имя пользователя: {client_name}')

        # Если имя пользователя не было задано, необходимо запросить пользователя.
        if not client_name:
            client_name = input('Введите имя пользователя: ')

        self.server_address = server_address
        self.server_port = server_port      # проверим подходящий номер порта
        self.client_name = client_name
        self.LOGGER.info(f'Запущен клиент "{client_name}" с парамертами: '
                         f'адрес сервера: {server_address} , порт: {server_port}')


    def start(self):
        """ Run client """
        # Инициализация сокета и сообщение серверу о нашем появлении
        try:
            self.transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.transport.connect((self.server_address, self.server_port))
            self.send_message(self.transport, self.create_presence())
            answer = self.process_response_ans(self.get_message(self.transport))
            self.LOGGER.info(f'Установлено соединение с сервером. Ответ сервера: {answer}')
            print(f'Установлено соединение с сервером. Ответ сервера: {answer}')
        except json.JSONDecodeError:
            self.LOGGER.error('Не удалось декодировать полученную Json строку.')
            sys.exit(1)
        except ServerError as error:
            self.LOGGER.error(f'При установке соединения сервер вернул ошибку: {error.text}')
            sys.exit(1)
        except ReqFieldMissingError as missing_error:
            self.LOGGER.error(f'В ответе сервера отсутствует необходимое поле {missing_error.missing_field}')
            sys.exit(1)
        except (ConnectionRefusedError, ConnectionError):
            self.LOGGER.critical(
                f'Не удалось подключиться к серверу {self.server_address}:{self.server_port}, '
                f'конечный компьютер отверг запрос на подключение.')
            sys.exit(1)
        else:
            # Если соединение с сервером установлено корректно,
            # запускаем клиенский процесс приёма сообщний
            receiver = threading.Thread(target=self.message_from_server)
            receiver.daemon = True
            receiver.start()

            # затем запускаем отправку сообщений и взаимодействие с пользователем.
            user_interface = threading.Thread(target=self.user_interactive)
            user_interface.daemon = True
            user_interface.start()
            self.LOGGER.debug('Запущены процессы')

            # Watchdog основной цикл, если один из потоков завершён,
            # то значит или потеряно соединение или пользователь
            # ввёл exit. Поскольку все события обработываются в потоках,
            # достаточно просто завершить цикл.
            while True:
                time.sleep(1)
                if receiver.is_alive() and user_interface.is_alive():
                    continue
                break


    def message_from_server(self):
        """Функция - обработчик сообщений других пользователей, поступающих с сервера"""
        while True:
            try:
                message = self.get_message(self.transport)
                if ACTION in message and message[ACTION] == MESSAGE and \
                        SENDER in message and DESTINATION in message \
                        and MESSAGE_TEXT in message and message[DESTINATION] == self.client_name:
                    print(f'\nПолучено сообщение от пользователя {message[SENDER]}:'
                          f'\n{message[MESSAGE_TEXT]}')
                    self.LOGGER.info(f'Получено сообщение от пользователя {message[SENDER]}:'
                                f'\n{message[MESSAGE_TEXT]}')
                else:
                    self.LOGGER.error(f'Получено некорректное сообщение с сервера: {message}')
            except IncorrectDataRecivedError:
                self.LOGGER.error(f'Не удалось декодировать полученное сообщение.')
            except (OSError, ConnectionError, ConnectionAbortedError,
                    ConnectionResetError, json.JSONDecodeError):
                self.LOGGER.critical(f'Потеряно соединение с сервером.')
                break


    def create_message(self):
        """
        Функция запрашивает кому отправить сообщение и само сообщение,
        и отправляет полученные данные на сервер
        :param sock:
        :return:
        """
        to_user = input('Введите получателя сообщения: ')
        message = input('Введите сообщение для отправки: ')
        message_dict = {
            ACTION: MESSAGE,
            SENDER: self.client_name,
            DESTINATION: to_user,
            TIME: time.time(),
            MESSAGE_TEXT: message
        }
        self.LOGGER.debug(f'Сформирован словарь сообщения: {message_dict}')
        try:
            self.send_message(self.transport, message_dict)
            self.LOGGER.info(f'Отправлено сообщение для пользователя {to_user}')
        except:
            self.LOGGER.critical('Потеряно соединение с сервером.')
            sys.exit(1)


    def user_interactive(self):
        """Функция взаимодействия с пользователем, запрашивает команды, отправляет сообщения"""
        self.print_help()
        while True:
            command = input('Введите команду: ')
            if command == 'message':
                self.create_message()
            elif command == 'help':
                self.print_help()
            elif command == 'exit':
                self.send_message(self.transport, self.create_exit_message())
                print('Завершение соединения.')
                self.LOGGER.info('Завершение работы по команде пользователя.')
                # Задержка неоходима, чтобы успело уйти сообщение о выходе
                time.sleep(0.5)
                break
            else:
                print('Команда не распознана, попробойте снова. help - вывести поддерживаемые команды.')


    def create_presence(self):
        """
        Функция генерирует запрос о присутствии клиента
        :param account_name:
        :return:
        """
        out = {
            ACTION: PRESENCE,
            TIME: time.time(),
            USER: {
                ACCOUNT_NAME: self.client_name
            }
        }
        self.LOGGER.debug(f'Сформировано {PRESENCE} сообщение для пользователя {self.client_name}')
        return out


    @staticmethod
    def print_help():
        """Функция выводящяя справку по использованию"""
        print('Поддерживаемые команды:')
        print('message - отправить сообщение. Кому и текст будет запрошены отдельно.')
        print('help - вывести подсказки по командам')
        print('exit - выход из программы')


    def process_response_ans(self, message):
        """
        Функция разбирает ответ сервера на сообщение о присутствии,
        возращает 200 если все ОК или генерирует исключение при ошибке
        :param message:
        :return:
        """
        self.LOGGER.debug(f'Разбор приветственного сообщения от сервера: {message}')
        if RESPONSE in message:
            if message[RESPONSE] == 200:
                return '200 : OK'
            elif message[RESPONSE] == 400:
                raise ServerError(f'400 : {message[ERROR]}')
        raise ReqFieldMissingError(RESPONSE)


    def close(self):
        self.transport.close()


    def create_exit_message(self):
        """Функция создаёт словарь с сообщением о выходе"""
        return {
            ACTION: EXIT,
            TIME: time.time(),
            ACCOUNT_NAME: self.client_name
        }


    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def main():
    # Загрузка параметров командной строки, если нет параметров, то задаём значения по умоланию
    params = add_default_in_arg_parser({'addr': DEFAULT_IP_ADDRESS, 'port': DEFAULT_PORT, '--name': None})
    Client(params.addr, params.port, params.name).start()


if __name__ == '__main__':
    main()
