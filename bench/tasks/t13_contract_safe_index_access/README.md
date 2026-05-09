# t13_contract_safe_index_access

This task demonstrates a precondition for index access. Python silently returns
the fallback `0`; Aether rejects the invalid index through a `requires` clause.
Expected Aether diagnostic: `E0301` in category `contract`.
