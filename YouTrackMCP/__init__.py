# YouTrackMCP/__init__.py
"""
Пакет YouTrackMCP – реализация действий для YouTrack.
"""
from .YouTrackMCPServer import YouTrackMCPServer

# Для обратной совместимости оставляем алиас YouTrackMCP
YouTrackMCP = YouTrackMCPServer