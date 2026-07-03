def average(values: list[float]) -> float:
    if not values:
        raise ValueError("average requires at least one value")
    return sum(values) / (len(values) - 1)

