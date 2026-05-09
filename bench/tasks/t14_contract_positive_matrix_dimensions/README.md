# t14_contract_positive_matrix_dimensions

This task checks that invalid matrix dimensions are rejected instead of being
silently coerced. The Python equivalent changes `0` rows to `1` and prints `5`.
Expected Aether diagnostic: `E0302` in category `refinement`.
