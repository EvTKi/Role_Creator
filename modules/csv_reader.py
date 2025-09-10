"""
Модуль чтения CSV файлов с поддержкой кодировок, валидации и логирования.
Универсальный — не зависит от семантики полей, работает с любыми required_fields из конфига.
"""

import chardet
import csv
import os
from typing import Dict, List, Tuple, Generator, Any
from .config_manager import get_config_value
import uuid
import logging


def gen_uid() -> str:
    """Генерирует уникальный идентификатор."""
    return str(uuid.uuid4())


def is_valid_uuid(val) -> bool:
    """
    Проверяет, является ли строка валидным UUID.

    Args:
        val: значение для проверки

    Returns:
        bool: True если валидный UUID
    """
    if not isinstance(val, str):
        return False
    try:
        uuid.UUID(val)
        return True
    except ValueError:
        return False


def read_encoding(file_path: str) -> str:
    """
    Определяет кодировку файла с помощью chardet.

    Args:
        file_path: путь к файлу

    Returns:
        str: определённая кодировка

    Raises:
        ValueError: если кодировку не удалось определить
    """
    with open(file_path, 'rb') as f:
        rawdata = f.read()  # Читаем ВЕСЬ файл для более точного определения

    result = chardet.detect(rawdata)
    encoding = result['encoding']
    confidence = result['confidence']

    if encoding is None or confidence < 0.7:
        # Если не уверены — пробуем стандартные кодировки
        return 'utf-8'

    return encoding


def iter_csv_rows(
    csv_file_path: str,
    encoding: str,
    required_fields: list,
    logger: Any = None,
    delimiter: str = None
) -> Generator[Tuple[int, Dict], None, None]:
    """
    Генератор: итерирует валидные строки CSV с номером строки.
    Поддерживает регистронезависимые заголовки.
    При ошибке декодирования — пробует fallback-кодировки.

    Args:
        csv_file_path: путь к CSV файлу
        encoding: кодировка файла (предполагаемая)
        required_fields: список обязательных полей
        logger: объект логгера (опционально)
        delimiter: разделитель в CSV (по умолчанию из конфига)

    Yields:
        Tuple[int, Dict]: номер строки и словарь с данными строки
    """
    if delimiter is None:
        delimiter = get_config_value('csv_processing.default_delimiter', ';')

    # Список кодировок для fallback
    encodings_to_try = [encoding, 'cp1251', 'utf-8', 'utf-8-sig']

    raw_rows = None
    used_encoding = None

    for enc in encodings_to_try:
        try:
            with open(csv_file_path, encoding=enc, errors='strict') as csvfile:
                content = csvfile.read()
                used_encoding = enc
                break
        except UnicodeDecodeError as e:
            if logger:
                logger.warning(
                    f"Не удалось открыть файл в кодировке {enc}: {e}")
            continue
    else:
        # Если ни одна кодировка не подошла — читаем с заменой символов
        with open(csv_file_path, encoding=encoding, errors='replace') as csvfile:
            content = csvfile.read()
            used_encoding = encoding
            if logger:
                logger.error(
                    f"Файл открыт с заменой невалидных символов в кодировке {encoding}")

    if logger:
        logger.info(f"Файл успешно открыт в кодировке: {used_encoding}")

    try:
        # Используем StringIO для имитации файла
        from io import StringIO
        csvfile = StringIO(content)

        reader = csv.DictReader(csvfile, delimiter=delimiter)
        reader.fieldnames = [field.strip().lower()
                             for field in reader.fieldnames]

        for line_num, row in enumerate(reader, start=2):
            row = {k.strip().lower(): v for k, v in row.items()}
            ok, err_msg = check_required_fields(row, required_fields)
            if not ok:
                if logger:
                    logger.error(
                        f"Строка {line_num}: {err_msg}. Данные: {row}")
                continue
            yield line_num, row

    except Exception as e:
        if logger:
            logger.error(f"Ошибка обработки CSV-файла {csv_file_path}: {e}")
        return


def check_required_fields(row: dict, required_fields: list) -> Tuple[bool, str]:
    """
    Проверяет наличие и валидность обязательных полей в строке CSV.
    Если поле оканчивается на '_uid', проверяется как UUID.

    Args:
        row: словарь с данными строки
        required_fields: список обязательных полей из конфига

    Returns:
        Tuple[bool, str]: (успешно, сообщение об ошибке)
    """
    for field in required_fields:
        val = row.get(field)
        if val is None or not str(val).strip():
            return False, f"Поле '{field}' отсутствует или пустое"

        if '_uid' in field.lower():
            uid_str = str(val).strip()
            if not is_valid_uuid(uid_str):
                return False, f"Поле '{field}' не является валидным UUID: '{uid_str}'"

    return True, ""


def get_csv_files(directory: str, exclude_files: List[str] = None) -> List[str]:
    """
    Получает список CSV файлов в директории, исключая указанные.

    Args:
        directory: путь к директории
        exclude_files: список файлов для исключения (по умолчанию ['Sample.csv'])

    Returns:
        List[str]: список имен CSV файлов
    """
    if exclude_files is None:
        exclude_files = get_config_value(
            'file_management.exclude_files', ['Sample.csv'])

    exclude_files = [f.lower() for f in exclude_files]
    all_files = [
        f for f in os.listdir(directory)
        if f.lower().endswith('.csv') and f.lower() not in exclude_files
    ]
    return all_files


# Алиасы для обратной совместимости
detect_encoding = read_encoding
iterate_csv_rows = iter_csv_rows
