"""Property-based parser fuzzer (S-008).

Three corpus modes:

  --mode random       Pure-random byte sequences over a slightly-restricted
                      ASCII alphabet (printable + space + newline). Most are
                      garbage; the parser must reject them with a structured
                      ParseError, never crash, never silently accept.

  --mode mutate       Take valid Aether programs from reference/ and bench/,
                      apply small mutations (drop char, duplicate char, swap
                      chars, insert random char), and check the same
                      properties as --mode random plus: if the mutated
                      program parses, emitting + compiling it must also not
                      crash.

  --mode tokens       Tokenize a valid program, then perturb the token
                      stream (drop, duplicate, swap), reconstruct source,
                      and parse. Structured diagnostics required on
                      rejection.

The invariant the parser must satisfy:
  - Either parse() returns a dict, OR raises AetherError (structured), OR
    the harness times out (we cap each parse to 1 second).
  - Never any other exception (TypeError, RecursionError uncaught, etc.).
  - Never silently accepts and emits broken Python.
  - Every accepted AST must print to canonical Aether source that reparses to
    the same AST after source-position metadata is stripped.

Run as:
  python3 -B scripts/fuzz_parser.py --rounds 500 --mode random
  python3 -B scripts/fuzz_parser.py --rounds 500 --mode mutate
  python3 -B scripts/fuzz_parser.py --rounds 500 --mode tokens
"""

from __future__ import annotations
import argparse
import os
import random
import signal
import string
import sys
import time
from typing import List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "transpiler"))

from aether.diagnostics import AetherError       # noqa: E402
from aether.parser import parse                  # noqa: E402
from aether.lexer import tokenize, KEYWORDS      # noqa: E402
from aether.emitter import emit                  # noqa: E402
from aether.printer import print_ast, strip_positions  # noqa: E402


# Each parse is wrapped in SIGALRM with this budget.
_PARSE_TIMEOUT_S = 1


class _ParseTimeout(Exception):
    pass


def _alarm(signum, frame):
    raise _ParseTimeout()


def safe_parse(src: str) -> dict:
    """Returns the AST dict if parse succeeds, raises AetherError or
    _ParseTimeout otherwise. ANY OTHER EXCEPTION = invariant violation."""
    have_alarm = hasattr(signal, "SIGALRM")
    if have_alarm:
        prev = signal.signal(signal.SIGALRM, _alarm)
        signal.setitimer(signal.ITIMER_REAL, _PARSE_TIMEOUT_S)
    try:
        return parse(src, "<fuzz>")
    finally:
        if have_alarm:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, prev)


# ----------------------------------------------------------------------
# Corpus generators
# ----------------------------------------------------------------------

_RANDOM_ALPHA = string.ascii_letters + string.digits + " \t\n" + "(){}[]<>+-*/%=:;,.\"'?!_"


def gen_random(rng: random.Random, max_len: int = 200) -> str:
    n = rng.randint(0, max_len)
    return "".join(rng.choice(_RANDOM_ALPHA) for _ in range(n))


def load_valid_corpus() -> List[str]:
    """Read every reference and bench program for use as mutation seeds."""
    out = []
    for sub in ("reference", "bench/tasks", "validation/tasks"):
        base = os.path.join(ROOT, sub)
        if not os.path.isdir(base):
            continue
        for d in os.listdir(base):
            for fname in ("program.aeth", "reference.aeth"):
                p = os.path.join(base, d, fname)
                if os.path.isfile(p):
                    with open(p) as f:
                        out.append(f.read())
    return out


def gen_mutate(rng: random.Random, seeds: List[str]) -> str:
    s = list(rng.choice(seeds))
    n_muts = rng.randint(1, 4)
    for _ in range(n_muts):
        if not s:
            break
        op = rng.choice(("drop", "dup", "swap", "ins"))
        i = rng.randrange(len(s))
        if op == "drop":
            del s[i]
        elif op == "dup":
            s.insert(i, s[i])
        elif op == "swap" and i + 1 < len(s):
            s[i], s[i + 1] = s[i + 1], s[i]
        elif op == "ins":
            s.insert(i, rng.choice(_RANDOM_ALPHA))
    return "".join(s)


def gen_tokens(rng: random.Random, seeds: List[str]) -> str:
    """Tokenize a valid seed, perturb the token stream, reconstruct source."""
    seed = rng.choice(seeds)
    try:
        toks = tokenize(seed)
    except Exception:
        # Seed itself fails to tokenize — skip
        return seed
    # Drop the EOF then perturb
    body = [t for t in toks if t.kind != "eof"]
    if not body:
        return seed
    n_muts = rng.randint(1, 3)
    for _ in range(n_muts):
        if not body:
            break
        i = rng.randrange(len(body))
        op = rng.choice(("drop", "dup", "swap"))
        if op == "drop":
            del body[i]
        elif op == "dup":
            body.insert(i, body[i])
        elif op == "swap" and i + 1 < len(body):
            body[i], body[i + 1] = body[i + 1], body[i]
    # Reconstruct source by serializing tokens with single spaces.
    out = []
    for t in body:
        if t.kind == "string":
            out.append('"' + str(t.value).replace("\\", "\\\\").replace('"', '\\"') + '"')
        elif t.kind == "int" or t.kind == "float":
            out.append(str(t.value))
        else:
            out.append(str(t.value))
    return " ".join(out)


# ----------------------------------------------------------------------
# Fuzz loop
# ----------------------------------------------------------------------

def run_fuzz(mode: str, rounds: int, seed: int, verbose: bool) -> dict:
    rng = random.Random(seed)
    seeds = load_valid_corpus() if mode in ("mutate", "tokens") else []
    if mode in ("mutate", "tokens") and not seeds:
        return {"ok": False, "reason": "no seeds found in reference/ or bench/"}

    counts = {
        "rounds": rounds,
        "parsed_ok": 0,
        "structured_reject": 0,
        "timeouts": 0,
        "violations": [],
        "emit_violations": [],
        "roundtrip_violations": [],
    }
    t0 = time.time()
    for r in range(rounds):
        if mode == "random":
            src = gen_random(rng)
        elif mode == "mutate":
            src = gen_mutate(rng, seeds)
        else:
            src = gen_tokens(rng, seeds)

        try:
            ast = safe_parse(src)
        except AetherError:
            counts["structured_reject"] += 1
            continue
        except _ParseTimeout:
            counts["timeouts"] += 1
            counts["violations"].append({
                "round": r,
                "kind": "parse_timeout",
                "src_head": src[:200],
            })
            continue
        except RecursionError as e:
            counts["violations"].append({
                "round": r,
                "kind": "recursion_error",
                "src_head": src[:200],
            })
            continue
        except Exception as e:
            counts["violations"].append({
                "round": r,
                "kind": f"{type(e).__name__}",
                "msg": str(e)[:200],
                "src_head": src[:200],
            })
            continue

        # parse succeeded; emit must also not crash
        counts["parsed_ok"] += 1
        try:
            py = emit(ast)
            compile(py, "<fuzz>", "exec")
        except AetherError:
            # legitimate: emitter raised structured error (rare)
            pass
        except Exception as e:
            counts["emit_violations"].append({
                "round": r,
                "kind": f"{type(e).__name__}",
                "msg": str(e)[:200],
                "src_head": src[:200],
            })

        try:
            canonical = print_ast(ast)
            reparsed = safe_parse(canonical)
            if strip_positions(reparsed) != strip_positions(ast):
                counts["roundtrip_violations"].append({
                    "round": r,
                    "kind": "ast_mismatch",
                    "src_head": src[:200],
                    "canonical_head": canonical[:200],
                })
        except AetherError as e:
            counts["roundtrip_violations"].append({
                "round": r,
                "kind": "canonical_parse_error",
                "msg": e.diag.message[:200],
                "src_head": src[:200],
            })
        except _ParseTimeout:
            counts["roundtrip_violations"].append({
                "round": r,
                "kind": "canonical_parse_timeout",
                "src_head": src[:200],
            })
        except Exception as e:
            counts["roundtrip_violations"].append({
                "round": r,
                "kind": f"{type(e).__name__}",
                "msg": str(e)[:200],
                "src_head": src[:200],
            })

        if verbose and r % 100 == 0:
            print(f"  ... round {r}, parsed_ok={counts['parsed_ok']}, "
                  f"struct_reject={counts['structured_reject']}", file=sys.stderr)

    counts["elapsed_s"] = round(time.time() - t0, 2)
    counts["ok"] = (
        len(counts["violations"]) == 0 and
        len(counts["emit_violations"]) == 0 and
        len(counts["roundtrip_violations"]) == 0
    )
    return counts


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=("random", "mutate", "tokens", "all"),
                   default="all")
    p.add_argument("--rounds", type=int, default=300)
    p.add_argument("--seed", type=int, default=20260503)
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    modes = ["random", "mutate", "tokens"] if args.mode == "all" else [args.mode]
    overall_ok = True
    for m in modes:
        print(f"## fuzz mode: {m} ({args.rounds} rounds, seed={args.seed})")
        result = run_fuzz(m, args.rounds, args.seed, args.verbose)
        print(f"  rounds:            {result['rounds']}")
        print(f"  parsed_ok:         {result.get('parsed_ok', 0)}")
        print(f"  structured_reject: {result.get('structured_reject', 0)}")
        print(f"  timeouts:          {result.get('timeouts', 0)}")
        print(f"  violations:        {len(result.get('violations', []))}")
        print(f"  emit_violations:   {len(result.get('emit_violations', []))}")
        print(f"  roundtrip_errors:  {len(result.get('roundtrip_violations', []))}")
        print(f"  elapsed:           {result.get('elapsed_s', 0)}s")
        if result.get("violations"):
            print("  first 3 violations:")
            for v in result["violations"][:3]:
                print(f"    {v}")
        if result.get("emit_violations"):
            print("  first 3 emit violations:")
            for v in result["emit_violations"][:3]:
                print(f"    {v}")
        if result.get("roundtrip_violations"):
            print("  first 3 roundtrip violations:")
            for v in result["roundtrip_violations"][:3]:
                print(f"    {v}")
        if not result.get("ok"):
            overall_ok = False
        print()

    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
