# ActionMachine/ResourceManagers/BaseResourceManager.py
from abc import ABC, abstractmethod
from typing import Optional, Type

class BaseResourceManager(ABC):
    """
    Маркерный класс для всех ресурсных менеджеров.
    Позволяет идентифицировать ресурс через isinstance.
    """

    @abstractmethod
    def get_wrapper_class(self) -> Optional[Type['BaseResourceManager']]:
        """
        Возвращает класс-обёртку (прокси) для данного ресурса.
        Если обёртка не требуется, возвращает None.
        """
        pass