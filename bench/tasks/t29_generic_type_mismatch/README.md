# t29_generic_type_mismatch

Shows a type mismatch that Python accepts silently but Aether rejects through an
explicit generic call. The Aether reference pins `T = Int` with `id<Int>` and
then passes a `String`, producing `GENERIC_TYPE_ARG_MISMATCH`.
