# src/action_machine/Core/DependencyFactory.py
"""
Dependency factory for actions.
Supports creating and caching dependencies.

Изменения (этап 0–1):
- Переименован метод get() → resolve().
- Удалены внешние ресурсы (_external_resources) и параметр machine из конструктора.
- Удалён метод run_action() (логика запуска дочерних действий перенесена в ToolsBox).
- Обновлены комментарии.
"""

from typing import Any


class DependencyFactory:
    """
    Dependency factory for actions.

    Creates and caches instances of dependencies declared via @depends.
    """

    def __init__(
        self,
        deps_info: list[dict[str, Any]],
    ) -> None:
        """
        Initializes the factory.

        Args:
            deps_info: list of dictionaries with dependency information (from @depends).
                       Each dictionary should have keys:
                       - 'class': the dependency class
                       - 'description': description string
                       - 'factory': optional callable to create the instance
        """
        self._deps: dict[type[Any], dict[str, Any]] = {info["class"]: info for info in deps_info}
        self._instances: dict[type[Any], Any] = {}

    def resolve(self, klass: type[Any]) -> Any:
        """
        Returns an instance of the dependency of the specified class.

        If the instance has already been created, it is returned from the cache.
        Otherwise, a new instance is created via a factory or the default constructor.

        Args:
            klass: dependency class.

        Returns:
            Dependency instance.

        Raises:
            ValueError: if the dependency is not declared via @depends.
        """
        if klass in self._instances:
            return self._instances[klass]
        if klass not in self._deps:
            raise ValueError(f"Dependency {klass.__name__} not declared in @depends")
        info = self._deps[klass]
        if info["factory"]:
            instance = info["factory"]()
        else:
            instance = klass()
        self._instances[klass] = instance
        return instance