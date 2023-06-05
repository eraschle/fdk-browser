
from abc import abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Type

from fdk.models.models import FdkObject, Property, PropertySet

from .builder import IBuilder, TModel


class AJsonBuilder(IBuilder[TModel]):
    _models: Dict[str, TModel] = {}

    @classmethod
    def _get_model(cls, model: TModel) -> TModel:
        if model.fdk_id not in cls._models:
            cls._models[model.fdk_id] = model
        return cls._models[model.fdk_id]

    @classmethod
    @abstractmethod
    def attribute_map(cls) -> Dict[str, str]:
        pass

    @classmethod
    @abstractmethod
    def builders_map(cls) -> Dict[str, Tuple[str, IBuilder]]:
        pass

    def __init__(self, model_type: Type[TModel], attr_map: Optional[Dict[str, str]] = None,
                 builder_map: Optional[Dict[str, Tuple[str, IBuilder]]] = None) -> None:
        self.model_type = model_type
        self.attr_map = attr_map or self.attribute_map()
        self.builder_map = builder_map or self.builders_map()

    def _attributes(self, content: Dict[str, Any]) -> Dict[str, Any]:
        attributes = {}
        for attr, src_attr in self.attr_map.items():
            value = content.get(src_attr)
            if value is None:
                continue
            if isinstance(value, str):
                value = value.strip()
            attributes[attr] = value
        return attributes

    def _model_attributes(self, content: Dict[str, Any]) -> Dict[str, Any]:
        attributes = {}
        for attr, builder_tuple in self.builder_map.items():
            src_attr, builder = builder_tuple
            value = content.get(src_attr)
            if value is None:
                continue
            if isinstance(value, List):
                attributes[attr] = builder.build_many(value)
            else:
                attributes[attr] = builder.build(value)
        return attributes

    def build(self, content: Dict[str, Any]) -> TModel:
        attributes = self._attributes(content)
        attributes.update(self._model_attributes(content))
        model = self.model_type(**attributes)
        return self._get_model(model)

    def build_many(self, contents: List[Dict[str, Any]]) -> List[TModel]:
        return [self.build(content) for content in contents]


class AJsonPropertyBuilder(AJsonBuilder[Property]):

    def __init__(self, attr_map: Optional[Dict[str, str]] = None,
                 builder_map: Optional[Dict[str, Tuple[str, IBuilder]]] = None) -> None:
        super().__init__(Property, attr_map, builder_map)


class AJsonPropertySetBuilder(AJsonBuilder[PropertySet]):

    def __init__(self, attr_map: Optional[Dict[str, str]] = None,
                 builder_map: Optional[Dict[str, Tuple[str, IBuilder]]] = None) -> None:
        super().__init__(PropertySet, attr_map, builder_map)


class AJsonFdkObjectBuilder(AJsonBuilder[FdkObject]):

    def __init__(self, attr_map: Optional[Dict[str, str]] = None,
                 builder_map: Optional[Dict[str, Tuple[str, IBuilder]]] = None) -> None:
        super().__init__(FdkObject, attr_map, builder_map)
