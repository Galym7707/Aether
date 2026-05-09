def repeat_cost(count):
    count = min(max(count, 0), 1000)
    total = 0
    for _ in range(count):
        total += 1
    return total


print(repeat_cost(5000))
