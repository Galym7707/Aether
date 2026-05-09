# t16_contract_bounded_loop_count

This task checks that oversized loop counts are rejected at the boundary. The
Python equivalent silently caps the value at `1000`. Expected Aether
diagnostic: `E0302` in category `refinement`.
