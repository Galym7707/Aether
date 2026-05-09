# Aether

Aether is an experimental AI-native programming language for safer
AI-generated code using contracts, refinement types, effects, and structured
diagnostics.

Status: research prototype / early compiler prototype, not production-ready.

## 30-Second Demo

Python can silently accept invalid input when the program author forgets a
guard:

```python
def average(xs: list[int]) -> int:
    if not xs:
        return 0  # fake value for invalid input
    return sum(xs) // len(xs)
```

Aether can put the input rule at the function boundary:

```aether
type NonEmptyIntList = List<Int> where length(self) > 0

function average(xs: NonEmptyIntList) returns Int
  requires length(xs) > 0
  effects pure
do
  var total: Int = 0
  for x in xs do
    total = total + x
  end
  return total / length(xs)
end
```

Run the negative example:

```powershell
python -B -m transpiler.aether.cli --json run examples\negative\01_empty_average_contract.aeth
```

The current compiler rejects `average([])` with diagnostic `E0302` in category
`refinement`.

## Quickstart

Windows:

```powershell
python -B scripts\run_all.py
python -B -m transpiler.aether.cli check examples\01_safe_divide.aeth
python -B -m transpiler.aether.cli run examples\01_safe_divide.aeth
pip install -e .
aether check examples\01_safe_divide.aeth
aether run examples\01_safe_divide.aeth
```

macOS/Linux:

```bash
python3 -B scripts/run_all.py
python3 -B -m transpiler.aether.cli check examples/01_safe_divide.aeth
python3 -B -m transpiler.aether.cli run examples/01_safe_divide.aeth
python3 -m pip install -e .
aether check examples/01_safe_divide.aeth
aether run examples/01_safe_divide.aeth
```

`examples/01_safe_divide.aeth` prints:

```text
5
```

## Write Aether With AI

Start with [docs/AETHER_LANGUAGE_GUIDE.md](docs/AETHER_LANGUAGE_GUIDE.md) and
the files in [examples/](examples/). Copyable prompts live in
[prompt/](prompt/):

- [prompt/AETHER_SYNTAX_CHEATSHEET.md](prompt/AETHER_SYNTAX_CHEATSHEET.md)
- [prompt/GEMINI_AETHER_PROMPT.md](prompt/GEMINI_AETHER_PROMPT.md)
- [prompt/CLAUDE_AETHER_PROMPT.md](prompt/CLAUDE_AETHER_PROMPT.md)
- [prompt/GPT_AETHER_PROMPT.md](prompt/GPT_AETHER_PROMPT.md)

Most common syntax rules:

- Use `function`, not `fn`.
- Use `returns`, not `->`.
- Use `List<Int>`, not `List[Int]`.
- Use `length(xs)`, not `xs.len()`.
- Use `do`/`end`, not braces.
- Use helper predicates instead of lambdas.
- Every function needs `effects`; pure helpers use `effects pure`.

## What Works Now

- Function declarations with parameters, return types, contracts, and effects.
- `requires` / `ensures` runtime checks.
- Refinement-typed parameter checks at function boundaries.
- Structural generic/list type checking for the supported subset: `List<T>`
  element types, nested lists, `Map<K,V>` helper flows, `Option<T>` /
  `Result<T,E>` constructors, and user generic functions such as
  `function id<T>(x: T) returns T`.
- Static diagnostics for mixed list literals, wrong `append` element types,
  empty lists without contextual type, non-Int indexes, negative indexes, and
  obvious known-length out-of-bounds indexes.
- Runtime index diagnostics for dynamic out-of-bounds cases, without Python
  tracebacks for the checked runtime helper path.
- Static effect checking for direct calls to known functions.
- Scoped SMT checks for a small Int/Float arithmetic contract fragment when
  `z3-solver` is installed.
- Lists, maps, records with positional constructors, tagged unions, pattern
  matching, loops, and helper functions.
- Structured JSON diagnostics through `--json`.
- `aether ast`, `aether check`, `aether run`, and `aether test`.
- A small Agent SDK in `transpiler/aether/agent_sdk.py`.

## What Is Not Implemented Yet

- Complete static verification. The type checker is stronger than the original
  prototype for supported generic/list constructs, but it is not a proof
  system and does not infer or verify every possible program property.
- Explicit generic call syntax such as `identity<Int>(5)`. Generic functions
  are called normally, for example `identity(5)`, and the checker infers
  supported type variables from arguments.
- Deterministic runtime hooks for time/random.
- Precise call-site source spans for every runtime diagnostic. Contract,
  refinement, and index diagnostics now include useful source lines where
  feasible, but some runtime errors still report boundary/helper positions.
- Record literal syntax such as `Point { x = 1, y = 2 }`.
- Direct list item assignment such as `xs[i] = value`.
- A production security model for capabilities. `--capability-strict` is an
  opt-in static check, not a complete sandbox.
- A package release. `pip install -e .` is for local development.

## Development Commands

Core gate:

```powershell
python -B scripts\run_all.py
python -B validation\run_validation.py
python -B validation\run_python_validation.py
python -B tests\test_regressions.py
python -B tests\test_json_diagnostics.py
python -B tests\test_prelint_ai_syntax_errors.py
python -B tests\test_list_operations.py
python -B tests\test_generic_typechecking.py
python -B tests\test_static_index_diagnostics.py
python -B tests\test_contract_diagnostics.py
python -B tests\test_ai_repair_diagnostics.py
python -m pytest -q
```

CLI examples:

```powershell
python -B -m transpiler.aether.cli ast examples\01_safe_divide.aeth
python -B -m transpiler.aether.cli check examples\01_safe_divide.aeth
python -B -m transpiler.aether.cli run examples\01_safe_divide.aeth
python -B -m transpiler.aether.cli --json check examples\negative\06_effect_violation_demo.aeth
```

Packaging:

```powershell
pip install -e .
aether ast examples\01_safe_divide.aeth
aether check examples\01_safe_divide.aeth
aether run examples\01_safe_divide.aeth
```

Fuzz smoke test:

```powershell
python -B scripts\fuzz_parser.py --rounds 200 --mode all
```

## Layout

```text
grammar/        Current grammar and language notes
reference/      Reference programs
examples/       Small canonical examples for humans and AI models
docs/           AI-facing guide, list guide, feature matrix, final report
prompt/         AI prompt pack
bench/          Benchmark tasks and AI generation benchmark plan
validation/     Validation task references
transpiler/     Compiler, runtime, passes, CLI, and Agent SDK
tests/          Regression and diagnostics tests
scripts/        Local verification scripts
```

See [docs/FEATURE_MATRIX.md](docs/FEATURE_MATRIX.md) for a feature-by-feature
status table.
