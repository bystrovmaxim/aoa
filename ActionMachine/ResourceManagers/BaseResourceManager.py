# ActionMachine/BaseConnectionManager.py
from abc import ABC, abstractmethod
from typing import Any
from ..Core.Exceptions import ConnectionAlreadyOpenError, ConnectionNotOpenError

class BaseResourceManager(ABC):
    """
    Абстрактный менеджер ресурсов, таких как базы данных, файлы и сервисы
    Где необходимо держать соединение
    """