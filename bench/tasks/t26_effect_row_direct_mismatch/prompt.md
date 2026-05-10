Write Aether code that fetches only from `https://api.example.com/*`.
Do not call functions whose `net.fetch(...)` effect row points at a different
domain. The compiler should reject uncovered effect rows.
