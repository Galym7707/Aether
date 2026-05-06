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
        self.allowed: List[Tuple[str, ...]] = []
        self.observed: List[Tuple[str, ...]] = []

    def push_frame(self, declared: List[Tuple[str, ...]]):
        self.allowed.append(declared)

    def pop_frame(self):
        self.allowed.pop()

    def record(self, path: Tuple[str, ...]):
        self.observed.append(path)
        if self.strict and self.allowed:
            top = self.allowed[-1]
            if ("pure",) in top:
                # pure means no effects allowed
                from .diagnostics import AetherError, Diagnostic, Position
                raise AetherError(Diagnostic(
                    code="E0501", category="effect", severity="error",
                    message=f"effect {'.'.join(path)} performed in a function declared 'pure'",
                    position=Position(0, 0),
                    suggestion="declare this effect in the function's effects clause",
                    confidence=1.0,
                ))
            # match-prefix check
            ok = any(self._prefix_match(declared, path) for declared in top)
            if not ok:
                from .diagnostics import AetherError, Diagnostic, Position
                raise AetherError(Diagnostic(
                    code="E0502", category="effect", severity="error",
                    message=f"effect {'.'.join(path)} not in declared effect set",
                    position=Position(0, 0),
                    suggestion=f"add '{'.'.join(path)}' to the function's effects clause",
                    confidence=1.0,
                ))

    @staticmethod
    def _prefix_match(declared: Tuple[str, ...], observed: Tuple[str, ...]) -> bool:
        if len(declared) > len(observed):
            return False
        return declared == observed[:len(declared)]


_TRACKER = EffectTracker(strict=False)


def set_effect_strict(strict: bool):
    _TRACKER.strict = strict


def push_effect_frame(declared):
    _TRACKER.push_frame(declared)


def pop_effect_frame():
    _TRACKER.pop_frame()


def record_effect(*path):
    _TRACKER.record(path)


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

def _ae_get(coll, key):
    if isinstance(coll, dict):
        return _ae_Some(coll[key]) if key in coll else _ae_None()
    if isinstance(coll, list):
        if 0 <= key < len(coll):
            return _ae_Some(coll[key])
        return _ae_None()
    raise TypeError(f"_ae_get: unsupported collection type {type(coll)}")

def _ae_map(xs, f):                    return [f(x) for x in xs]
def _ae_filter(xs, p):                 return [x for x in xs if p(x)]

def _ae_foldLeft(xs, z, f):
    a = z
    for x in xs:
        a = f(a, x)
    return a

def _ae_reverse(xs):                   return list(reversed(xs))
def _ae_range(lo, hi):                 return list(range(lo, hi))


# ----------------------------------------------------------------------
# Stdlib: Map
# ----------------------------------------------------------------------

def _ae_size(s):                       return len(s)
def _ae_set(m, k, v):
    new = dict(m)
    new[k] = v
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
    import time
    return {"_kind": "Instant", "epochMillis": int(time.time() * 1000)}

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
def _ae_min(a, b):                     return min(a, b)
def _ae_max(a, b):                     return max(a, b)
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
def _ae_unwrapOr(r, default):          return r[1] if r[0] == "Ok" else default

def _ae_isSome_q(o):                   return o[0] == "Some"
def _ae_isNone_q(o):                   return o[0] == "None"
def _ae_unwrapOrElse(o, default):      return o[1] if o[0] == "Some" else default


# ----------------------------------------------------------------------
# Contract assertion helper
# ----------------------------------------------------------------------

def _ae_assert_contract(cond: bool, kind: str, expr: str, fn: str, args=None):
    """Raise a structured contract error if `cond` is False."""
    if cond:
        return
    from .diagnostics import AetherError, Diagnostic, Position
    raise AetherError(Diagnostic(
        code="E0301", category="contract", severity="error",
        message=f"{kind} clause failed in {fn}: {expr}",
        position=Position(0, 0),
        extra={"args": args or {}},
        confidence=1.0,
        suggestion=f"check inputs to {fn}",
    ))


def _ae_check_refinement(value, predicate_fn, type_name: str, binding_name: str):
    """Boundary-crossing check for a refinement type.

    Called at function entry for any parameter whose declared type is a
    refinement (e.g. `type PositiveInt = Int where self > 0`). The
    predicate is compiled into a lambda taking the candidate as `_ae_self`.
    """
    try:
        ok = bool(predicate_fn(value))
    except Exception as e:
        from .diagnostics import AetherError, Diagnostic, Position
        raise AetherError(Diagnostic(
            code="E0303", category="refinement", severity="error",
            message=(f"refinement predicate for {type_name} raised "
                     f"{type(e).__name__} on value bound to {binding_name!r}"),
            position=Position(0, 0),
            suggestion=("ensure refinement predicates are total over their base type "
                        "(handle every possible input)"),
            confidence=1.0,
        )) from e
    if ok:
        return
    from .diagnostics import AetherError, Diagnostic, Position
    raise AetherError(Diagnostic(
        code="E0302", category="refinement", severity="error",
        message=(f"value bound to {binding_name!r} fails refinement "
                 f"{type_name}"),
        position=Position(0, 0),
        suggestion=(f"caller must ensure {binding_name} satisfies "
                    f"{type_name}'s refinement clause"),
        confidence=1.0,
        extra={"value_repr": repr(value)[:80]},
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
        }:
            g[name] = val
    return g
