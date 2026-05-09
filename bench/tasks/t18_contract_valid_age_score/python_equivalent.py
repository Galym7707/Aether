def age_bucket(age):
    age = max(0, min(130, age))
    return "adult" if age >= 18 else "minor"


print(age_bucket(-5))
