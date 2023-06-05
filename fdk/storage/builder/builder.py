
from typing import Any, Dict, List, Protocol, Tuple, TypeVar

from fdk.models.models import AFdkModel

TModel = TypeVar('TModel', bound=AFdkModel)


class IBuilder(Protocol[TModel]):
    attr_map: Dict[str, str]
    builder_map: Dict[str, Tuple[str, 'IBuilder']]

    def build(self, content: Dict[str, Any]) -> TModel:
        ...

    def build_many(self, content: List[Dict[str, Any]]) -> List[TModel]:
        ...
