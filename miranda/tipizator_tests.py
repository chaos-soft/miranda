#!/usr/bin/env python3
from datetime import date, datetime
from decimal import Decimal
import json

from tipizator import Tipizator

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
    types_dump = {
        'd': str,
        'e': str,
        'f': str,
    }
    types_load = {
        'd': date.fromisoformat,
        'e': Decimal,
        'f': datetime.fromisoformat,
    }
    tipizator = Tipizator(types_dump, types_load)

    str1 = tipizator.dumps(test1)
    str2 = json.dumps(test2, **tipizator.dump_kwargs)
    assert str1 == str2

    test1_ = tipizator.loads(str1)
    assert test1 == test1_
