# t28_explicit_generic_collection

Demonstrates explicit generic calls for collection, `Option`, and `Result`
helpers. The Aether reference pins generic arguments with `id<List<Int>>`,
`wrapOption<Int>`, and `makeResult<Int, String>` so generated code does not rely
on inference for the important container shapes.
