#!/usr/bin/env python3
from datetime import date, datetime
from decimal import Decimal
from typing import Any
import json

TYPES_DUMP: dict[str, type] = {
    'd': str,
    'e': str,
    'f': str,
}
TYPES_LOAD: dict[str, Any] = {
    'd': date.fromisoformat,
    'e': Decimal,
    'f': datetime.fromisoformat,
}


class Tipizator:
    dump_kwargs: dict[str, Any] = {'ensure_ascii': False}
    types_dump = TYPES_DUMP
    types_load = TYPES_LOAD

    def dump(self, obj: dict) -> dict:
        r = obj.copy()
        for k, v in obj.items():
            if k in self.types_dump:
                r[k] = self.types_dump[k](v)
        return r

    def dumps(self, obj: dict) -> str:
        return json.dumps(self.dump(obj), **self.dump_kwargs)

    def load(self, obj: dict) -> dict:
        r = obj.copy()
        for k, v in obj.items():
            if k in self.types_load:
                r[k] = self.types_load[k](v)
        return r

    def loads(self, obj: str) -> dict:
        return self.load(json.loads(obj))


INSTANCE: Tipizator = Tipizator()

if __name__ == '__main__':
    test1 = {
        'a': 1,
        'b': 'й',
        'c': 2.3,
        'd': date.fromisoformat('2023-03-21'),
        'e': Decimal('1.2'),
        'f': datetime.fromisoformat('2023-03-21'),
    }
    test2 = {
        'a': 1,
        'b': 'й',
        'c': 2.3,
        'd': '2023-03-21',
        'e': '1.2',
        'f': '2023-03-21 00:00:00',
    }

    str1 = INSTANCE.dumps(test1)
    str2 = json.dumps(test2, **INSTANCE.dump_kwargs)
    assert str1 == str2

    test1_ = INSTANCE.loads(str1)
    assert test1 == test1_
