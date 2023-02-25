from datetime import date, datetime
from decimal import Decimal
from typing import Any
import json

TYPES_DUMP: dict[str, type] = {
    'Decimal': str,
    'date': str,
    'datetime': str,
}
TYPES_LOAD: dict[str, Any] = {
    'Decimal': Decimal,
    'date': date.fromisoformat,
    'datetime': datetime.fromisoformat,
}
TYPES_DUMPK: dict[str, type] = {
    'bb': str,
    'd': str,
    'e': str,
    'f': str,
}
TYPES_LOADK: dict[str, Any] = {
    'bb': Decimal,
    'd': date.fromisoformat,
    'e': Decimal,
    'f': datetime.fromisoformat,
}


class JSON:
    dump_kwargs: dict[str, Any] = {'ensure_ascii': False}
    types_dump = TYPES_DUMP
    types_load = TYPES_LOAD

    def dumps(self, obj: Any) -> str:
        return json.dumps(self.dump_recursive(obj), **self.dump_kwargs)

    def dump_inner(self, k: str, v: Any) -> tuple[str, str]:
        t = type(v).__name__
        if t in self.types_dump:
            return f'{k}:{t}', self.types_dump[t](v)
        return k, v

    def dump_recursive(self, obj: Any) -> Any:
        r = obj
        if isinstance(obj, dict):
            r = {}
            for k, v in obj.items():
                if isinstance(v, list):
                    r[k] = self.dump_recursive(v)
                else:
                    k, v = self.dump_inner(k, v)
                    r[k] = v
        elif isinstance(obj, list):
            r = []
            for v in obj:
                r += [self.dump_recursive(v)]
        return r

    def loads(self, obj: str) -> Any:
        return self.load_recursive(json.loads(obj))

    def load_inner(self, kt: str, v: str) -> tuple[str, Any]:
        try:
            k, t = kt.split(':', 1)
            v = self.types_load[t](v)
            return k, v
        except ValueError:
            return kt, v

    def load_recursive(self, obj: Any) -> Any:
        r = obj
        if isinstance(obj, dict):
            r = {}
            for kt, v in obj.items():
                if isinstance(v, list):
                    r[kt] = self.load_recursive(v)
                else:
                    k, v = self.load_inner(kt, v)
                    r[k] = v
        elif isinstance(obj, list):
            r = []
            for v in obj:
                r += [self.load_recursive(v)]
        return r


class JSONK(JSON):
    types_dump = TYPES_DUMPK
    types_load = TYPES_LOADK

    def dump_inner(self, k: str, v: Any) -> tuple[str, str]:
        if k in self.types_dump:
            return k, self.types_dump[k](v)
        return k, v

    def load_inner(self, k: str, v: str) -> tuple[str, Any]:
        if k in self.types_load:
            return k, self.types_load[k](v)
        return k, v


INSTANCE: JSON = JSON()
INSTANCEK: JSONK = JSONK()

if __name__ == '__main__':
    test1 = {
        'a': 1,
        'b': 'й',
        'c': 2.3,
        'd': date.today(),
        'e': Decimal('1.2'),
        'f': datetime.today(),
        'h': [{'aa': 1, 'bb': Decimal('3.4')}],
        'j': [1, 2, 3],
    }

    str_ = INSTANCE.dumps(test1)
    assert 'bb:Decimal' in str_
    assert 'd:date' in str_
    assert 'e:Decimal' in str_
    assert 'f:datetime' in str_
    test2 = INSTANCE.loads(str_)
    assert test1 == test2

    str_ = INSTANCEK.dumps(test1)
    assert '"bb": "3.4"' in str_
    assert '"e": "1.2"' in str_
    test2 = INSTANCEK.loads(str_)
    assert test1 == test2
