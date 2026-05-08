# Aether v0.1 — Phase 1 Bootstrap

A programming language designed for AI-native code generation: keyword-rich surface syntax, canonical AST, contracts in signatures, an effect system, and a capability-aware module model.

This repository is the **Phase 1 bootstrap** described in the project plan. It is not production-ready. The goal of v0.1 is a runnable system end-to-end so a Claude-driven generation/test loop can be evaluated against it.

## Layout

    grammar/        Specification: keywords, types, effects, EBNF, stdlib
    reference/      Reference programs (source + canonical AST + Python equivalent + tests)
    transpiler/     The aether compiler/runtime; the SMT pass uses z3-solver
    prompt/         The locked system prompt used for generation
    bench/          Benchmark harness — drives the prompt+compiler+test loop
    tests/          Top-level integration tests
    scripts/        Helper scripts (run_all, fuzz, etc.)
    SPEC_ISSUES.md  Log of v0.2 issues discovered during v0.1 work
    requirements.txt Python dependencies for the current toolchain

## Quick start

    # From the project root
    python3 -m transpiler.aether.cli run reference/01_hello/program.aeth
    python3 -m transpiler.aether.cli check reference/02_factorial_recursive/program.aeth
    python3 scripts/run_all.py        # run every reference program + tests
    python3 bench/run_bench.py        # run the benchmark harness on a task set

The CLI emits structured JSON on `--json` so an agent can consume it.

## Design principles (short form)

1. One syntactic form per semantic operation.
2. Every public function declares contracts (`requires`, `ensures`) and effects.
3. Modules declare their capabilities; the runtime grants only what's declared.
4. The AST is canonical modulo source-position metadata: `strip_positions(parse(print_ast(ast))) == strip_positions(ast)` and `print_ast(parse(s)) == canonical(s)`.
5. Errors are structured; suggestions are machine-readable.

See `grammar/keywords.md`, `grammar/types.md`, `grammar/effects.md`, `grammar/grammar.ebnf`, `grammar/stdlib.md`.
