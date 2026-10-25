import random
F = 10**48 + 1
R = lambda m: (10**m - 1) // 9
inv9 = pow(9, -1, F)
random.seed(5)
bad = 0
for _ in range(2000):
    q = random.randint(5, 40)
    nu = random.randrange(48)
    items = [(random.randint(2, 9), random.randrange(48)) for _ in range(q)]
    V = R(nu) + sum((d - 1) * 10**e for d, e in items)
    J = [random.random() < 0.5 for _ in range(q)]
    lift_nu = random.random() < 0.5
    V2 = R(nu + 48 * lift_nu) + sum((d - 1) * 10**(e + 48 * j) for (d, e), j in zip(items, J))
    pred = V - 2 * sum((d - 1) * 10**e for (d, e), j in zip(items, J) if j)
    if lift_nu:
        pred += -2 * inv9 * 10**nu
    bad += (V2 - pred) % F != 0
print("mismatches", bad, "of 2000")
