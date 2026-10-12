def normalize(v):
    return [abs(t) for t in v]


def total_loss(model, batch):
    out = model(batch)
    parts = {"mse": sum(out), "reg": len(normalize(out))}
    return sum(parts.values()), parts
