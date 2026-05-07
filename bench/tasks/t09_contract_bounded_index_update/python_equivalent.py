def update_at(xs, index, value):
    updated = list(xs)
    if 0 <= index < len(updated):
        updated[index] = value
    return updated


print(update_at([1, 2, 3], 9, 99))
