"""Pairwise structural similarity between programs.

Includes reference/, bench/tasks/, and validation/tasks/.
Method, threshold, and rationale unchanged from the prior version.
"""

from __future__ import annotations
import os
import sys
from collections import Counter
from typing import Iterable, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "transpiler"))

from aether.parser import parse  # noqa: E402


def walk(node, parent_kind=None) -> Iterable[Tuple]:
    if isinstance(node, dict) and "kind" in node:
        kind = node["kind"]
        yield ("node", kind)
        if parent_kind is not None:
            yield ("edge", parent_kind, kind)
        for v in node.values():
            yield from walk(v, kind)
    elif isinstance(node, list):
        for x in node:
            yield from walk(x, parent_kind)


def signature(ast) -> Counter:
    return Counter(walk(ast))


def jaccard_multiset(a: Counter, b: Counter) -> float:
    if not a and not b:
        return 1.0
    keys = set(a) | set(b)
    inter = sum(min(a[k], b[k]) for k in keys)
    union = sum(max(a[k], b[k]) for k in keys)
    return inter / union if union else 0.0


def split_signature(sig: Counter):
    nodes = Counter({k[1]: v for k, v in sig.items() if k[0] == "node"})
    edges = Counter({(k[1], k[2]): v for k, v in sig.items() if k[0] == "edge"})
    return nodes, edges


def gather_programs():
    out = []
    refdir = os.path.join(ROOT, "reference")
    for d in sorted(os.listdir(refdir)):
        p = os.path.join(refdir, d, "program.aeth")
        if os.path.isfile(p):
            out.append(("ref:" + d, p))
    benchdir = os.path.join(ROOT, "bench", "tasks")
    if os.path.isdir(benchdir):
        for d in sorted(os.listdir(benchdir)):
            p = os.path.join(benchdir, d, "reference.aeth")
            if os.path.isfile(p):
                out.append(("bench:" + d, p))
    valdir = os.path.join(ROOT, "validation", "tasks")
    if os.path.isdir(valdir):
        import json as _json
        for d in sorted(os.listdir(valdir)):
            p = os.path.join(valdir, d, "reference.aeth")
            cfg = os.path.join(valdir, d, "grader.json")
            if not os.path.isfile(p) or not os.path.isfile(cfg):
                continue
            with open(cfg) as f:
                if _json.load(f).get("deprecated"):
                    continue
            out.append(("val:" + d, p))
    return out


def main():
    progs = gather_programs()
    sigs, sizes = {}, {}
    for label, path in progs:
        with open(path) as f:
            ast = parse(f.read(), path)
        nodes, edges = split_signature(signature(ast))
        sigs[label] = (nodes, edges)
        sizes[label] = sum(nodes.values())

    THRESHOLD = 0.70
    rows = []
    for la, _ in progs:
        for lb, _ in progs:
            if la >= lb:
                continue
            na, ea = sigs[la]
            nb, eb = sigs[lb]
            jn = jaccard_multiset(na, nb)
            je = jaccard_multiset(ea, eb)
            score = max(jn, je)
            rows.append({"a": la, "b": lb,
                         "size_a": sizes[la], "size_b": sizes[lb],
                         "j_nodes": round(jn, 3), "j_edges": round(je, 3),
                         "max": round(score, 3)})
    rows.sort(key=lambda r: -r["max"])

    print(f"# Pairwise structural similarity (threshold {THRESHOLD})")
    print(f"# {len(progs)} programs total: "
          f"{sum(1 for l,_ in progs if l.startswith('ref:'))} reference + "
          f"{sum(1 for l,_ in progs if l.startswith('bench:'))} bench + "
          f"{sum(1 for l,_ in progs if l.startswith('val:'))} validation")
    print()

    # Cross-set findings: validation must not collide with ref or bench
    print("## CROSS-SET (validation vs reference+bench) — must all be < threshold")
    cross_val = []
    for r in rows:
        a, b = r["a"], r["b"]
        is_val = a.startswith("val:") or b.startswith("val:")
        is_other = (a.startswith("ref:") or a.startswith("bench:")) or \
                   (b.startswith("ref:") or b.startswith("bench:"))
        # exactly one val, exactly one other
        n_val = (a.startswith("val:") + b.startswith("val:"))
        if n_val == 1 and is_other:
            cross_val.append(r)
    cross_val.sort(key=lambda r: -r["max"])
    for r in cross_val[:15]:
        flag = "***" if r["max"] >= THRESHOLD else "   "
        print(f"  {r['a']:36s} <-> {r['b']:36s}  max={r['max']:.3f}  {flag}")
    n_flag_val = sum(1 for r in cross_val if r["max"] >= THRESHOLD)
    print(f"# {n_flag_val} validation cross-set pairs above {THRESHOLD}")
    print()

    # Cross-set findings: reference vs bench (the original Phase A2 concern)
    print("## CROSS-SET (reference vs bench)")
    cross_rb = []
    for r in rows:
        a, b = r["a"], r["b"]
        if (a.startswith("ref:") and b.startswith("bench:")) or \
           (a.startswith("bench:") and b.startswith("ref:")):
            cross_rb.append(r)
    cross_rb.sort(key=lambda r: -r["max"])
    for r in cross_rb[:10]:
        flag = "***" if r["max"] >= THRESHOLD else "   "
        print(f"  {r['a']:36s} <-> {r['b']:36s}  max={r['max']:.3f}  {flag}")
    n_flag_rb = sum(1 for r in cross_rb if r["max"] >= THRESHOLD)
    print(f"# {n_flag_rb} ref-vs-bench pairs above {THRESHOLD}")
    print()

    # Overall flagged
    all_flagged = [r for r in rows if r["max"] >= THRESHOLD]
    print(f"## ALL pairs above {THRESHOLD}: {len(all_flagged)}")
    for r in all_flagged:
        print(f"  {r['a']:36s} <-> {r['b']:36s}  max={r['max']:.3f}")

    # The strict gate: any val-vs-other above threshold = fail
    return 0 if n_flag_val == 0 and n_flag_rb == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
