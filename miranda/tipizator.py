from typing import Any
import json


class Tipizator:
    dump_kwargs: dict[str, Any] = {'ensure_ascii': False}

    def __init__(self, types_dump: dict[str, Any] = {}, types_load: dict[str, Any] = {}):
        self.types_dump = types_dump
        self.types_load = types_load

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
