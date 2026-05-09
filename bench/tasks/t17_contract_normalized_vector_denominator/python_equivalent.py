def first_normalized(value, total):
    safe_total = total if total != 0 else 1
    return value // safe_total


print(first_normalized(10, 0))
