"""
Инициализация пакета модулей
"""

# Импортируем по одному, чтобы избежать циклических зависимостей
from .csv_reader import *
from .xml_generator import *
from .file_manager import *
from .logger_manager import *
from .csv_processor import *

__version__ = "1.0.0"
__author__ = "Your Name"