# Aether Function Type Effects Report

## 1. Summary

This pass added effect annotations to function types without adding lambda
syntax. Function types can now carry effect metadata, and calls through
function-typed parameters are checked against the enclosing function's declared
effects.

Aether remains a research / early compiler prototype, not production-ready.

## 2. Files Changed

- `README.md`
- `docs/AETHER_FIX_PLAN_RESULTS.md`
- `docs/AETHER_FUNCTION_TYPE_EFFECTS_REPORT.md`
- `docs/AETHER_LANGUAGE_GUIDE.md`
- `docs/FEATURE_MATRIX.md`
- `examples/14_function_type_effects.aeth`
- `examples/README.md`
- `examples/negative/11_function_type_effect_escape.aeth`
- `grammar/effects.md`
- `grammar/grammar.ebnf`
- `grammar/types.md`
- `prompt/AETHER_SYNTAX_CHEATSHEET.md`
- `prompt/CLAUDE_AETHER_PROMPT.md`
- `prompt/GEMINI_AETHER_PROMPT.md`
- `prompt/GPT_AETHER_PROMPT.md`
- `prompt/system_prompt.md`
- `scripts/run_all.py`
- `tests/test_function_type_effects.py`
- `transpiler/aether/parser.py`
- `transpiler/aether/passes/effects.py`
- `transpiler/aether/passes/types.py`
- `transpiler/aether/printer.py`

## 3. New Syntax

Function type effects are optional and default to pure:

```aether
function(Int) returns Int
function(Int) returns Int effects log
function(Int) returns function(Int) returns Bool effects log effects pure
```

The nested example means:

- the returned inner function has `effects log`;
- the outer function type has `effects pure`.

In a function declaration returning a function type, a single trailing
`effects` clause belongs to the declaration. To annotate the returned function
type itself and the declaration, write two clauses:

```aether
function make() returns function(Int) returns Int effects log
  effects pure
do
  ...
end
```

## 4. Parser and AST Changes

`FunctionType` AST nodes now include an `effects` field. If omitted in source,
the parser stores `effects pure` explicitly:

```json
{
  "kind": "FunctionType",
  "params": [{"kind": "TypeName", "name": "Int"}],
  "returns": {"kind": "TypeName", "name": "Int"},
  "effects": [{"path": ["pure"], "arg": null}]
}
```

The printer now preserves non-pure function type effects so canonical AST
round-trip tests keep passing.

## 5. Type and Effect Checking

The type checker now:

- stores function effects in internal `function(...) returns ...` types;
- returns function types for named functions used as values;
- typechecks calls through function-typed parameters;
- rejects passing an effectful function where a pure function type is expected.

The effect checker now:

- reads function type effects from function parameters;
- checks calls such as `f(x)` when `f` has a function type with effects;
- emits `HIGHER_ORDER_EFFECT_ESCAPE` when the enclosing function does not
  declare a covering effect.

## 6. Examples Added

- `examples/14_function_type_effects.aeth`
- `examples/negative/11_function_type_effect_escape.aeth`

The positive example prints:

```text
8
5
10
```

The negative example fails with `HIGHER_ORDER_EFFECT_ESCAPE`.

## 7. Tests Added

Added `tests/test_function_type_effects.py` covering:

- parsing function type effects;
- defaulting omitted function type effects to pure;
- nested function type effects;
- pure function-typed callbacks;
- effectful function-typed callbacks with a correct enclosing `effects log`;
- `HIGHER_ORDER_EFFECT_ESCAPE` for missing enclosing effects;
- rejection of effectful functions passed to default-pure function types;
- existing direct-call effect behavior for incorrectly annotated callbacks.

## 8. Verification Results

| Command | Result | Summary |
|---|---|---|
| `python -B tests\test_function_type_effects.py` | pass | `FUNCTION TYPE EFFECT TESTS PASS` |
| `python -B tests\test_regressions.py` | pass | `ALL REGRESSION TESTS PASS`; canonical AST round-trip `48` corpus programs |
| `python -B -m transpiler.aether.cli check examples\14_function_type_effects.aeth` | pass | `OK: examples\14_function_type_effects.aeth (5 decls)` |
| `python -B -m transpiler.aether.cli run examples\14_function_type_effects.aeth` | pass | printed `8`, `5`, `10` |
| `python -B -m transpiler.aether.cli --json check examples\negative\11_function_type_effect_escape.aeth` | expected failure | JSON diagnostic `HIGHER_ORDER_EFFECT_ESCAPE`, category `effect` |
| `python -B scripts\run_all.py` | pass | reference `10/10`, bench `23/23`, python equivalents `20/20`, regression PASS, additional PASS, fuzz PASS |
| `python -m pytest -q` | pass | `98 passed in 8.37s` |
| `python -B validation\run_validation.py` | pass | `10/10 validation references pass` |
| `python -B validation\run_python_validation.py` | pass | `10/10 python validation references pass` |
| `python -B tests\test_option_result_helpers.py` | pass | `OPTION RESULT HELPER TESTS PASS` |
| `python -B tests\test_match_exhaustiveness.py` | pass | `MATCH EXHAUSTIVENESS TESTS PASS` |
| `python -m bench.harness run-reference` | pass | `23/23 reference solutions pass` |
| `python -m bench.harness run-python-equivalents` | pass | `20/20 python equivalents pass` |
| `git diff --check` | pass | exit code `0`; Git printed CRLF conversion warnings on this Windows host |
| `python3 --version` | environment limitation | `python3` is not installed on this Windows host |

## 9. Remaining Limitations

- Lambda syntax is still intentionally unsupported.
- Function type effects are tracked for supported function values and
  parameters, not for arbitrary dynamic values.
- Function effect compatibility now models the supported string-literal
  `net.fetch("...")` rows, but it is still not a complete algebra for
  arbitrary effect arguments.
- Runtime source spans remain best effort for some dynamic failures.

## 10. Recommended Next Tasks

1. Extend effect annotations to future lambda syntax if the language adds it.
2. Add effect-aware checking for collection helpers such as `map`, `filter`,
   and `foldLeft`.
3. Improve diagnostics for effect mismatch when passing function values.
4. Extend effect-row precision beyond the currently supported string-literal
   `net.fetch("...")` cases.
