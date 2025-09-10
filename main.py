"""
Основной модуль приложения для конвертации CSV в XML
Координирует работу всех модулей из папки modules
"""


from typing import List, Callable
import sys
import os

# Добавляем путь к папке modules в системный путь
# modules_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modules')
# sys.path.insert(0, modules_path)

# Импортируем модули из папки modules
from modules.csv_reader import get_csv_files
from modules.csv_processor import create_batch_processor
from modules.file_manager import create_file_manager, create_cli_manager
from modules.logger_manager import create_logger_manager, LoggerConfig
from modules.config_manager import get_config_value


def process_all_csv_from_list(
    folder_uid: str,
    csv_dir: str,
    file_list: List[str],
    log_callback: Callable[[str], None] = None,
    allow_headdep_recursive=get_config_value(
        'csv_processing.allow_headdep_recursive')
) -> dict:
    """
    Обрабатывает список CSV файлов через пакетный процессор.

    Args:
        folder_uid: UID папки для ролей
        csv_dir: директория с CSV файлами
        file_list: список файлов для обработки
        log_callback: callback для логов UI
        allow_headdep_recursive: разрешить рекурсивный доступ

    Returns:
        dict: результаты обработки
    """
    # Создаем менеджеры
    file_manager = create_file_manager(csv_dir)
    logger_manager = create_logger_manager()
    batch_processor = create_batch_processor()

    # Создаем директорию для логов
    log_dir = file_manager.create_log_directory()

    # Фабрика логгеров
    def logger_factory(filename: str):
        log_path = file_manager.get_log_path(filename)
        config = LoggerConfig()
        return logger_manager.create_logger(
            log_path, log_file_path=log_path,
            ui_callback=log_callback, config=config
        )

    # Обрабатываем файлы
    results = batch_processor.process_file_list(
        folder_uid, csv_dir, file_list, logger_factory, allow_headdep_recursive
    )

    return results


def debug_cli():
    """CLI для пакетного запуска."""
    cli_manager = create_cli_manager()
    logger_manager = create_logger_manager()

    folder_uid, csv_dir = cli_manager.get_cli_parameters()
    file_manager = create_file_manager(csv_dir)
    csv_files = cli_manager.validate_and_list_files(file_manager)

    if not csv_files:
        return

    def cli_log(msg):
        print(msg, end='' if msg.endswith('\n') else '\n')

    results = process_all_csv_from_list(
        folder_uid, csv_dir, csv_files,
        log_callback=cli_log,
        allow_headdep_recursive=True
    )

    successful = sum(1 for success in results.values() if success)
    total = len(results)
    print(f"Обработано файлов: {successful}/{total}")

    if successful < total:
        print("Ошибки в файлах:")
        for filename, success in results.items():
            if not success:
                print(f"  - {filename}")

    cli_manager.print_completion_message()


if __name__ == '__main__':
    debug_cli()
