# LLM-judge problem-signature prompt — v1

Use one model not in the experimental lineup (e.g. Gemini if benchmarking
Claude+GPT). For each candidate pair, run the prompt twice with A and B
swapped; if verdicts disagree the pair drops to manual review regardless
of confidence. Save raw JSON outputs alongside the experiment results.

## Prompt body (copy below this line)

You are auditing a pair of small programs for informational similarity.
Two programs are *informationally similar* if seeing one as a worked
example would give a model an unfair advantage when asked to write the
other from scratch. This is a stricter test than "look similar" and a
weaker test than "are identical."

You will receive two programs labeled A and B. Both are written in
Aether, a small statically-typed language. You don't need to understand
every Aether construct — focus on what each program *computes*.

Do this in order. Do not skip steps.

Step 1. Write a one-sentence problem signature for A. The signature
should describe what A computes, not how. Avoid mentioning specific
language constructs (no "uses match", "uses for-loop", "uses HOF").
Format: "A computes <what>, given <inputs>, producing <output>."

Step 2. Write a one-sentence problem signature for B in the same format.

Step 3. Judge three relationships independently:

  same_problem: Would a competent programmer, asked to solve A and B
  separately, write substantially the same algorithm? Examples of
  same_problem=true: "sum a list" implemented with foldLeft vs.
  for-loop. "compute factorial" implemented recursively vs.
  iteratively. Examples of same_problem=false: "sum a list" vs.
  "find max of a list" — same shape, different answer.

  same_technique: Do A and B require the same core programming
  technique (e.g., structural recursion, accumulator pattern,
  state machine, lookup table, two-pointer)? Two programs can share
  technique without sharing problem.

  same_domain: Do A and B operate on the same data domain (numbers,
  strings, lists, trees, graphs, key-value maps)? Weakest relation;
  recorded for completeness, not to drive decisions.

Step 4. For each of the three judgments, give a confidence between
0.0 and 1.0. 1.0 means "I would stake my reputation on this." 0.5
means "genuinely unsure." Below 0.7 means "this needs human review."

Step 5. Output JSON only, no preamble, in exactly this shape:

{
  "signature_a": "...",
  "signature_b": "...",
  "same_problem":   {"verdict": true|false, "confidence": 0.0-1.0, "why": "<one sentence>"},
  "same_technique": {"verdict": true|false, "confidence": 0.0-1.0, "why": "<one sentence>"},
  "same_domain":    {"verdict": true|false, "confidence": 0.0-1.0, "why": "<one sentence>"}
}

Decision rules the experimenter applies based on your output:

  - same_problem=true at confidence >= 0.7  →  true near-clone; one
    program must be replaced.
  - same_problem=false but same_technique=true  →  no contamination of
    the answer, but the technique is shared. Note in EXPERIMENT.md.
  - any judgment at confidence < 0.7  →  human review.

Calibration examples:

EXAMPLE 1.
Program A: a function that, given a List<Int>, returns the sum of its
elements using foldLeft.
Program B: a function that, given a List<Int>, returns the sum of its
elements using a for-loop with a var accumulator.
Correct output:
{
  "signature_a": "A computes the sum, given a list of integers, producing an integer.",
  "signature_b": "B computes the sum, given a list of integers, producing an integer.",
  "same_problem":   {"verdict": true,  "confidence": 0.98, "why": "Both compute sum-of-list; the only difference is the iteration mechanism."},
  "same_technique": {"verdict": false, "confidence": 0.85, "why": "A uses higher-order folding, B uses imperative accumulation; technique differs."},
  "same_domain":    {"verdict": true,  "confidence": 0.99, "why": "Both operate on lists of integers."}
}

EXAMPLE 2.
Program A: a recursive function that returns the length of a list.
Program B: a recursive function that returns the factorial of an integer.
Correct output:
{
  "signature_a": "A computes the length, given a list, producing an integer count.",
  "signature_b": "B computes the factorial, given a non-negative integer, producing an integer.",
  "same_problem":   {"verdict": false, "confidence": 0.95, "why": "Different outputs (length of structure vs. product of integers)."},
  "same_technique": {"verdict": true,  "confidence": 0.85, "why": "Both use structural recursion with a base case and one inductive call."},
  "same_domain":    {"verdict": false, "confidence": 0.80, "why": "A operates on lists, B on integers."}
}

Now judge this pair.

Program A:
---
<paste A's source here>
---

Program B:
---
<paste B's source here>
---
