# t15_contract_probability_value

This task checks a probability refinement. Python silently clamps `1.4` to
`1.0`; Aether rejects the invalid probability. Expected Aether diagnostic:
`E0302` in category `refinement`.
