from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Callable, Dict, Iterable, Optional, List

logger = logging.getLogger(__name__)


class PropertyBag:
    """Hierarchical property bag structure. Each PropertyBag is a dictionary of name/value pairs where each
    value can either be a string or another child PropertyBag. In addition, each PropertyBag may have a
    base PropertyBag that it will inherit (and can override) values from."""

    def __init__(self, name: str, value: Optional[str] = '',
                 base_props: Optional[Iterable[PropertyBag]] = None) -> None:
        if name is None:
            raise ValueError('name')

        if value is None:
            raise ValueError('value')

        self._name = name
        self._value = value
        self._bases: List[PropertyBag] = []
        self._children: PropSetCollection = {}

        if base_props:
            self._bases.extend(base_props)

    def __str__(self):
        return f'{self.name}{f"={self.value}" if self.value is not None else ""}'

    def __next__(self):
        yield from self.flatten_properties.values()

    @lru_cache(maxsize=16)
    def __contains__(self, item):
        return item in self.flatten_properties

    @lru_cache(maxsize=32)
    def __getitem__(self, item) -> Optional[PropertyBag]:
        # try this level first
        if item in self._children:
            return self._children[item]

        # then recurse up bases (in reverse order, so that later items override previous ones)
        for base in self._bases[::-1]:
            if item in base:
                return base[item]

        return None

    @property
    def name(self) -> str:
        return self._name

    @property
    def value(self) -> str:
        return self._value

    @property
    def bases(self):
        return self._bases

    @property
    def count(self):
        return len(self.flatten_properties)

    def add(self, prop: PropertyBag) -> None:
        self._children[prop.name] = prop

    def get(self, name: str, default=None) -> Optional[str, bool]:
        """Tries to get value from the named prop"""
        if name in self:
            return self[name].value

        return default

    def getint(self, name: str, default=None) -> Optional[int, bool]:
        if name in self:
            return int(self[name].value)

        return default

    def convert(self, name: str, convertor: Callable[[str], Any], default: Any = None):
        if name in self:
            return convertor(self[name].value)

        return default

    @property
    def flatten_properties(self) -> PropSetCollection:
        properties: PropSetCollection = {}

        # start with parent properties
        for base_prop in self._bases:
            for name, child in base_prop.flatten_properties.items():
                properties[name] = child

        # and then override with the child ones
        for name, child in self._children.items():
            properties[name] = child

        return properties


PropSetCollection = Dict[str, PropertyBag]
