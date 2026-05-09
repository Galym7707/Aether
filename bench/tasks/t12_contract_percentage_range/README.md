# t12_contract_percentage_range

This task shows Aether rejecting an out-of-range percentage before a nonsensical
discount calculation. The Python equivalent accepts `150` and prints `-100`.
Expected Aether diagnostic: `E0302` in category `refinement`.
