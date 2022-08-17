# This flow is based on https://pypi.org/project/json-logic/
# which supposed to be a Python implementation of the jsonLogic JS library:
# https://github.com/jwadhams/json-logic-js

import sys
from functools import reduce
from typing import Optional

OPERATIONS = {
    "==": (lambda a, b: a == b),
    "===": (lambda a, b: a is b),
    "!=": (lambda a, b: a != b),
    "!==": (lambda a, b: a is not b),
    ">": (lambda a, b: a > b),
    ">=": (lambda a, b: a >= b),
    "<": (lambda a, b, c=None: a < b if (c is None) else (a < b) and (b < c)),
    "<=": (lambda a, b, c=None: a <= b if (c is None) else (a <= b) and (b <= c)),
    "!": (lambda a: not a),
    "%": (lambda a, b: a % b),
    "and": (lambda *args: reduce(lambda total, arg: total and arg, args, True)),
    "or": (lambda *args: reduce(lambda total, arg: total or arg, args, False)),
    "?:": (lambda a, b, c: b if a else c),
    "log": (lambda a: sys.stdout.write(str(a))),
    "in": (lambda a, b: a in b if "__contains__" in dir(b) else False),
    "cat": (lambda *args: "".join(args)),
    "+": (lambda *args: reduce(lambda total, arg: total + float(arg), args, 0.0)),
    "*": (lambda *args: reduce(lambda total, arg: total * float(arg), args, 1.0)),
    "-": (lambda a, b=None: -a if b is None else a - b),
    "/": (lambda a, b=None: a if b is None else float(a) / float(b)),
    "min": (lambda *args: min(args)),
    "max": (lambda *args: max(args)),
    "count": (lambda *args: sum(1 if a else 0 for a in args)),
}


def _get_value(_data, key):
    if type(_data) == dict:
        if key in _data.keys():
            return _data[key]
        else:
            raise ValueError(f"Invalid context: key '{key}' not found")
    if type(_data) in [list, tuple] and str(key).lstrip("-").isdigit():
        try:
            return _data[int(key)]
        except IndexError as e:
            raise ValueError(f"Invalid context: key '{key}': {e}")


def evaluate(tests, data: Optional[dict]):
    # You've recursed to a primitive, stop!
    if tests is None or type(tests) != dict:
        return tests

    data = data or {}

    op = next(iter(tests))
    values = tests[op]

    OPERATIONS["var"] = lambda a: reduce(
        _get_value,
        str(a).split("."),
        data,
    )

    if op not in OPERATIONS:
        raise RuntimeError("Unrecognized operation %s" % op)

    # Easy syntax for unary operators, like {"var": "x"} instead of strict
    # {"var": ["x"]}
    if type(values) not in [list, tuple]:
        values = [values]

    # Recursion!
    values = map(lambda val: evaluate(val, data), values)

    return OPERATIONS[op](*values)
