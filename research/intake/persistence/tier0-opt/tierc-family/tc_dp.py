import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-family')
import random, time, json, math
P = 193 * 769


def count_zero_sum(weights_positions, nu):
    cnt = [0] * P
    cnt[0] = 1
    terms = [(d - 1) * pow(10, e, P) % P for d, e in weights_positions]
    inv9 = pow(9, -1, P)
    terms.append(pow(10, nu, P) * inv9 % P)
    for c in terms:
        sh = cnt[-c:] + cnt[:-c] if c else cnt[:]
        cnt = [x + y for x, y in zip(cnt, sh)]
    return cnt


def sample(M, trials, rng, tag):
    out = []
    k = len(M)
    tau = (-pow(9, -1, P)) % P
    for t in range(trials):
        pos = [(d, rng.randrange(0, 96)) for d in M]
        nu = rng.randrange(0, 96)
        cnt = count_zero_sum(pos, nu)
        out.append((cnt[0] - 1, cnt[tau]))
    mu = 2 ** (k + 1) / P
    z = [o[0] for o in out]
    t = [o[1] for o in out]
    mean_z = sum(z) / len(z)
    mean_t = sum(t) / len(t)
    var_t = sum((x - mean_t) ** 2 for x in t) / (len(t) - 1)
    print(json.dumps(dict(tag=tag, k=k, trials=trials, expected=round(mu, 3), mean_zero_minus_shadow=round(mean_z, 3), min_zero=min(z), max_zero=max(z),
                          mean_tau=round(mean_t, 3), min_tau=min(t), max_tau=max(t), sd_tau=round(math.sqrt(var_t), 3), poisson_sd=round(math.sqrt(mu), 3))), flush=True)


if __name__ == '__main__':
    rng = random.Random(20261024)
    t0 = time.time()
    sets = [
        ('A/B k=12', [2] * 6 + [3, 3, 4, 7, 8, 8]),
        ('A/B k=16', [2] * 10 + [3, 3, 4, 7, 8, 8]),
        ('A/B k=20', [2] * 14 + [3, 3, 4, 7, 8, 8]),
        ('C 128421199872 k=31', [2] * 23 + [3] * 7 + [7]),
        ('C 3416267673274176 k=34', [2] * 6 + [3] * 27 + [7]),
        ('C 727326941773824 k=44', [2] * 39 + [3] * 3 + [7] * 2),
    ]
    for tag, M in sets:
        sample(M, 12, rng, tag)
    print('seconds', round(time.time() - t0, 1))
