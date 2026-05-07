def minimum(xs):
    if not xs:
        return 0
    best = xs[0]
    for value in xs[1:]:
        if value < best:
            best = value
    return best


print(minimum([]))
