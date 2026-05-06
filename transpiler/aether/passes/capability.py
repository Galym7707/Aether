"""Capability-gating pass.

Runs when `aether run --capability-strict` (or `aether check --capability-strict`)
is set. Walks the AST once, collects every capability declared by every
`module ... requires capability X end` block, then walks every FunctionDecl's
effects clause and checks each effect's required capability is in the declared
set. Diagnostics are returned as a list; an empty list means all green.

Effect-to-capability mapping (v0.2 minimum):

    pure                  → no capability required
    panic                 → no capability required (always available)
    mutate(_)             → no capability required (module-local mutation)
    log                   → log
    random                → random
    fs.<anything>         → fs
    net.<anything>        → net
    db.<anything>         → db
    time.<anything>       → time
    other.<anything>      → first segment of the dotted path (default rule)

Programs that have no `module` declaration have an empty declared-capability
set; under --capability-strict this means only `pure`/`panic`/`mutate` effects
are permitted. To declare a non-pure effect, declare a module with the matching
capability. This is the v0.2 surface for the project's "trust by construction"
pitch.
"""

from __future__ import annotations
from typing import Any, Dict, List, Set

from ..diagnostics import Diagnostic, Position


# Effects that require no capability.
_FREE_EFFECTS = {"pure", "panic"}


def effect_capability(effect: Dict[str, Any]) -> str:
    """Return the capability name required by an effect, or '' if none.

    `effect` is the AST node: `{"path": ["fs", "read"], "arg": ...}`.
    """
    path = effect["path"]
    head = path[0]
    if head in _FREE_EFFECTS:
        return ""
    if head == "mutate":
        return ""
    # Single-segment effects whose name is also their capability.
    return head


def collect_declared_capabilities(ast: Dict[str, Any]) -> Set[str]:
    out: Set[str] = set()
    for d in ast["decls"]:
        if d["kind"] == "ModuleDecl":
            out.update(d.get("capabilities", []))
    return out


def check_capabilities(ast: Dict[str, Any]) -> List[Diagnostic]:
    declared = collect_declared_capabilities(ast)
    diags: List[Diagnostic] = []
    for d in ast["decls"]:
        if d["kind"] != "FunctionDecl":
            continue
        fn_name = d["name"]
        pos = d.get("pos") or {"line": 0, "column": 0}
        for eff in d.get("effects", []):
            cap = effect_capability(eff)
            if not cap:
                continue
            if cap not in declared:
                effname = ".".join(eff["path"])
                diags.append(Diagnostic(
                    code="E0701",
                    category="capability",
                    severity="error",
                    message=(f"function {fn_name!r} declares effect {effname!r} which "
                             f"requires capability {cap!r}, but no module in this "
                             f"program declares it"),
                    position=Position(pos.get("line", 0), pos.get("column", 0)),
                    suggestion=(f"add `module ... requires capability {cap} ... end` "
                                f"to the program, or change the function to be `effects pure`"),
                    confidence=1.0,
                    extra={"function": fn_name, "effect": effname,
                           "required_capability": cap,
                           "declared_capabilities": sorted(declared)},
                ))
    return diags
