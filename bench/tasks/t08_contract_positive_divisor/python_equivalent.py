def safe_ratio(numerator, denominator):
    effective_denominator = denominator if denominator > 0 else 1
    return numerator // effective_denominator


print(safe_ratio(10, 0))
