"""Декораторы"""

import sys
import logging
import types
from functools import wraps

import logs.config_server_log
import logs.config_client_log
import traceback
import inspect

# метод определения модуля, источника запуска.
# Метод find () возвращает индекс первого вхождения искомой подстроки,
# если он найден в данной строке.
# Если его не найдено, - возвращает -1.
# if sys.argv[0].find('client') == -1:
#     # если не клиент то сервер!
#     LOGGER = logging.getLogger('server')
# else:
#     # ну, раз не сервер, то клиент
#     LOGGER = logging.getLogger('client')


def get_module_name(arg):
    start = arg.rfind('/')+1
    end = arg.rfind('.py')
    return arg[start:end]

LOGGER = logging.getLogger(get_module_name(sys.argv[0]))

def log_func(func_to_log):
    """Функция-декоратор для функций"""
    @wraps(func_to_log)
    def log_saver(*args, **kwargs):
        ret = func_to_log(*args, **kwargs)
        func_name = func_to_log.__name__ if hasattr(func_to_log, '__name__') else \
            func_to_log.name if hasattr(func_to_log, 'name') else ''
        LOGGER.debug(f'Была вызвана функция {func_name} c параметрами {args}, {kwargs}. '
                     f'Вызов из модуля {func_to_log.__module__}.'
                     f'Вызов из функции {traceback.format_stack()[0].strip().split()[-1]}.'
                     f'Вызов из функции {inspect.stack()[1][3]}')
        return ret
    return log_saver


def log_class(cls):
    """Функция-декоратор для Классов"""
    for name, method in cls.__dict__.items():
        if not name.startswith('_'):
            if isinstance(method, types.FunctionType) or not hasattr(method, '__func__'):
                setattr(cls, name, method_decorator(method))
            else:                                                                       # @staticmethod not callable
                setattr(cls, name, method_decorator(method.__func__, is_static=True))   # доступ с помощью __func__

    return cls


def method_decorator(func_to_log, is_static=False):
    @wraps(func_to_log)
    def wrapper(self, *args, **kwargs):
        func_name = func_to_log.__name__ if hasattr(func_to_log, '__name__') else \
            func_to_log.name if hasattr(func_to_log, 'name') else ''
        LOGGER.debug(f'Была вызвана функция {func_name} c параметрами {args}, {kwargs}. '
                     f'Вызов из модуля {func_to_log.__module__}.'
                     f'Вызов из функции {traceback.format_stack()[0].strip().split()[-1]}.'
                     f'Вызов из функции {inspect.stack()[1][3]}')
        return func_to_log(*args, **kwargs) if is_static else func_to_log(self, *args, **kwargs)
    return wrapper