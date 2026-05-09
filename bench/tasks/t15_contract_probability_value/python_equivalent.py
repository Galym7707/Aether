def risk_label(p):
    p = max(0.0, min(1.0, p))
    return "high" if p > 0.5 else "low"


print(risk_label(1.4))
