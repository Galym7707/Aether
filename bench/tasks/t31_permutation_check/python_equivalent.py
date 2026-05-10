def same_sorted_items(xs, ys):
    return all(a == b for a, b in zip(xs, ys))


print("same" if same_sorted_items([1, 2], [1, 2, 3]) else "different")
