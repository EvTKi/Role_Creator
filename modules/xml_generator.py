"""
Модуль генерации XML файлов в формате RDF.
Универсальный — не зависит от семантики полей.
Использует только шаблоны и поля из конфигурации.
"""

import uuid
from datetime import datetime
import lxml.etree as etree
from lxml.etree import xmlfile
from typing import Dict, Callable, Any
from .config_manager import get_config_value
import logging


def gen_uid() -> str:
    """Генерирует уникальный идентификатор."""
    return str(uuid.uuid4())


class XMLGenerator:
    """
    Базовый генератор XML файлов с настраиваемыми параметрами.
    """

    def __init__(self, namespaces: Dict[str, str] = None):
        """
        Инициализация генератора XML.

        Args:
            namespaces: словарь пространств имён (если не передан — берётся из конфига)
        """
        self.namespaces = get_config_value('xml_generation.namespaces') or {}
        self.default_model_version = get_config_value(
            'csv_processing.model_version') or "1.0.0"
        self.default_model_name = get_config_value(
            'csv_processing.model_name') or "GeneratedModel"

    def generate_xml(
        self,
        output_file: str,
        content_generator: Callable,
        encoding: str = 'utf-8'
    ) -> None:
        """
        Генерирует XML файл используя переданный генератор контента.

        Args:
            output_file: путь к выходному файлу
            content_generator: функция, генерирующая содержимое
            encoding: кодировка выходного файла
        """
        with xmlfile(output_file, encoding=encoding) as xf:
            xf.write_declaration()
            with xf.element('{%s}RDF' % self.namespaces['rdf'], nsmap=self.namespaces):
                content_generator(xf)

    def add_full_model(
        self,
        xf: xmlfile,
        model_version: str = None,
        model_name: str = None
    ) -> str:
        """
        Добавляет элемент FullModel с метаданными.

        Args:
            xf: xmlfile объект
            model_version: версия модели
            model_name: имя модели

        Returns:
            str: UID модели
        """
        model_uid = gen_uid()
        model_version = model_version or self.default_model_version
        model_name = model_name or self.default_model_name

        with xf.element('{%s}FullModel' % self.namespaces.get('md', ''),
                        attrib={'{%s}about' % self.namespaces['rdf']: '#_' + model_uid}):
            time_str = datetime.now().strftime('%Y-%m-%dT%H:%M:%S') + "Z"

            with xf.element('{%s}Model.created' % self.namespaces.get('md', '')):
                xf.write(time_str)

            with xf.element('{%s}Model.version' % self.namespaces.get('md', '')):
                xf.write(model_version)

            me_namespace = get_config_value('xml_generation.me_namespace')
            if me_namespace:
                with xf.element('{%s}Model.name' % me_namespace, nsmap={'me': me_namespace}):
                    xf.write(model_name)
            else:
                with xf.element('{%s}Model.name' % self.namespaces.get('md', '')):
                    xf.write(model_name)

        return model_uid


class AccessXMLGenerator(XMLGenerator):
    """
    Универсальный генератор XML для системы доступа.
    Не зависит от семантики полей — использует только конфигурацию.
    """

    def __init__(self):
        """Инициализация генератора."""
        super().__init__()

    def add_role_structure(
        self,
        xf: xmlfile,
        data: Dict[str, str],
        folder_uid: str,  # ← UID папки, указанный пользователем
        logger: logging.Logger = None
    ) -> None:
        """
        Генерирует универсальную структуру: Role → Privilege → DataGroup → ObjectReference.
        Все имена полей и шаблоны берутся из конфига.
        ParentObject для Role = folder_uid, указанный пользователем.

        Args:
            xf: xmlfile объект
            data: словарь с данными строки CSV
            folder_uid: UID папки для ролей (указанный пользователем)
            logger: логгер для записи событий
        """
        if logger:
            object_uid_field = next(
                (f for f in data.keys() if '_uid' in f.lower()), 'object_uid')
            object_uid = data.get(object_uid_field, 'unknown')
            logger.debug(
                f"Начало генерации структуры для {object_uid_field}={object_uid}")

        role_uid = gen_uid()
        privilege_uid = gen_uid()
        datagroup_uid = gen_uid()
        objectref_uid = gen_uid()

        # Получаем шаблоны из конфига
        role_template = get_config_value(
            'csv_processing.role_template', 'Роль {org_name}')
        datagroup_template = get_config_value(
            'csv_processing.datagroup_template', 'Группа {org_name}')

        # Форматируем имена
        try:
            role_name = role_template.format(**data)
            datagroup_name = datagroup_template.format(**data)
        except KeyError as e:
            if logger:
                logger.error(
                    f"Ошибка формирования шаблона: отсутствует поле {e} в данных {data}")
            raise

        if logger:
            logger.debug(
                f"Сгенерированы UID: Role={role_uid}, Privilege={privilege_uid}, DataGroup={datagroup_uid}, ObjectReference={objectref_uid}")
            logger.debug(
                f"Имена: Role='{role_name}', DataGroup='{datagroup_name}'")

        # Получаем фиксированные ресурсы из конфига (кроме role_parent_object!)
        fixed = get_config_value('xml_generation.fixed_resources', {})
        dg_parent = fixed.get('datagroup_parent_object',
                              "#_f02c26a7-df3d-43a7-9c61-46d382e31d2c")
        priv_operation = fixed.get(
            'privilege_operation', "#_200006fe-0000-0000-c000-0000006d746c")
        dg_category = fixed.get('dataitem_category',
                                "#_200006ff-0000-0000-c000-0000006d746c")
        dg_class = fixed.get(
            'datagroup_class', "#_50000709-0000-0000-c000-0000006d746c")

        # === Role ===
        with xf.element('{%s}Role' % self.namespaces['cim'],
                        attrib={'{%s}about' % self.namespaces['rdf']: "#_" + role_uid}):
            with xf.element('{%s}IdentifiedObject.name' % self.namespaces['cim']):
                xf.write(role_name)
            # ❗❗❗ ВАЖНО: ParentObject = folder_uid, указанный пользователем
            with xf.element('{%s}IdentifiedObject.ParentObject' % self.namespaces['cim'],
                            attrib={'{%s}resource' % self.namespaces['rdf']: "#_" + folder_uid}):
                pass
            with xf.element('{%s}Role.kind' % self.namespaces['cim'],
                            attrib={'{%s}resource' % self.namespaces['rdf']: "cim:RoleKind.allow"}):
                pass
            with xf.element('{%s}Role.isHost' % self.namespaces['cim']):
                xf.write('false')
            with xf.element('{%s}Role.isUser' % self.namespaces['cim']):
                xf.write('true')
            with xf.element('{%s}Role.Privileges' % self.namespaces['cim'],
                            attrib={'{%s}resource' % self.namespaces['rdf']: "#_" + privilege_uid}):
                pass

        # === Privilege ===
        with xf.element('{%s}Privilege' % self.namespaces['cim'],
                        attrib={'{%s}about' % self.namespaces['rdf']: "#_" + privilege_uid}):
            with xf.element('{%s}Privilege.Role' % self.namespaces['cim'],
                            attrib={'{%s}resource' % self.namespaces['rdf']: "#_" + role_uid}):
                pass
            with xf.element('{%s}Privilege.DataItems' % self.namespaces['cim'],
                            attrib={'{%s}resource' % self.namespaces['rdf']: "#_" + datagroup_uid}):
                pass
            with xf.element('{%s}Privilege.Operation' % self.namespaces['cim'],
                            attrib={'{%s}resource' % self.namespaces['rdf']: priv_operation}):
                pass

        # === DataGroup ===
        with xf.element('{%s}DataGroup' % self.namespaces['cim'],
                        attrib={'{%s}about' % self.namespaces['rdf']: "#_" + datagroup_uid}):
            with xf.element('{%s}IdentifiedObject.name' % self.namespaces['cim']):
                xf.write(datagroup_name)
            with xf.element('{%s}IdentifiedObject.ParentObject' % self.namespaces['cim'],
                            attrib={'{%s}resource' % self.namespaces['rdf']: dg_parent}):
                pass
            with xf.element('{%s}DataItem.isHostRestricted' % self.namespaces['cim']):
                xf.write('false')
            with xf.element('{%s}DataItem.isUserRestricted' % self.namespaces['cim']):
                xf.write('true')
            with xf.element('{%s}DataItem.Privileges' % self.namespaces['cim'],
                            attrib={'{%s}resource' % self.namespaces['rdf']: "#_" + privilege_uid}):
                pass
            with xf.element('{%s}DataItem.Category' % self.namespaces['cim'],
                            attrib={'{%s}resource' % self.namespaces['rdf']: dg_category}):
                pass
            with xf.element('{%s}DataGroup.Class' % self.namespaces['cim'],
                            attrib={'{%s}resource' % self.namespaces['rdf']: dg_class}):
                pass
            with xf.element('{%s}DataGroup.Objects' % self.namespaces['cim'],
                            attrib={'{%s}resource' % self.namespaces['rdf']: "#_" + objectref_uid}):
                pass

        # === ObjectReference ===
        object_uid_field = next(
            (f for f in data.keys() if '_uid' in f.lower()), None)
        if not object_uid_field:
            raise ValueError(
                "Не найдено поле, содержащее '_uid' для ObjectReference.objectUid")

        with xf.element('{%s}ObjectReference' % self.namespaces['cim'],
                        attrib={'{%s}about' % self.namespaces['rdf']: "#_" + objectref_uid}):
            with xf.element('{%s}ObjectReference.objectUid' % self.namespaces['cim']):
                xf.write(data[object_uid_field])
            with xf.element('{%s}ObjectReference.Group' % self.namespaces['cim'],
                            attrib={'{%s}resource' % self.namespaces['rdf']: "#_" + datagroup_uid}):
                pass

        if logger:
            logger.debug(
                f"Структура для {object_uid_field}={data[object_uid_field]} успешно сгенерирована")


def format_xml_pretty(file_path: str) -> None:
    """
    Читает XML и записывает с отступами (pretty print).

    Args:
        file_path: путь к XML-файлу
    """
    parser = etree.XMLParser(remove_blank_text=False, encoding='utf-8')
    tree = etree.parse(file_path, parser)
    root = tree.getroot()
    etree.indent(root, space="  ")
    tree.write(file_path, encoding="utf-8",
               xml_declaration=True, pretty_print=True)


# Фабричная функция
def create_access_generator() -> AccessXMLGenerator:
    """Создает универсальный генератор XML."""
    return AccessXMLGenerator()
