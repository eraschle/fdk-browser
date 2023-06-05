from dataclasses import fields
from fdk.storage.builder.json import (AJsonFdkObjectBuilder,
                                      AJsonPropertyBuilder,
                                      AJsonPropertySetBuilder)
from fdk.storage.builder.builder import IBuilder, TModel
from fdk.models.models import (AFdkModel, FdkObject, Property, PropertySet,
                               are_models, is_model)
from deta import _Base, Deta
import dotenv as env
from typing import (Any, Dict, Generic, Iterable, List, Optional, Protocol,
                    Set, Tuple)
from abc import ABC
import os


env.load_dotenv('.env')


_KEY = 'key'
_NAME = 'name'
_CONTENT = 'content'
_NAME_CLEAN = 'name_clean'
_OBJECT_IDS = 'object_ids'
_PSET_IDS = 'pset_ids'


def _get_key(content: Dict[str, Any]) -> str:
    return content[_KEY]


def _get_name(content: Dict[str, Any], name: str = _NAME) -> str:
    return content[name]


def _as_db(model: AFdkModel) -> Dict[str, Any]:
    db_attr = model.as_dict(with_reference=False)
    db_attr[_KEY] = model.fdk_id
    for attr, value in model.as_ref_dict().items():
        if is_model(value):
            db_attr[attr] = value.fdk_id
        elif are_models(value):
            db_attr[attr] = [model.fdk_id for model in value]
    return db_attr


def _as_build_dict(content: Dict[str, Any]) -> Dict[str, Any]:
    # model_content = content.pop(_CONTENT)
    # content.update(model_content)
    return content


class IDetaBuilder(IBuilder[TModel], Protocol[TModel]):
    pass


class PropertyBuilder(AJsonPropertyBuilder, IDetaBuilder[Property]):

    @ classmethod
    def attribute_map(cls) -> Dict[str, str]:
        return {field.name: field.name for field in fields(Property)}

    @ classmethod
    def builders_map(cls) -> Dict[str, Tuple[str, IBuilder]]:
        return {}

    def build(self, content: Dict[str, Any]) -> Property:
        return super().build(_as_build_dict(content))


class PropertySetBuilder(IDetaBuilder[PropertySet], AJsonPropertySetBuilder):

    @ classmethod
    def attribute_map(cls) -> Dict[str, str]:
        return {field.name: field.name for field in fields(PropertySet)}

    @ classmethod
    def builders_map(cls) -> Dict[str, Tuple[str, IBuilder]]:
        return {
            'properties': ('properties', PropertyBuilder())
        }

    def build(self, content: Dict[str, Any]) -> PropertySet:
        return super().build(_as_build_dict(content))


class FdkObjectBuilder(IDetaBuilder[FdkObject], AJsonFdkObjectBuilder):

    @ classmethod
    def attribute_map(cls) -> Dict[str, str]:
        return {field.name: field.name for field in fields(FdkObject)}

    @ classmethod
    def builders_map(cls) -> Dict[str, Tuple[str, IBuilder]]:
        return {
            'properties': ('properties', PropertyBuilder()),
            'property_sets': ('property_sets', PropertySetBuilder())
        }

    def build(self, content: Dict[str, Any]) -> FdkObject:
        return super().build(_as_build_dict(content))


def _get_deta_db(name: str) -> _Base:
    deta_key = os.getenv('DETA_KEY')
    if deta_key is None:
        raise EnvironmentError('DETA_KEY not exists')
    return Deta(project_key=deta_key).Base(name=name)


class AFdkGateway(ABC, Generic[TModel]):

    def __init__(self, db_name: str, builder: IDetaBuilder[TModel],
                 gateway_map: Dict[str, 'AFdkGateway'], fetch_limit: int = 1000) -> None:
        super().__init__()
        self.db = _get_deta_db(db_name)
        self.builder = builder
        self.gateways = gateway_map
        self.fetch_limit = fetch_limit

    def _get_by(self, fdk_id: str) -> Optional[Dict[str, Any]]:
        content = self.db.get(fdk_id)
        return content if isinstance(content, dict) else None

    def create_or_update(self, model: TModel) -> None:
        self.db.put(self._as_db_dict(model))

    def create_or_update_many(self, models: Iterable[TModel]) -> None:
        self.db.put_many([self._as_db_dict(model) for model in models])

    def _as_db_dict(self, model: TModel) -> Dict[str, Any]:
        return _as_db(model)

    def delete_all(self) -> None:
        model_ids = self.all_ids()
        while len(model_ids) > 0:
            for model_id in model_ids:
                self.db.delete(model_id)
            model_ids = self.all_ids()

    def all_ids(self) -> List[str]:
        contents = self.db.fetch(limit=self.fetch_limit).items
        return [_get_key(content) for content in contents]

    def by_id(self, fdk_id: str) -> Optional[TModel]:
        content = self._get_by(fdk_id)
        if content is None:
            return None
        content = self._with_reference_content(content)
        return self.builder.build(content)

    def _with_reference_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        for attr, gateway in self.gateways.items():
            ref_content = content.get(attr)
            if ref_content is None:
                raise AttributeError(f'{attr} does not exist in {content}')
            content[attr] = gateway.content_by_ids(ref_content)
        return content

    def content_by_ids(self, fdk_ids: Iterable[str]) -> List[Dict[str, Any]]:
        models = [self._get_by(fdk_id) for fdk_id in fdk_ids]
        return [model for model in models if model is not None]

    def by_ids(self, fdk_ids: Iterable[str]) -> List[TModel]:
        models = [self.by_id(fdk_id) for fdk_id in fdk_ids]
        return [model for model in models if model is not None]

    def all_names(self) -> Set[str]:
        contents = self.db.fetch(limit=self.fetch_limit).items
        return set([_get_name(content) for content in contents])

    def by_name(self, name: str) -> List[TModel]:
        contents = self.db.fetch({_NAME: name}, limit=self.fetch_limit).items
        return self.builder.build_many(contents)

    def all_models(self) -> List[TModel]:
        contents = self.db.fetch(limit=self.fetch_limit).items
        return self.builder.build_many(contents)


class FdkPropertyGateway(AFdkGateway[Property]):

    def __init__(self, builder: Optional[IDetaBuilder[Property]] = None,
                 gateway_map: Optional[Dict[str, 'AFdkGateway']] = None) -> None:
        super().__init__('properties', builder or PropertyBuilder(), gateway_map or {}, fetch_limit=5000)

    def _as_db_dict(self, model: Property) -> Dict[str, Any]:
        db_dict = super()._as_db_dict(model)
        # db_dict[_OBJECT_IDS] = db_dict[_CONTENT].pop(_OBJECT_IDS)
        # db_dict[_PSET_IDS] = db_dict[_CONTENT].pop(_PSET_IDS)
        # db_dict[_NAME_CLEAN] = db_dict[_CONTENT].pop(_NAME_CLEAN)
        return db_dict

    def all_names(self) -> Set[str]:
        contents = self.db.fetch(limit=self.fetch_limit).items
        return set([_get_name(content, _NAME_CLEAN) for content in contents])

    def by_name(self, name: str) -> List[Property]:
        contents = self.db.fetch(query={_NAME_CLEAN: name}, limit=self.fetch_limit).items
        return self.builder.build_many(contents)


class FdkPropertySetGateway(AFdkGateway[PropertySet]):

    @ classmethod
    def gaeteways_map(cls) -> Dict[str, AFdkGateway]:
        return {
            'properties': FdkPropertyGateway(),
        }

    def __init__(self, builder: Optional[IDetaBuilder[PropertySet]] = None,
                 gateway_map: Optional[Dict[str, 'AFdkGateway']] = None) -> None:
        super().__init__('property_sets', builder or PropertySetBuilder(),
                         gateway_map or self.gaeteways_map())

    def _as_db_dict(self, model: PropertySet) -> Dict[str, Any]:
        db_dict = super()._as_db_dict(model)
        # db_dict[_OBJECT_IDS] = db_dict[_CONTENT].pop(_OBJECT_IDS)
        return db_dict


class FdkObjectGateway(AFdkGateway[FdkObject]):

    @ classmethod
    def gaeteways_map(cls) -> Dict[str, AFdkGateway]:
        return {
            'properties': FdkPropertyGateway(),
            'property_sets': FdkPropertySetGateway()
        }

    def __init__(self, builder: Optional[IDetaBuilder[FdkObject]] = None,
                 gateway_map: Optional[Dict[str, 'AFdkGateway']] = None) -> None:
        super().__init__('fdk_objects', builder or FdkObjectBuilder(),
                         gateway_map or self.gaeteways_map(), fetch_limit=3000)
