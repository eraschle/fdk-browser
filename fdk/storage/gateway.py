
from typing import Iterable, List, Optional, Protocol, Set, TypeVar

from fdk.models.models import AFdkModel, FdkObject, Property, PropertySet
from fdk.storage.db.deta import FdkObjectGateway, FdkPropertyGateway, FdkPropertySetGateway

TModel = TypeVar('TModel', bound=AFdkModel)


class IModelGateway(Protocol[TModel]):

    def create_or_update(self, model: TModel) -> None:
        ...

    def create_or_update_many(self, models: Iterable[TModel]) -> None:
        ...

    def all_ids(self) -> List[str]:
        ...

    def by_id(self, fdk_id: str) -> Optional[TModel]:
        ...

    def by_ids(self, fdk_ids: Iterable[str]) -> List[TModel]:
        ...

    def all_names(self) -> Set[str]:
        ...

    def by_name(self, name: str) -> List[TModel]:
        ...

    def all_models(self) -> List[TModel]:
        ...

    def delete_all(self) -> None:
        ...


class IFdkGateway(Protocol):
    properties: IModelGateway[Property]
    property_sets: IModelGateway[PropertySet]
    objects: IModelGateway[FdkObject]

    def save_object(self, model: FdkObject) -> None:
        ...

    def save_objects(self, models: Iterable[FdkObject]) -> None:
        ...

    def get_objects(self) -> List[FdkObject]:
        ...

    def delete_objects(self) -> None:
        ...

    def save_pset(self, model: PropertySet) -> None:
        ...

    def save_psets(self, models: Iterable[PropertySet]) -> None:
        ...

    def get_psets(self) -> List[PropertySet]:
        ...

    def delete_psets(self) -> None:
        ...

    def save_property(self, model: Property) -> None:
        ...

    def save_properties(self, models: Iterable[Property]) -> None:
        ...

    def get_properties(self) -> List[Property]:
        ...

    def delete_properties(self) -> None:
        ...

    def properties_by_name(self, name: Optional[str]) -> List[Property]:
        ...

    def property_names(self) -> Set[str]:
        ...


class FdkGateway(IFdkGateway):
    def __init__(self, objects: IModelGateway[FdkObject],
                 property_sets: IModelGateway[PropertySet],
                 properties: IModelGateway[Property]) -> None:
        super().__init__()
        self.properties = properties
        self.property_sets = property_sets
        self.objects = objects

    def save_object(self, model: FdkObject) -> None:
        self.objects.create_or_update(model)

    def save_objects(self, models: Iterable[FdkObject]) -> None:
        self.objects.create_or_update_many(models)

    def get_objects(self) -> List[FdkObject]:
        return self.objects.all_models()

    def delete_objects(self) -> None:
        self.objects.delete_all()

    def save_pset(self, model: PropertySet) -> None:
        self.property_sets.create_or_update(model)

    def save_psets(self, models: Iterable[PropertySet]) -> None:
        self.property_sets.create_or_update_many(models)

    def get_psets(self) -> List[PropertySet]:
        return self.property_sets.all_models()

    def delete_psets(self) -> None:
        self.property_sets.delete_all()

    def save_property(self, model: Property) -> None:
        self.properties.create_or_update(model)

    def save_properties(self, models: Iterable[Property]) -> None:
        self.properties.create_or_update_many(models)

    def get_properties(self) -> List[Property]:
        return self.properties.all_models()

    def delete_properties(self) -> None:
        self.properties.delete_all()

    def properties_by_name(self, name: Optional[str]) -> List[Property]:
        if name is None:
            return []
        return self.properties.by_name(name)

    def property_names(self) -> List[str]:
        return sorted(self.properties.all_names())


def fdk_gateway() -> IFdkGateway:
    return FdkGateway(
        objects=FdkObjectGateway(),
        property_sets=FdkPropertySetGateway(),
        properties=FdkPropertyGateway()
    )
