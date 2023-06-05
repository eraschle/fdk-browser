import codecs
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Protocol, TextIO, TypeVar

TUri = TypeVar('TUri', bound=Path, contravariant=True)
TContent = TypeVar('TContent', bound=Iterable)


class IoHandler(Protocol[TUri, TContent]):
    extension: str

    def can_read(self, path: TUri, **kwargs) -> bool:
        ...

    def read(self, path: TUri, **kwargs) -> TContent:
        ...

    def write(self, path: TUri, context: TContent, **kwargs) -> None:
        ...


class AFileHandler(ABC, IoHandler[Path, TContent]):

    def __init__(self, extension: str, encoding: str = 'utf-8') -> None:
        super().__init__()
        self.encoding = encoding
        self.extension = extension

    def _as_str(self, value: Path) -> str:
        value = value.with_suffix(self.extension)
        return str(value.absolute())

    def can_read(self, path: Path, **kwargs) -> bool:
        return path.exists()

    def _open(self, path: Path, callback: Callable[[TextIO], Any], **kwargs) -> Any:
        args = {'mode': 'r', 'encoding': self.encoding}
        args.update(kwargs)
        with open(self._as_str(path), **args) as file:
            return callback(file, **kwargs)

    def _first_line(self, file: TextIO, **kwargs) -> str:
        return file.readline()

    def _read_first_line(self, path: Path, **kwargs) -> str:
        return self._open(path, self._first_line)

    def read(self, path: Path, **kwargs) -> TContent:
        return self._open(path, self._read, **kwargs)

    def write(self, path: Path, content: TContent, **kwargs) -> None:
        args = {'mode': 'w', 'encoding': self.encoding}
        args.update(kwargs)
        with codecs.open(self._as_str(path), **args) as file:
            self._write(file, content, **kwargs)

    @abstractmethod
    def _read(self, file: TextIO, **kwargs) -> TContent:
        pass

    @abstractmethod
    def _write(self, file: TextIO, content: TContent, **kwargs) -> None:
        pass


class TextHandler(AFileHandler[Iterable[str]]):

    def _read(self, file: TextIO, **kwargs) -> Iterable[str]:
        return file.readlines()

    def _write(self, file: TextIO, content: Iterable[str], **kwargs) -> None:
        content = [line if line.endswith('\n') else f'{line}\n' for line in content]
        file.writelines(content)


class CsvHandler(AFileHandler[List[List[Any]]]):

    def __init__(self, delimiter: str, extension: str = '.csv', encoding: str = 'utf-8') -> None:
        super().__init__(extension, encoding)
        self.delimiter = delimiter

    def _read(self, file: TextIO, **kwargs) -> List[List[Any]]:
        return [line.split(self.delimiter) for line in file.readlines()]

    def _to_dict(self, headers: Iterable[str], values: List[Any], **kwargs) -> Dict[str, Any]:
        value_dict = {}
        for index, header in enumerate(headers):
            value = values[index] if index < len(values) else kwargs.get('default', None)
            value_dict[header] = value
        return value_dict

    def _as_dict(self, headers: Iterable[str], lines: Iterable[List[Any]], **kwargs) -> List[Dict[str, Any]]:
        values = []
        for line in lines:
            values.append(self._to_dict(headers, line, **kwargs))
        return values

    def read_as_dict(self, path: Path, **kwargs) -> List[Dict[str, Any]]:
        hdr_idx = kwargs.get('header_idx', 0)
        lines = self.read(path)
        if len(lines) <= hdr_idx:
            return []
        headers = [str(hdr).strip() for hdr in lines[hdr_idx]]
        return self._as_dict(headers, lines[hdr_idx + 1:], **kwargs)

    def _write(self, file: TextIO, content: List[List[Any]], **kwargs) -> None:
        raise NotImplementedError


class JsonHandler(AFileHandler[Dict[str, Any]]):

    def __init__(self, extension: str = '.json', encoding: str = 'utf-8') -> None:
        super().__init__(extension, encoding)

    def can_read(self, path: Path, **kwargs) -> bool:
        if not super().can_read(path, **kwargs):
            return False
        return self._read_first_line(path, **kwargs).startswith('{')

    def _read(self, file: TextIO, **kwargs) -> Dict[str, Any]:
        return json.loads(file.read())

    def _write(self, file: TextIO, content: Dict[str, Any], **kwargs) -> None:
        args = {'indent': 4, 'ensure_ascii': False}
        args.update(**kwargs)
        json.dump(content, file, **args)
