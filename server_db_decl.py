from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

# Класс - серверная база данных (Декларативное объявление):
class ServerDB:
    Base = declarative_base()

    # Класс - отображение таблицы всех пользователей
    class AllUsers(Base):
        __tablename__ = 'all_users'
        id = Column(Integer, primary_key=True)
        name = Column(String, unique=True)
        last_login = Column(DateTime)

        def __init__(self, username):
            self.name = username
            self.last_login = datetime.datetime.now()

    # Класс - отображение таблицы активных пользователей:
    class ActiveUsers(Base):
        __tablename__ = 'active_users'
        id = Column(Integer, primary_key=True)
        user = Column(String, ForeignKey('all_users.id'), unique=True)
        ip = Column(String)
        port = Column(Integer)
        login_time = Column(DateTime)

        def __init__(self, user_id, ip, port, login_time):
            self.user = user_id
            self.ip = ip
            self.port = port
            self.login_time = login_time

    # Класс - отображение таблицы истории входов
    class LoginHistory(Base):
        __tablename__ = 'login_history'
        id = Column(Integer, primary_key=True)
        user = Column(String, ForeignKey('all_users.id'))
        ip = Column(String)
        port = Column(Integer)
        last_login = Column(DateTime)

        def __init__(self, user, ip, port, last_login):
            self.user = user
            self.ip = ip
            self.port = port
            self.last_login = last_login

    # Класс - отображение таблицы контактов пользователей
    class UsersContacts(Base):
        __tablename__ = 'contacts'
        id = Column(Integer, primary_key=True)
        user = Column(String, ForeignKey('all_users.id'))
        contact = Column(String, ForeignKey('all_users.id'))

        def __init__(self, user, contact):
            self.id = None
            self.user = user
            self.contact = contact

    # Класс отображение таблицы истории действий
    class UsersHistory(Base):
        __tablename__ = 'history'
        id = Column(Integer, primary_key=True)
        user = Column(String, ForeignKey('all_users.id'))
        sent = Column(Integer)
        accepted = Column(Integer)

        def __init__(self, user):
            self.id = None
            self.user = user
            self.sent = 0
            self.accepted = 0

    def __init__(self, path):
        # Создаём движок базы данных
        # path - server_base.db3
        # echo=False - отключает вывод на экран sql-запросов)
        # pool_recycle - по умолчанию соединение с БД через 8 часов простоя обрывается
        # Чтобы этого не случилось необходимо добавить pool_recycle=7200 (переустановка
        #    соединения через каждые 2 часа)
        # check_same_thread - защищает от ошибок обновления БД из разных потоков
        self.engine = create_engine(f'sqlite:///{path}', echo=False, pool_recycle=7200,
                                    connect_args={'check_same_thread': False})

        # Создаём таблицы
        self.Base.metadata.create_all(self.engine)
        # Создаём сессию
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        # Если в таблице активных пользователей есть записи, то их необходимо удалить
        # Когда устанавливаем соединение, очищаем таблицу активных пользователей
        self.session.query(self.ActiveUsers).delete()
        self.session.commit()

    # Функция выполняется при входе пользователя, фиксирует в базе сам факт входа
    def user_login(self, username, ip_address, port):
        # Запрос в таблицу пользователей на наличие там пользователя с таким именем
        rez = self.session.query(self.AllUsers).filter_by(name=username)
        # print(type(rez))
        # Если имя пользователя уже присутствует в таблице, обновляем время последнего входа
        if rez.count():
            user = rez.first()
            user.last_login = datetime.datetime.now()
        # Если нет, то создаём нового пользователя
        else:
            # Создаем экземпляр класса self.AllUsers, через который передаем данные в таблицу
            user = self.AllUsers(username)
            self.session.add(user)
            # Коммит здесь нужен, чтобы в db записался ID
            self.session.commit()

        # Теперь можно создать запись в таблицу активных пользователей о факте входа.
        # Создаем экземпляр класса self.ActiveUsers, через который передаем данные в таблицу
        new_active_user = self.ActiveUsers(user.id, ip_address, port, datetime.datetime.now())
        self.session.add(new_active_user)

        # и сохранить в историю входов
        # Создаем экземпляр класса self.LoginHistory, через который передаем данные в таблицу
        history = self.LoginHistory(user.id, ip_address, port, datetime.datetime.now())
        self.session.add(history)

        # Сохраняем изменения
        self.session.commit()

    # Функция фиксирует отключение пользователя
    def user_logout(self, username):
        # Запрашиваем пользователя, что покидает нас
        # получаем запись из таблицы AllUsers
        user = self.session.query(self.AllUsers).filter_by(name=username).first()

        # Удаляем его из таблицы активных пользователей.
        # Удаляем запись из таблицы ActiveUsers
        self.session.query(self.ActiveUsers).filter_by(user=user.id).delete()

        # Применяем изменения
        self.session.commit()

    # Функция фиксирует передачу сообщения и делает соответствующие отметки в БД
    def process_message(self, sender, recipient):
        # Получаем ID отправителя и получателя
        sender = self.session.query(self.AllUsers).filter_by(name=sender).first().id
        recipient = self.session.query(self.AllUsers).filter_by(name=recipient).first().id
        # Запрашиваем строки из истории и увеличиваем счётчики
        sender_row = self.session.query(self.UsersHistory).filter_by(user=sender).first()
        if sender_row == None:
            # Создаем экземпляр класса
            sender_row = self.UsersHistory(sender)
            self.session.add(sender_row)
        sender_row.sent += 1
        recipient_row = self.session.query(self.UsersHistory).filter_by(user=recipient).first()
        if recipient_row == None:
            # Создаем экземпляр класса
            recipient_row = self.UsersHistory(recipient)
            self.session.add(recipient_row)
        recipient_row.accepted += 1
        self.session.commit()

    # Функция добавляет контакт для пользователя.
    def add_contact(self, user, contact):
        # Получаем ID пользователей
        user = self.session.query(self.AllUsers).filter_by(name=user).first()
        contact = self.session.query(self.AllUsers).filter_by(name=contact).first()

        # Проверяем что не дубль и что контакт может существовать (полю пользователь мы доверяем)
        if not contact or self.session.query(self.UsersContacts).filter_by(user=user.id, contact=contact.id).count():
            return

        # Создаём объект и заносим его в базу
        contact_row = self.UsersContacts(user.id, contact.id)
        self.session.add(contact_row)
        self.session.commit()

    # Функция удаляет контакт из базы данных
    def remove_contact(self, user, contact):
        # Получаем ID пользователей
        user = self.session.query(self.AllUsers).filter_by(name=user).first()
        contact = self.session.query(self.AllUsers).filter_by(name=contact).first()

        # Проверяем что контакт может существовать (полю пользователь мы доверяем)
        if not contact:
            return

        # Удаляем требуемое
        print(self.session.query(self.UsersContacts).filter(
            self.UsersContacts.user == user.id,
            self.UsersContacts.contact == contact.id
        ).delete())
        self.session.commit()

    # Функция возвращает список известных пользователей со временем последнего входа.
    def users_list(self):
        query = self.session.query(
            self.AllUsers.name,
            self.AllUsers.last_login,
        )
        # Возвращаем список тюплов
        return query.all()

    # Функция возвращает список активных пользователей
    def active_users_list(self):
        # Запрашиваем соединение таблиц и собираем тюплы имя, адрес, порт, время.
        query = self.session.query(
            self.AllUsers.name,
            self.ActiveUsers.ip,
            self.ActiveUsers.port,
            self.ActiveUsers.login_time
        ).join(self.AllUsers)
        # Возвращаем список тюплов
        return query.all()

    # Функция возвращает историю входов по пользователю или по всем пользователям
    def login_history(self, username=None):
        # Запрашиваем историю входа
        query = self.session.query(self.AllUsers.name,
                                   self.LoginHistory.last_login,
                                   self.LoginHistory.ip,
                                   self.LoginHistory.port
                                   ).join(self.AllUsers)
        # Если было указано имя пользователя, то фильтруем по нему
        if username:
            query = query.filter(self.AllUsers.name == username)
        return query.all()


    # Функция возвращает список контактов пользователя.
    def get_contacts(self, username):
        # Запрашиваем указанного пользователя
        user = self.session.query(self.AllUsers).filter_by(name=username).one()

        # Запрашиваем его список контактов
        query = self.session.query(self.UsersContacts, self.AllUsers.name). \
            filter_by(user=user.id). \
            join(self.AllUsers, self.UsersContacts.contact == self.AllUsers.id)

        # выбираем только имена пользователей и возвращаем их.
        return [contact[1] for contact in query.all()]


    # Функция возвращает количество переданных и полученных сообщений
    def message_history(self):
        query = self.session.query(
            self.AllUsers.name,
            self.AllUsers.last_login,
            self.UsersHistory.sent,
            self.UsersHistory.accepted
        ).join(self.AllUsers)
        # Возвращаем список кортежей
        return query.all()


# Отладка
if __name__ == '__main__':
    db = ServerDB('server_base.db3')

    # Выполняем "подключение" пользователей
    db.user_login('client_1', '192.168.1.4', 8888)
    db.user_login('client_2', '192.168.1.5', 7777)

    # выводим список кортежей - активных пользователей
    print(' ---- active_users_list() ----')
    print(db.active_users_list())

    # выполянем 'отключение' пользователя
    db.user_logout('client_1')
    print(' ---- active_users_list() after logout client_1 ----')
    print(db.active_users_list())

    # Запрашиваем историю входов по пользователю
    print(' ---- login_history(client_1) ----')
    print(db.login_history('client_1'))

    db.user_logout('client_2')

    # и выводим список известных пользователей
    print(' ---- users_list() ----')
    print(db.users_list())

    # Запрашиваем историю сообщений
    db.process_message('client_1', 'client_2')
    print(' ---- message_history ----')
    print(db.message_history())


