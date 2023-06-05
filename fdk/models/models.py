
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, TypeGuard, get_args, get_origin


def are_models(values: Any) -> TypeGuard[List['AFdkModel']]:
    if not isinstance(values, Iterable):
        return False
    return all(isinstance(model, AFdkModel) for model in values)


def is_model(value: Any) -> TypeGuard['AFdkModel']:
    return isinstance(value, AFdkModel)


def _is_model_reference(value: Any) -> bool:
    if get_origin(value) is list:
        return any(issubclass(clazz, AFdkModel) for clazz in get_args(value))
    return issubclass(value, AFdkModel)


@dataclass
class AFdkModel:
    @classmethod
    def ref_attrs(cls) -> List[str]:
        attr_names = []
        for attr, value_type in cls.__annotations__.items():
            if not _is_model_reference(value_type):
                continue
            attr_names.append(attr)
        return attr_names

    fdk_id: str = field(hash=True, compare=False)
    name: str = field(hash=False)

    def as_dict(self, with_reference: bool):
        attr_dict = asdict(self)
        if with_reference:
            return attr_dict
        for attr in self.ref_attrs():
            attr_dict.pop(attr)
        return attr_dict

    def as_ref_dict(self) -> Dict[str, Any]:
        return {attr: self.__dict__[attr] for attr in self.ref_attrs()}


@dataclass
class Property(AFdkModel):
    name_clean: str = field(compare=False, repr=True)
    format: str = field(compare=False, repr=False)
    unit: str = field(compare=False, repr=False)
    description: str = field(compare=False, repr=False)
    example: str = field(compare=False, repr=False)
    object_ids: List[str] = field(default_factory=list, compare=False, repr=False)
    pset_ids: List[str] = field(default_factory=list, compare=False, repr=False)


@dataclass
class PropertySet(AFdkModel):
    properties: List[Property] = field(compare=False, repr=False)
    object_ids: List[str] = field(default_factory=list, compare=False, repr=False)


@dataclass
class FdkObject(AFdkModel):
    department: str = field(compare=False, repr=True)
    group: str = field(compare=False, repr=True)
    description: str = field(default='', compare=False, repr=False)
    properties: List[Property] = field(default_factory=list, compare=False, repr=False)
    property_sets: List[PropertySet] = field(default_factory=list, compare=False, repr=False)
