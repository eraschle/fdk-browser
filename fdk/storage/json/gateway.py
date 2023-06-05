
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from fdk.io.file import JsonHandler
from fdk.models.models import AFdkModel, FdkObject, Property, PropertySet
from fdk.storage.builder.builder import IBuilder
from fdk.storage.builder.json import (AJsonFdkObjectBuilder,
                                      AJsonPropertyBuilder,
                                      AJsonPropertySetBuilder)

_CLEAN_VALUES: List[Tuple[str, str]] = [
    ('[', ']',),
    ('(', ')',),
    ('{', '}',)
]


def _is_number(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


def _clean_name(name: str) -> str:
    splitted = name.split(' ')
    cleaned = []
    for value in splitted:
        value = value.strip()
        if len(value) < 2 and not _is_number(value):
            continue
        if any(value.startswith(start) and value.endswith(end) for start, end in _CLEAN_VALUES):
            continue
        cleaned.append(value)
    return ' '.join(cleaned).strip()


class JsonPropertyBuilder(AJsonPropertyBuilder):

    @classmethod
    def attribute_map(cls) -> Dict[str, str]:
        return {
            'fdk_id': 'ID_PTY',
            'name': 'name_PTY',
            'format': 'format',
            'unit': 'unit',
            'description': 'description',
            'example': 'example'
        }

    @classmethod
    def builders_map(cls) -> Dict[str, Tuple[str, IBuilder]]:
        return {}

    def _attributes(self, content: Dict[str, Any]) -> Dict[str, Any]:
        attr = super()._attributes(content)
        attr['name_clean'] = _clean_name(str(attr['name']))
        return attr


class JsonPropertySetBuilder(AJsonPropertySetBuilder):

    @classmethod
    def attribute_map(cls) -> Dict[str, str]:
        return {
            'fdk_id': 'ID_PSET',
            'name': 'name_PSET',
        }

    @classmethod
    def builders_map(cls) -> Dict[str, Tuple[str, IBuilder]]:
        return {
            'properties': ('pty_ids', JsonPropertyBuilder())
        }


class JsonObjectBuilder(AJsonFdkObjectBuilder):

    @classmethod
    def attribute_map(cls) -> Dict[str, str]:
        return {
            'fdk_id': 'ID_OBJ',
            'name': 'name_DE',
            'department': 'name_SYS',
            'group': 'name_OGRP',
            'description': 'description'
        }

    @classmethod
    def builders_map(cls) -> Dict[str, Tuple[str, IBuilder]]:
        return {
            'properties': ('properties', JsonPropertyBuilder()),
            'property_sets': ('psets', JsonPropertySetBuilder())
        }


class JsonFdkFactory():

    def __init__(self, handler: JsonHandler = JsonHandler(),
                 builder: IBuilder[FdkObject] = JsonObjectBuilder()) -> None:
        self.handler = handler
        self.builder = builder

    def create(self, path: Path) -> FdkObject:
        content = self.handler.read(path)
        return self.builder.build(content)


def _sort_model(model: AFdkModel, number_first: bool):
    splitted = model.fdk_id.split('_')
    if number_first:
        return int(splitted[-1]), '_'.join(splitted[:-1]),
    return '_'.join(splitted[:-1]), int(splitted[-1]),


class JsonFdkGateway():

    def __init__(self, path: Path, factory: JsonFdkFactory) -> None:
        self.path = path
        self.factory = factory
        self._objects: List[FdkObject] = []

    def _get_files(self, current: Path) -> List[Path]:
        files = []
        for path in current.iterdir():
            if path.is_dir():
                files.extend(self._get_files(path))
            elif path.suffix.endswith('json'):
                files.append(path)
        return files

    def _read_files(self) -> None:
        if len(self._objects) > 0:
            return
        for path in self._get_files(self.path):
            model = self.factory.create(path)
            self._update_property_sets(model.property_sets, model)
            self._update_properties(model.properties, model)
            self._objects.append(model)

    def _update_property_sets(self, property_sets: Iterable[PropertySet], model: FdkObject) -> None:
        for pset in property_sets:
            if model.fdk_id not in pset.object_ids:
                pset.object_ids.append(model.fdk_id)
            self._update_properties(pset.properties, model, pset)

    def _update_properties(self, properties: Iterable[Property], model: FdkObject, pset: Optional[PropertySet] = None) -> None:
        for prop in properties:
            if model.fdk_id not in prop.object_ids:
                prop.object_ids.append(model.fdk_id)
            if pset is None:
                continue
            if pset.fdk_id not in prop.pset_ids:
                prop.pset_ids.append(pset.fdk_id)

    def objects(self) -> List[FdkObject]:
        self._read_files()
        return sorted(self._objects, key=lambda model: _sort_model(model, number_first=False))

    def psets(self) -> List[PropertySet]:
        self._read_files()
        pset_dict = {}
        for model in self._objects:
            for pset in model.property_sets:
                pset_dict[pset.fdk_id] = pset
        return sorted(pset_dict.values(), key=lambda model: _sort_model(model, number_first=True))

    def properties(self) -> List[Property]:
        self._read_files()
        properties = {}
        for model in self._objects:
            for pset in model.property_sets:
                for prop in pset.properties:
                    properties[prop.fdk_id] = prop
            for prop in model.properties:
                properties[prop.fdk_id] = prop
        return sorted(properties.values(), key=lambda model: _sort_model(model, number_first=True))


def fdk_import_gateway(path: Path, factory: JsonFdkFactory = JsonFdkFactory()) -> JsonFdkGateway:
    return JsonFdkGateway(path=path, factory=factory)
