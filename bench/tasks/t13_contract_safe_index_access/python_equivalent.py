def safe_at(xs, index):
    if 0 <= index < len(xs):
        return xs[index]
    return 0


print(safe_at([10, 20, 30], 5))
