# t19_safe_list_update_helper

This task checks the standard `updateAt` helper. Python code often clamps or
ignores an invalid index and continues with a misleading list. The Aether
reference makes the invalid state explicit by returning `Err("index out of
bounds")` instead of mutating or silently accepting the update.
