def choose_bucket(weights, threshold):
    cleaned = [max(0, weight) for weight in weights]
    total = sum(cleaned)
    if total <= 0:
        return 0
    scaled_threshold = threshold * total // 100
    cumulative = 0
    for index, weight in enumerate(cleaned):
        cumulative += weight
        if scaled_threshold < cumulative:
            return index
    return len(weights) - 1


print(f"bucket={choose_bucket([50, -20, 70], 25)}")
