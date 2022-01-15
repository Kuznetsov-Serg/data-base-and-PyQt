import sys
from PyQt5.QtWidgets import QApplication

from common.variables import *
from common.errors import ServerError
from common.decos import log_class, log_func
from common.utils import add_default_in_arg_parser
from client.database import ClientDatabase
from client.transport import ClientTransport
from client.main_window import ClientMainWindow
from client.start_dialog import UserNameDialog


# Инициализация клиентского логера
logger = logging.getLogger('client')


# Основная функция клиента
if __name__ == '__main__':
    # Загрузка параметров командной строки, если нет параметров, то задаём значения по умоланию
    params = add_default_in_arg_parser({'addr': DEFAULT_IP_ADDRESS, 'port': DEFAULT_PORT, '--name': None})
    server_address = params.addr
    server_port = params.port
    client_name = params.name

    # Создаём клиентокое приложение
    client_app = QApplication(sys.argv)

    # Если имя пользователя не было указано в командной строке то запросим его
    if not client_name:
        start_dialog = UserNameDialog()
        client_app.exec_()
        # Если пользователь ввёл имя и нажал ОК, то сохраняем ведённое и удаляем объект, инааче выходим
        if start_dialog.ok_pressed:
            client_name = start_dialog.client_name.text()
            del start_dialog
        else:
            exit(0)

    # Записываем логи
    logger.info(
        f'Запущен клиент с парамертами: адрес сервера: {server_address} , порт: {server_port}, имя пользователя: {client_name}')

    # Создаём объект базы данных
    database = ClientDatabase(client_name)

    # Создаём объект - транспорт и запускаем транспортный поток
    try:
        transport = ClientTransport(server_port, server_address, database, client_name)
    except ServerError as error:
        print(error.text)
        exit(1)
    transport.setDaemon(True)
    transport.start()

    # Создаём GUI
    main_window = ClientMainWindow(database, transport)
    main_window.make_connection(transport)
    main_window.setWindowTitle(f'Чат Программа alpha release - {client_name}')
    client_app.exec_()

    # Раз графическая оболочка закрылась, закрываем транспорт
    transport.transport_shutdown()
    transport.join()