# t18_contract_valid_age_score

This task checks a realistic integer-domain refinement. Python silently clamps
`-5` to `0`; Aether rejects the invalid age. Expected Aether diagnostic:
`E0302` in category `refinement`.
