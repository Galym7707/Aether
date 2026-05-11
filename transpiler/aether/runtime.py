"""Aether v0.1 runtime — the Python implementation of stdlib functions
and the constructors for Result/Option/Unions.

All Aether identifiers are mangled to avoid colliding with Python builtins:

    foo       -> _ae_foo
    foo?      -> _ae_foo_q
    foo!      -> _ae_foo_e

The emitter rewrites every identifier through `mangle()`. The runtime
exposes its functions under their mangled names so the emitted code
just calls them directly.
"""

from __future__ import annotations
from datetime import datetime, timezone
from fnmatch import fnmatchcase
import random as _py_random
from typing import Any, Callable, Dict, List, Tuple, Optional


# ----------------------------------------------------------------------
# Identifier mangling
# ----------------------------------------------------------------------

PY_RESERVED = {
    "False", "None", "True", "and", "as", "assert", "async", "await", "break",
    "class", "continue", "def", "del", "elif", "else", "except", "finally",
    "for", "from", "global", "if", "import", "in", "is", "lambda", "nonlocal",
    "not", "or", "pass", "raise", "return", "try", "while", "with", "yield",
    "match", "case",
}


def mangle(name: str) -> str:
    base = name
    suffix = ""
    if base.endswith("?"):
        base, suffix = base[:-1], "_q"
    elif base.endswith("!"):
        base, suffix = base[:-1], "_e"
    return f"_ae_{base}{suffix}"


# ----------------------------------------------------------------------
# Effect tracking (test mode)
# ----------------------------------------------------------------------

class EffectTracker:
    """Records every effect invocation; can be checked against declared sets."""

    def __init__(self, strict: bool = False):
        self.strict = strict
        self.allowed: List[Any] = []
        self.observed: List[Any] = []

    def push_frame(self, declared: List[Any]):
        self.allowed.append(declared)

    def pop_frame(self):
        self.allowed.pop()

    def record(self, effect):
        observed_path, _, _ = self._split_effect(effect)
        self.observed.append(effect)
        if self.strict and self.allowed:
            top = self.allowed[-1]
            if any(self._split_effect(declared)[0] == ("pure",) for declared in top):
                # pure means no effects allowed
                from .diagnostics import AetherError, Diagnostic, Position
                raise AetherError(Diagnostic(
                    code="E0501", category="effect", severity="error",
                    message=(f"effect {self._effect_name(effect)} performed in "
                             "a function declared 'pure'"),
                    position=Position(0, 0),
                    suggestion="declare this effect in the function's effects clause",
                    confidence=1.0,
                ))
            # match-prefix check
            ok = any(self._prefix_match(declared, effect) for declared in top)
            if not ok:
                from .diagnostics import AetherError, Diagnostic, Position
                raise AetherError(Diagnostic(
                    code="E0502", category="effect", severity="error",
                    message=f"effect {self._effect_name(effect)} not in declared effect set",
                    position=Position(0, 0),
                    suggestion=(f"add '{'.'.join(observed_path)}' to the "
                                "function's effects clause"),
                    confidence=1.0,
                ))

    @staticmethod
    def _split_effect(effect):
        if (
            isinstance(effect, tuple)
            and len(effect) == 2
            and isinstance(effect[0], tuple)
            and (effect[1] is None or isinstance(effect[1], str))
        ):
            return tuple(effect[0]), effect[1], True
        return tuple(effect), None, False

    @staticmethod
    def _has_glob(pattern: str) -> bool:
        return any(ch in pattern for ch in "*?[")

    @classmethod
    def _trailing_star_prefix(cls, pattern: str):
        if not pattern.endswith("*"):
            return None
        prefix = pattern[:-1]
        if cls._has_glob(prefix):
            return None
        return prefix

    @classmethod
    def _glob_covers(cls, declared_pattern: str, observed_pattern: str) -> bool:
        if declared_pattern == observed_pattern:
            return True
        if not cls._has_glob(observed_pattern):
            return fnmatchcase(observed_pattern, declared_pattern)
        declared_prefix = cls._trailing_star_prefix(declared_pattern)
        observed_prefix = cls._trailing_star_prefix(observed_pattern)
        if declared_prefix is None or observed_prefix is None:
            return False
        return observed_prefix.startswith(declared_prefix)

    @classmethod
    def _effect_name(cls, effect) -> str:
        path, arg, has_arg = cls._split_effect(effect)
        name = ".".join(path)
        if has_arg:
            if arg is None:
                return f"{name}(?)"
            escaped = arg.replace("\\", "\\\\").replace('"', '\\"')
            return f'{name}("{escaped}")'
        return name

    @classmethod
    def _prefix_match(cls, declared, observed) -> bool:
        declared_path, declared_arg, declared_has_arg = cls._split_effect(declared)
        observed_path, observed_arg, observed_has_arg = cls._split_effect(observed)
        if declared_path != observed_path:
            return False
        if not declared_has_arg:
            if observed_has_arg:
                return declared_path == ("net", "fetch")
            return True
        if not observed_has_arg:
            return False
        if declared_arg is None or observed_arg is None:
            return False
        if declared_path != ("net", "fetch"):
            return declared_arg == observed_arg
        return cls._glob_covers(declared_arg, observed_arg)


_TRACKER = EffectTracker(strict=False)
_CALLSITE_STACK: List[Tuple[int, int]] = []
_DETERMINISTIC = False
_RNG = _py_random.Random(0)
_FIXED_EPOCH_MILLIS: Optional[int] = None


def configure_deterministic_runtime(
    *,
    deterministic: bool = False,
    seed: int = 0,
    fixed_time: Optional[str] = None,
):
    """Configure deterministic stdlib hooks for one CLI/SDK execution."""
    global _DETERMINISTIC, _RNG, _FIXED_EPOCH_MILLIS
    _DETERMINISTIC = bool(deterministic)
    _RNG = _py_random.Random(seed)
    if fixed_time is not None:
        _FIXED_EPOCH_MILLIS = _parse_fixed_time(fixed_time)
    elif _DETERMINISTIC:
        _FIXED_EPOCH_MILLIS = 0
    else:
        _FIXED_EPOCH_MILLIS = None


def _parse_fixed_time(value: str) -> int:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def set_effect_strict(strict: bool):
    _TRACKER.strict = strict


def push_effect_frame(declared):
    _TRACKER.push_frame(declared)


def pop_effect_frame():
    _TRACKER.pop_frame()


def record_effect(*path):
    _TRACKER.record(path)


def record_effect_arg(arg, *path):
    _TRACKER.record((tuple(path), arg))


def _aether_call(fn, line: int, column: int, *args):
    _CALLSITE_STACK.append((line, column))
    try:
        return fn(*args)
    finally:
        _CALLSITE_STACK.pop()


def _current_callsite():
    return _CALLSITE_STACK[-1] if _CALLSITE_STACK else None


# ----------------------------------------------------------------------
# Constructors for built-in unions
# ----------------------------------------------------------------------

def _make_union(tag: str, *args):
    """Tagged-union value: a tuple where [0] is the tag, [1:] are payloads."""
    return (tag,) + args


# These are exposed at the AST level as `Some(x)`, `None()`, `Ok(x)`, `Err(e)`.
def _ae_Some(x):                       return _make_union("Some", x)
def _ae_None():                        return _make_union("None")
def _ae_Ok(x):                         return _make_union("Ok", x)
def _ae_Err(e):                        return _make_union("Err", e)


# ----------------------------------------------------------------------
# Stdlib: List
# ----------------------------------------------------------------------

def _ae_length(xs):
    if isinstance(xs, str):
        return len(xs)
    return len(xs)

def _ae_empty_q(xs):                   return len(xs) == 0
def _ae_head(xs):                      return _ae_Some(xs[0]) if xs else _ae_None()
def _ae_tail(xs):
    if not xs:
        from .diagnostics import AetherError, Diagnostic, Position
        raise AetherError(Diagnostic(code="E0301", category="contract",
                                     severity="error",
                                     message="tail of empty list",
                                     position=Position(0, 0)))
    return list(xs[1:])

def _ae_append(xs, x):                 return list(xs) + [x]
def _ae_prepend(x, xs):                return [x] + list(xs)
def _ae_concat(xs, ys):                return list(xs) + list(ys)

def _aether_index(coll, index, line: int = 0, column: int = 0):
    from .diagnostics import AetherError, Diagnostic, Position
    if not isinstance(index, int) or isinstance(index, bool):
        raise AetherError(Diagnostic(
            code="INDEX_TYPE_INVALID",
            category="runtime",
            severity="error",
            message=f"index has type {type(index).__name__}; expected Int",
            position=Position(line, column),
            suggestion="use an Int index expression",
            confidence=1.0,
            extra={"expected": "Int", "actual": type(index).__name__},
        ))
    if index < 0:
        raise AetherError(Diagnostic(
            code="INDEX_NEGATIVE_UNSUPPORTED",
            category="runtime",
            severity="error",
            message=f"Aether does not support negative indexing; got index {index}.",
            position=Position(line, column),
            suggestion="check `index >= 0` before indexing",
            confidence=1.0,
            extra={
                "expected": "index >= 0",
                "actual": str(index),
                "actual_index": index,
            },
        ))
    if isinstance(coll, (list, tuple, str)):
        if index >= len(coll):
            valid_range = "empty" if len(coll) == 0 else f"0..{len(coll) - 1}"
            raise AetherError(Diagnostic(
                code="INDEX_OUT_OF_BOUNDS_RUNTIME",
                category="runtime",
                severity="error",
                message=f"index {index} is out of bounds for length {len(coll)}",
                position=Position(line, column),
                suggestion="ensure the index is less than length(value)",
                confidence=1.0,
                extra={
                    "expected": valid_range,
                    "actual": str(index),
                    "valid_range": valid_range,
                    "actual_index": index,
                },
            ))
        return coll[index]
    raise AetherError(Diagnostic(
        code="INDEX_TARGET_INVALID",
        category="runtime",
        severity="error",
        message=f"cannot index value of type {type(coll).__name__}",
        position=Position(line, column),
        suggestion="index only lists, strings, or tuple-backed union values",
        confidence=1.0,
        extra={"actual": type(coll).__name__},
    ))

def _ae_get(coll, key):
    if isinstance(coll, dict):
        return _ae_Some(coll[key]) if key in coll else _ae_None()
    if isinstance(coll, list):
        if 0 <= key < len(coll):
            return _ae_Some(coll[key])
        return _ae_None()
    raise TypeError(f"_ae_get: unsupported collection type {type(coll)}")

def _ae_inBounds(xs, index):
    return isinstance(index, int) and not isinstance(index, bool) and 0 <= index < len(xs)

def _ae_validSliceBounds(xs, start, end):
    return (
        isinstance(start, int)
        and not isinstance(start, bool)
        and isinstance(end, int)
        and not isinstance(end, bool)
        and 0 <= start <= end <= len(xs)
    )

def _ae_safeAt(xs, index):
    if _ae_inBounds(xs, index):
        return _ae_Some(xs[index])
    return _ae_None()

def _ae_updateAt(xs, index, value):
    if not _ae_inBounds(xs, index):
        return _ae_Err("index out of bounds")
    out = list(xs)
    out[index] = value
    return _ae_Ok(out)

def _ae_safeSlice(xs, start, end):
    if not _ae_validSliceBounds(xs, start, end):
        return _ae_Err("slice bounds out of range")
    return _ae_Ok(list(xs)[start:end])

def _ae_map(xs, f):                    return [f(x) for x in xs]
def _ae_filter(xs, p):                 return [x for x in xs if p(x)]

def _ae_foldLeft(xs, z, f):
    a = z
    for x in xs:
        a = f(a, x)
    return a

def _ae_reverse(xs):                   return list(reversed(xs))
def _ae_range(lo, hi):                 return list(range(lo, hi))

def _aggregate_error(code: str, message: str, line: int, column: int, hint: str):
    from .diagnostics import AetherError, Diagnostic, Position
    raise AetherError(Diagnostic(
        code=code,
        category="runtime",
        severity="error",
        message=message,
        position=Position(line, column),
        suggestion=hint,
        confidence=1.0,
    ))

def _ensure_int_list(name: str, xs, line: int, column: int):
    if not isinstance(xs, list):
        _aggregate_error(
            "AGGREGATE_LIST_TYPE_RUNTIME",
            f"{name} expects List<Int>, got {type(xs).__name__}",
            line,
            column,
            f"pass a List<Int> to {name}",
        )
    for value in xs:
        if not isinstance(value, int) or isinstance(value, bool):
            _aggregate_error(
                "AGGREGATE_ELEMENT_TYPE_RUNTIME",
                f"{name} expects List<Int>, but an element has type {type(value).__name__}",
                line,
                column,
                f"pass only Int values to {name}",
            )
    return xs

def _ae_sum(xs, *, line: int = 0, column: int = 0):
    values = _ensure_int_list("sum", xs, line, column)
    if not values:
        _aggregate_error(
            "AGGREGATE_EMPTY_LIST_RUNTIME",
            "sum requires a non-empty List<Int>",
            line,
            column,
            "guard with `requires length(xs) > 0` before calling sum",
        )
    return sum(values)

def _ae_min(a, b=None, *, line: int = 0, column: int = 0):
    if b is not None:
        return min(a, b)
    values = _ensure_int_list("min", a, line, column)
    if not values:
        _aggregate_error(
            "AGGREGATE_EMPTY_LIST_RUNTIME",
            "min requires a non-empty List<Int>",
            line,
            column,
            "guard with `requires length(xs) > 0` before calling min",
        )
    return min(values)

def _ae_max(a, b=None, *, line: int = 0, column: int = 0):
    if b is not None:
        return max(a, b)
    values = _ensure_int_list("max", a, line, column)
    if not values:
        _aggregate_error(
            "AGGREGATE_EMPTY_LIST_RUNTIME",
            "max requires a non-empty List<Int>",
            line,
            column,
            "guard with `requires length(xs) > 0` before calling max",
        )
    return max(values)

def _ae_sorted(xs):
    values = _ensure_int_list("sorted", xs, 0, 0)
    return all(values[i - 1] <= values[i] for i in range(1, len(values)))

def _ae_permutation(xs, ys):
    if not isinstance(xs, list) or not isinstance(ys, list):
        return False
    if len(xs) != len(ys):
        return False
    remaining = list(ys)
    for item in xs:
        try:
            idx = remaining.index(item)
        except ValueError:
            return False
        remaining.pop(idx)
    return not remaining


def _aether_check_loop_invariant(ok: bool, line: int = 0, column: int = 0, expr: str = ""):
    if ok:
        return
    from .diagnostics import AetherError, Diagnostic, Position
    raise AetherError(Diagnostic(
        code="LOOP_INVARIANT_FAILED",
        category="contract",
        severity="error",
        message=f"loop invariant failed: {expr}",
        position=Position(line, column),
        suggestion="strengthen the loop body or weaken the invariant so it holds before and after every iteration",
        confidence=1.0,
        extra={"contract_kind": "loop invariant", "contract": expr},
    ))


def _aether_check_loop_variant(prev, next_value, line: int = 0, column: int = 0, expr: str = ""):
    if not isinstance(prev, (int, float)) or isinstance(prev, bool):
        from .diagnostics import AetherError, Diagnostic, Position
        raise AetherError(Diagnostic(
            code="LOOP_VARIANT_TYPE_RUNTIME",
            category="runtime",
            severity="error",
            message=f"loop variant must be numeric before the iteration: {expr}",
            position=Position(line, column),
            suggestion="use an Int arithmetic expression for `variant`",
            confidence=1.0,
            extra={"expected": "numeric", "actual": type(prev).__name__, "contract": expr},
        ))
    if not isinstance(next_value, (int, float)) or isinstance(next_value, bool):
        from .diagnostics import AetherError, Diagnostic, Position
        raise AetherError(Diagnostic(
            code="LOOP_VARIANT_TYPE_RUNTIME",
            category="runtime",
            severity="error",
            message=f"loop variant must be numeric after the iteration: {expr}",
            position=Position(line, column),
            suggestion="use an Int arithmetic expression for `variant`",
            confidence=1.0,
            extra={"expected": "numeric", "actual": type(next_value).__name__, "contract": expr},
        ))
    if next_value < prev:
        return
    from .diagnostics import AetherError, Diagnostic, Position
    raise AetherError(Diagnostic(
        code="LOOP_VARIANT_NOT_DECREASING",
        category="contract",
        severity="error",
        message=f"loop variant did not strictly decrease: {expr}",
        position=Position(line, column),
        suggestion="update loop variables so `variant` is smaller after each iteration",
        confidence=1.0,
        extra={
            "contract_kind": "loop variant",
            "contract": expr,
            "previous_value": prev,
            "actual_value": next_value,
        },
    ))


# ----------------------------------------------------------------------
# Stdlib: Map
# ----------------------------------------------------------------------

def _ae_size(s):                       return len(s)
def _ae_set(m, k, v):
    new = dict(m)
    new[k] = v
    return new

def _aether_record_update(record, updates, line: int = 0, column: int = 0):
    if not isinstance(record, dict):
        from .diagnostics import AetherError, Diagnostic, Position
        raise AetherError(Diagnostic(
            code="RECORD_UPDATE_TARGET_RUNTIME",
            category="runtime",
            severity="error",
            message=f"record update target must be a record, got {type(record).__name__}",
            position=Position(line, column),
            suggestion="use `value { field = newValue }` only with record values",
            confidence=1.0,
            extra={"expected": "record", "actual": type(record).__name__},
        ))
    unknown = [name for name in updates if name not in record]
    if unknown:
        from .diagnostics import AetherError, Diagnostic, Position
        raise AetherError(Diagnostic(
            code="RECORD_UPDATE_FIELD_UNKNOWN_RUNTIME",
            category="runtime",
            severity="error",
            message=f"record update references unknown field {unknown[0]!r}",
            position=Position(line, column),
            suggestion="update only fields declared on the record",
            confidence=1.0,
            extra={"field": unknown[0]},
        ))
    new = dict(record)
    new.update(updates)
    return new

def _ae_remove(m, k):
    new = dict(m)
    new.pop(k, None)
    return new

def _ae_has_q(m, k):                   return k in m
def _ae_keys(m):                       return list(m.keys())
def _ae_values(m):                     return list(m.values())


# ----------------------------------------------------------------------
# Stdlib: Set (immutable, frozenset-backed)
# ----------------------------------------------------------------------

def _ae_add(s, x):                     return frozenset(s | {x})
def _ae_contains_q(s, x):              return x in s


# ----------------------------------------------------------------------
# Stdlib: String
# ----------------------------------------------------------------------

def _ae_slice(s, lo, hi):              return s[lo:hi]
def _ae_split(s, sep):                 return s.split(sep) if sep else list(s)
def _ae_join(parts, sep):              return sep.join(parts)
def _ae_trim(s):                       return s.strip()
def _ae_toLower(s):                    return s.lower()
def _ae_toUpper(s):                    return s.upper()
def _ae_replace(s, frm, to):           return s.replace(frm, to)
def _ae_startsWith_q(s, p):            return s.startswith(p)
def _ae_endsWith_q(s, p):              return s.endswith(p)

def _ae_parseInt(s):
    try:
        return _ae_Ok(int(s))
    except (ValueError, TypeError):
        return _ae_Err(f"could not parse Int: {s!r}")

def _ae_parseFloat(s):
    try:
        return _ae_Ok(float(s))
    except (ValueError, TypeError):
        return _ae_Err(f"could not parse Float: {s!r}")

def _ae_intToString(n):                return str(n)


# ----------------------------------------------------------------------
# Stdlib: IO
# ----------------------------------------------------------------------

def _ae_print(s):
    record_effect("log")
    print(s)
    return None  # Unit

def _ae_readLine():
    record_effect("log")
    try:
        return _ae_Ok(input())
    except EOFError:
        return _ae_Err("EOF")

def _ae_readFile(path):
    record_effect("fs", "read")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return _ae_Ok(f.read())
    except OSError as e:
        return _ae_Err(str(e))

def _ae_writeFile(path, contents):
    record_effect("fs", "write")
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(contents)
        return _ae_Ok(None)
    except OSError as e:
        return _ae_Err(str(e))


# ----------------------------------------------------------------------
# Stdlib: Time / Hash / Math
# ----------------------------------------------------------------------

def _ae_now():
    record_effect("time", "now")
    if _FIXED_EPOCH_MILLIS is not None:
        return {"_kind": "Instant", "epochMillis": _FIXED_EPOCH_MILLIS}
    import time
    return {"_kind": "Instant", "epochMillis": int(time.time() * 1000)}

def _ae_random():
    record_effect("random")
    if _DETERMINISTIC:
        return _RNG.randrange(0, 2147483648)
    return _py_random.randrange(0, 2147483648)

def _ae_sha256(b):
    import hashlib
    return hashlib.sha256(b).digest()

def _ae_sha1(b):
    import hashlib
    return hashlib.sha1(b).digest()

def _ae_md5(b):
    import hashlib
    return hashlib.md5(b).digest()

def _ae_abs(x):                        return abs(x)
def _ae_floor(x):                      import math; return math.floor(x)
def _ae_ceil(x):                       import math; return math.ceil(x)
def _ae_pow(a, b):                     return a ** b

def _ae_sqrt(x):
    if x < 0:
        from .diagnostics import AetherError, Diagnostic, Position
        raise AetherError(Diagnostic(code="E0301", category="contract",
                                     severity="error",
                                     message="sqrt of negative",
                                     position=Position(0, 0)))
    import math; return math.sqrt(x)


# ----------------------------------------------------------------------
# Result / Option helpers
# ----------------------------------------------------------------------

def _ae_isOk_q(r):                     return r[0] == "Ok"
def _ae_isErr_q(r):                    return r[0] == "Err"
def _ae_isOk(r):                       return _ae_isOk_q(r)
def _ae_isErr(r):                      return _ae_isErr_q(r)

def _ae_isSome_q(o):                   return o[0] == "Some"
def _ae_isNone_q(o):                   return o[0] == "None"
def _ae_isSome(o):                     return _ae_isSome_q(o)
def _ae_isNone(o):                     return _ae_isNone_q(o)

def _ae_unwrapOr(value, default):
    return value[1] if value[0] in {"Some", "Ok"} else default

def _ae_unwrapOrResult(r, default):
    return r[1] if r[0] == "Ok" else default

def _ae_unwrapOrElse(o, default):      return o[1] if o[0] == "Some" else default

def _ae_mapOption(o, f):
    return _ae_Some(f(o[1])) if o[0] == "Some" else _ae_None()

def _ae_andThenOption(o, f):
    return f(o[1]) if o[0] == "Some" else _ae_None()

def _ae_mapResult(r, f):
    return _ae_Ok(f(r[1])) if r[0] == "Ok" else r

def _ae_mapErr(r, f):
    return _ae_Err(f(r[1])) if r[0] == "Err" else r

def _ae_andThenResult(r, f):
    return f(r[1]) if r[0] == "Ok" else r

def _ae_expectSome(o, message: str, line: int = 0, column: int = 0):
    if o[0] == "Some":
        return o[1]
    from .diagnostics import AetherError, Diagnostic, Position
    raise AetherError(Diagnostic(
        code="EXPECT_SOME_FAILED",
        category="runtime",
        severity="error",
        message=message,
        position=Position(line, column),
        suggestion="handle None() with match or use unwrapOr for a fallback value",
        confidence=1.0,
        extra={"actual_case": o[0], "expected": "Some", "actual": o[0]},
    ))

def _ae_expectOk(r, message: str, line: int = 0, column: int = 0):
    if r[0] == "Ok":
        return r[1]
    from .diagnostics import AetherError, Diagnostic, Position
    raise AetherError(Diagnostic(
        code="EXPECT_OK_FAILED",
        category="runtime",
        severity="error",
        message=message,
        position=Position(line, column),
        suggestion="handle Err(...) with match or use unwrapOrResult for a fallback value",
        confidence=1.0,
        extra={"actual_case": r[0], "expected": "Ok", "actual": r[0], "error": r[1] if len(r) > 1 else None},
    ))


def _aether_match_failed(value, line: int = 0, column: int = 0):
    from .diagnostics import AetherError, Diagnostic, Position
    actual_case = value[0] if isinstance(value, tuple) and value else type(value).__name__
    raise AetherError(Diagnostic(
        code="MATCH_NON_EXHAUSTIVE_RUNTIME",
        category="runtime",
        severity="error",
        message=f"non-exhaustive match reached runtime for case {actual_case}",
        position=Position(line, column),
        suggestion="add the missing match case or a `_` wildcard arm",
        confidence=1.0,
        extra={"actual_case": actual_case},
    ))


# ----------------------------------------------------------------------
# Contract assertion helper
# ----------------------------------------------------------------------

def _ae_assert_contract(
    cond: bool,
    kind: str,
    expr: str,
    fn: str,
    args=None,
    line: int = 0,
    column: int = 0,
):
    """Raise a structured contract error if `cond` is False."""
    if cond:
        return
    from .diagnostics import AetherError, Diagnostic, Position
    callsite = _current_callsite()
    extra = {
        "function": fn,
        "contract_kind": kind,
        "contract": expr,
        "contract_line": line,
        "contract_column": column,
        "args": args or {},
        "actual_value": args or {},
    }
    if callsite is not None:
        extra["callsite_line"] = callsite[0]
        extra["callsite_column"] = callsite[1]
    raise AetherError(Diagnostic(
        code="E0301", category="contract", severity="error",
        message=f"{kind} clause failed in {fn}: {expr}",
        position=Position(line, column),
        extra=extra,
        confidence=1.0,
        suggestion=f"check the {kind} contract and inputs to {fn}",
    ))


def _ae_check_refinement(
    value,
    predicate_fn,
    type_name: str,
    binding_name: str,
    fn: str = "?",
    line: int = 0,
    column: int = 0,
):
    """Boundary-crossing check for a refinement type.

    Called at function entry for any parameter whose declared type is a
    refinement (e.g. `type PositiveInt = Int where self > 0`). The
    predicate is compiled into a lambda taking the candidate as `_ae_self`.
    """
    try:
        ok = bool(predicate_fn(value))
    except Exception as e:
        from .diagnostics import AetherError, Diagnostic, Position
        callsite = _current_callsite()
        extra = {
            "function": fn,
            "argument": binding_name,
            "actual_value": repr(value)[:80],
            "type_name": type_name,
            "contract_line": line,
            "contract_column": column,
        }
        if callsite is not None:
            extra["callsite_line"] = callsite[0]
            extra["callsite_column"] = callsite[1]
        raise AetherError(Diagnostic(
            code="E0303", category="refinement", severity="error",
            message=(f"refinement predicate for {type_name} raised "
                     f"{type(e).__name__} on value bound to {binding_name!r}"),
            position=Position(line, column),
            suggestion=("ensure refinement predicates are total over their base type "
                        "(handle every possible input)"),
            confidence=1.0,
            extra=extra,
        )) from e
    if ok:
        return
    from .diagnostics import AetherError, Diagnostic, Position
    callsite = _current_callsite()
    extra = {
        "function": fn,
        "argument": binding_name,
        "actual_value": repr(value)[:80],
        "type_name": type_name,
        "value_repr": repr(value)[:80],
        "contract_line": line,
        "contract_column": column,
    }
    if callsite is not None:
        extra["callsite_line"] = callsite[0]
        extra["callsite_column"] = callsite[1]
    raise AetherError(Diagnostic(
        code="E0302", category="refinement", severity="error",
        message=(f"value bound to {binding_name!r} fails refinement "
                 f"{type_name} in {fn}"),
        position=Position(line, column),
        suggestion=(f"caller must ensure {binding_name} satisfies "
                    f"{type_name}'s refinement clause"),
        confidence=1.0,
        extra=extra,
    ))


# ----------------------------------------------------------------------
# Build the global namespace dict the emitter injects into exec()
# ----------------------------------------------------------------------

def build_namespace() -> Dict[str, Any]:
    g: Dict[str, Any] = {}
    for name, val in globals().items():
        if name.startswith("_ae_") or name in {
            "_make_union", "_TRACKER",
            "push_effect_frame", "pop_effect_frame",
            "record_effect", "set_effect_strict",
            "record_effect_arg", "_aether_index", "_aether_call",
            "_aether_match_failed", "_aether_check_loop_invariant",
            "_aether_check_loop_variant", "_aether_record_update",
        }:
            g[name] = val
    g["_ae_time"] = {"now": _ae_now}
    return g
