"""
Модуль обработки CSV файлов и генерации XML.
Универсальный — работает с любыми required_fields из конфига.
Не зависит от семантики (department, shiftrole и т.д.).
"""

import logging
from typing import List, Dict, Callable
from pathlib import Path

# Импортируем необходимые модули
from .csv_reader import read_encoding, iter_csv_rows, gen_uid
from .xml_generator import create_access_generator, format_xml_pretty
from .config_manager import get_config_value


class CSVProcessor:
    """
    Универсальный процессор CSV файлов.
    Интерпретирует данные на основе конфигурации, без привязки к именам полей.
    """

    def __init__(self):
        """Инициализация процессора на основе конфигурации."""
        self.required_fields = get_config_value(
            'csv_processing.required_fields', [])
        self.model_version = get_config_value(
            'csv_processing.model_version', '1.0.0')
        self.model_name = get_config_value(
            'csv_processing.model_name', 'Access')

    def process_csv_file_stream(
        self,
        folder_uid: str,
        csv_file_path: str,
        xml_file_path: str,
        logger: logging.Logger,
        allow_headdep_recursive: bool = True  # для совместимости, не используется
    ) -> bool:
        """
        Потоковая обработка CSV-файла с генерацией XML.
        Каждая строка → одна XML-структура.

        Args:
            folder_uid: UID папки для ролей
            csv_file_path: путь к входному CSV-файлу
            xml_file_path: путь к выходному XML-файлу
            logger: логгер для записи событий
            allow_headdep_recursive: флаг для совместимости (не используется)

        Returns:
            bool: True если обработка успешна, иначе False
        """
        logger.info(f"Старт обработки файла {csv_file_path} → {xml_file_path}")

        try:
            encoding = read_encoding(csv_file_path)
            logger.debug(f"Определена кодировка: {encoding}")
        except Exception as e:
            logger.error(
                f"Ошибка определения кодировки файла {csv_file_path}: {e}")
            return False

        # Создаем генератор XML
        xml_generator = create_access_generator()

        def generate_content(xf):
            """Генератор контента для XML файла."""
            roles_added = 0
            logger.debug("Добавление FullModel в XML")
            xml_generator.add_full_model(
                xf, self.model_version, self.model_name)

            # Обрабатываем каждую строку
            for line_num, row in iter_csv_rows(csv_file_path, encoding, self.required_fields, logger):
                # Передаём всю строку как есть — генератор сам найдёт нужные поля
                logger.info(
                    f"Строка {line_num}: Обработка записи с полями: {list(row.keys())}")

                # Генерируем структуру
                xml_generator.add_role_structure(
                    xf,
                    data=row,
                    folder_uid=folder_uid,
                    logger=logger
                )
                roles_added += 1

            logger.info(f"Всего добавлено ролей: {roles_added}")

        try:
            logger.debug("Начало генерации XML")
            xml_generator.generate_xml(xml_file_path, generate_content)
            logger.debug("Форматирование XML с отступами")
            format_xml_pretty(xml_file_path)
            logger.info(f"XML успешно сохранён: {xml_file_path}")
            return True
        except Exception as e:
            logger.error(f"Ошибка генерации XML-файла {xml_file_path}: {e}")
            return False


class BatchProcessor:
    """
    Класс для пакетной обработки CSV файлов.
    """

    def __init__(self):
        """Инициализация пакетного процессора."""
        self.csv_processor = CSVProcessor()

    def process_file_list(
        self,
        folder_uid: str,
        csv_dir: str,
        file_list: List[str],
        logger_factory: Callable[[str], logging.Logger],
        allow_headdep_recursive: bool = True
    ) -> Dict[str, bool]:
        """
        Обрабатывает список CSV файлов.

        Args:
            folder_uid: UID папки для ролей
            csv_dir: директория с CSV файлами
            file_list: список файлов для обработки
            logger_factory: фабрика логгеров
            allow_headdep_recursive: флаг для совместимости

        Returns:
            Dict[str, bool]: результаты обработки файлов
        """
        results = {}

        for csv_filename in file_list:
            csv_file_path = str(Path(csv_dir) / csv_filename)
            xml_filename = Path(csv_filename).stem + '.xml'
            xml_file_path = str(Path(csv_dir) / xml_filename)

            logger = logger_factory(csv_filename)
            logger.info(f"Начало обработки файла: {csv_filename}")

            success = self.csv_processor.process_csv_file_stream(
                folder_uid, csv_file_path, xml_file_path, logger,
                allow_headdep_recursive=allow_headdep_recursive
            )

            results[csv_filename] = success
            status = "успешно" if success else "с ошибкой"
            logger.info(f"Обработка файла {csv_filename} завершена: {status}")

        return results


# Фабричные функции
def create_csv_processor() -> CSVProcessor:
    """Создает универсальный процессор CSV файлов."""
    return CSVProcessor()


def create_batch_processor() -> BatchProcessor:
    """Создает пакетный процессор."""
    return BatchProcessor()
