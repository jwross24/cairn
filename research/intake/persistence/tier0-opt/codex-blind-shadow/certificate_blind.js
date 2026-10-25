function certificate(input) {
  const Z = BigInt;
  const abs = x => x < 0n ? -x : x;
  const mod = (x, m) => (x % m + m) % m;
  const gcd = (a, b) => {
    while (b) [a, b] = [b, a % b];
    return abs(a);
  };
  function inv(a, m) {
    if (m === 1n) return 0n;
    let [r, s, u, v] = [m, mod(a, m), 0n, 1n];
    while (s) {
      const q = r / s;
      [r, s, u, v] = [s, r - q * s, v, u - q * v];
    }
    if (r !== 1n) throw Error("nonunit");
    return mod(u, m);
  }
  function pow(a, e, m) {
    if (e < 0n) return pow(inv(a, m), -e, m);
    let r = 1n;
    for (a = mod(a, m); e; e >>= 1n, a = a * a % m)
      if (e & 1n) r = r * a % m;
    return r % m;
  }
  const floor = (a, b) => (a - mod(a, b)) / b;
  const ceil = (a, b) => -floor(-a, b);
  const round = (a, b) => floor(2n * a + b, 2n * b);
  function sqrt(n) {
    if (n < 0n) throw Error("negative square root");
    if (n < 2n) return n;
    let x = 1n << Z(Math.ceil(n.toString(2).length / 2));
    for (;;) {
      const y = (x + n / x) / 2n;
      if (y >= x) return x;
      x = y;
    }
  }
  const add = (u, v) => [u[0] + v[0], u[1] + v[1]];
  const mul = (s, u) => [s * u[0], s * u[1]];
  const dot = (u, v) => u[0] * v[0] + u[1] * v[1];
  const det = (u, v) => u[0] * v[1] - u[1] * v[0];
  function reduce(C) {
    let [u, v] = C.basis.map(x => x.slice());
    if (!det(u, v)) throw Error("singular lattice");
    for (;;) {
      if (dot(v, v) < dot(u, u)) [u, v] = [v, u];
      if (2n * abs(dot(u, v)) <= dot(u, u)) break;
      v = add(v, mul(-round(dot(u, v), dot(u, u)), u));
    }
    if (det(u, v) < 0n) v = mul(-1n, v);
    let o = C.offset;
    o = add(o, mul(-round(det(u, o), det(u, v)), v));
    o = add(o, mul(-round(dot(u, o), dot(u, u)), u));
    return {offset: o, basis: [u, v]};
  }
  function cut(C, A, B, T, N) {
    if (!C) return null;
    const [u, v] = C.basis;
    const alpha = A * u[0] + B * u[1];
    const beta = A * v[0] + B * v[1];
    const gamma = T - A * C.offset[0] - B * C.offset[1];
    const g = gcd(alpha, N), d = gcd(beta, g);
    if (gamma % d) return null;
    const n = N / g, s = g / d, ia = inv(alpha / g, n);
    const y = mod(gamma / d * inv(beta / d, s), s);
    const x = mod((gamma - beta * y) / g * ia, n);
    const t = mod(-beta / d * ia, n);
    return reduce({
      offset: add(C.offset, add(mul(x, u), mul(y, v))),
      basis: [mul(n, u), add(mul(t, u), mul(s, v))]
    });
  }
  function factors(n) {
    const out = [];
    for (let q = 2n; q * q <= n; q += q === 2n ? 1n : 2n) {
      let e = 0;
      while (n % q === 0n) {n /= q; e++;}
      if (e) out.push([q, e]);
    }
    if (n > 1n) out.push([n, 1]);
    return out;
  }
  function bsgs(g, h, m, order) {
    const z = sqrt(order) + 1n, table = new Map();
    let x = 1n;
    for (let j = 0n; j < z; j++, x = x * g % m)
      if (!table.has(x.toString())) table.set(x.toString(), j);
    const step = pow(g, -z, m);
    x = h;
    for (let i = 0n; i <= z; i++, x = x * step % m) {
      const j = table.get(x.toString());
      if (j !== undefined && i * z + j < order) return i * z + j;
    }
    throw Error("discrete log outside subgroup");
  }
  function log(g, h, m, N, fs) {
    let answer = 0n, product = 1n;
    for (const [q, e] of fs) {
      let x = 0n, qe = 1n;
      const base = pow(g, N / q, m);
      for (let i = 0; i < e; i++) {
        const hq = pow(h * pow(g, -x, m) % m, N / (qe * q), m);
        x += bsgs(base, hq, m, q) * qe;
        qe *= q;
      }
      const t = mod((x - answer) * inv(product, qe), qe);
      answer += product * t;
      product *= qe;
    }
    if (product !== N || pow(g, answer, m) !== mod(h, m))
      throw Error("invalid discrete log");
    return answer;
  }
  const primeCache = new Map(), windowCache = new Map();
  function primeData(p) {
    const key = p.toString();
    if (!primeCache.has(key)) {
      const N = p - 1n, fs = factors(N);
      let g = 2n;
      while (fs.some(([q]) => pow(g, N / q, p) === 1n)) g++;
      const dl = h => log(g, h, p, N, fs);
      primeCache.set(key, {N, dl, A: dl(3n), B: dl(7n)});
    }
    return primeCache.get(key);
  }
  function primeCut(C, V, a, p) {
    if (!C || mod(V, p) === 0n) return null;
    const {N, dl, A, B} = primeData(p);
    return cut(C, A, B, dl(mod(V * pow(2n, -a, p), p)), N);
  }
  function primeCuts(C, V, a, ps) {
    for (const p of ps) {
      C = primeCut(C, V, a, p);
      if (!C) break;
    }
    return C;
  }
  function image(C, v, p) {
    return mod(pow(3n, v[0], p) * pow(7n, v[1], p), p);
  }
  function windowData(K, a) {
    const key = `${K}/${a}`;
    if (windowCache.has(key)) return windowCache.get(key);
    const h = K - a;
    if (h <= 0n) throw Error("requires a < K");
    const m5 = 5n ** K, n5 = 4n * 5n ** (K - 1n);
    const fs5 = [[2n, 2], ...(K > 1n ? [[5n, Number(K - 1n)]] : [])];
    const dl5 = x => log(2n, x, m5, n5, fs5);
    const data = {h, m5, n5, dl5, A5: dl5(3n), B5: dl5(7n)};
    if (h >= 3n) {
      const m2 = 2n ** h, n2 = 2n ** (h - 2n);
      const dl2 = x => log(5n, x, m2, n2, [[2n, Number(h - 2n)]]);
      Object.assign(data, {
        m2, n2, dl2,
        A2: dl2(m2 - 3n), B2: dl2(m2 - 7n)
      });
    }
    windowCache.set(key, data);
    return data;
  }
  function windowCut(C, L, K, a) {
    if (!C) return null;
    const twoa = 2n ** a;
    if (L % twoa || L / twoa % 2n === 0n || L % 5n === 0n)
      return null;
    const w = windowData(K, a);
    C = cut(C, w.A5, w.B5,
      w.dl5(mod(L * inv(twoa, w.m5), w.m5)), w.n5);
    if (!C || w.h === 1n) return C;
    const target = mod(L / twoa, 2n ** w.h);
    const sign = target % 4n === 1n ? 0n : 1n;
    C = cut(C, 1n, 1n, sign, 2n);
    if (!C || w.h === 2n) return C;
    return cut(C, w.A2, w.B2,
      w.dl2(sign ? w.m2 - target : target), w.n2);
  }
  function nearest(C) {
    C = reduce(C);
    const [u, v] = C.basis, o = C.offset;
    const uu = dot(u, u), D = det(u, v), A = det(u, o);
    const t = -round(A, D);
    const z = add(o, mul(t, v));
    let point = add(z, mul(-round(dot(u, z), uu), u));
    let R = dot(point, point);
    const H = sqrt(R * uu);
    for (let j = ceil(-H - A, D); j <= floor(H - A, D); j++) {
      const y = add(o, mul(j, v));
      const p = add(y, mul(-round(dot(u, y), uu), u));
      const r = dot(p, p);
      if (r < R) {R = r; point = p;}
    }
    return {squared_norm: R, nearest: point};
  }
  function analyze(C, U) {
    const q = nearest(C);
    return {...q, above_upper_bound: U === null ? null :
      2209n * q.squared_norm > 20000n * U * U};
  }
  function subsetDP(weights, M, shift) {
    const rows = [Array(M).fill(0n)];
    rows[0][0] = 1n;
    for (const w of weights) {
      const old = rows[rows.length - 1], next = old.slice();
      for (let s = 0; s < M; s++)
        if (old[s]) next[(s + w) % M] += old[s];
      rows.push(next);
    }
    function* back(i, target, mask) {
      if (!i) {if (!target) yield mask; return;}
      if (rows[i - 1][target])
        yield* back(i - 1, target, mask);
      const prior = (target - weights[i - 1] + M) % M;
      if (rows[i - 1][prior])
        yield* back(i - 1, prior, mask | (1n << Z(i - 1)));
    }
    function* candidates() {
      for (let sn = 0; sn <= 1; sn++) {
        const target = (M - sn * shift) % M;
        for (const mask of back(weights.length, target, 0n))
          if (mask || sn) yield {mask, sn};
      }
    }
    return {
      count: rows[weights.length][0] +
        rows[weights.length][(M - shift) % M] - 1n,
      candidates
    };
  }
  function* submasks(mask) {
    for (let s = mask;; s = (s - 1n) & mask) {
      yield s;
      if (!s) return;
    }
  }
  const ids = mask => digits.flatMap((_, i) =>
    mask & (1n << Z(i)) ? [i] : []);
  const sum = mask => digits.reduce((s, x, i) =>
    s + (mask & (1n << Z(i)) ? weightsExact[i] : 0n), 0n);
  const rep = K => (10n ** K - 1n) / 9n;
  if (Z(input.min_digits ?? 0) < 384n)
    throw Error("requires checked large-candidate scope n >= 384");
  const L = 96n, M = Number(input.modulus);
  if (M !== 148417 || 193n * 769n !== Z(M))
    throw Error("wrong modulus");
  const digits = input.digits, a = Z(input.a), nu = Z(input.nu);
  if (a < 0n || a >= L || nu < 0n || nu >= L)
    throw Error("invalid a or nu");
  for (const x of digits)
    if (!Number.isInteger(x.d) || x.d < 2 || x.d > 9 ||
        !Number.isInteger(x.e) || x.e < 0 || x.e >= 96)
      throw Error("invalid digit");
  const weightsExact = digits.map(x => Z(x.d - 1) * 10n ** Z(x.e));
  const weights = weightsExact.map(w => Number(w % Z(M)));
  const shift = Number(
    pow(10n, nu, Z(M)) * inv(9n, Z(M)) % Z(M));
  const dp = subsetDP(weights, M, shift);
  const V = rep(nu) + sum((1n << Z(digits.length)) - 1n);
  const all = (1n << Z(digits.length)) - 1n;
  const ps192 = [
    19841n, 976193n, 6187457n,
    834427406578561n, 1253224535459902849n
  ];
  const ps384 = [3457n, 12289n, 418725889n, 1265011073n];
  const U = input.upper_digits == null ? null : Z(input.upper_digits);
  if (U !== null && U < 1n) throw Error("invalid upper bound");
  const words = [];
  for (const word of input.words) {
    let fixed = 0n;
    const occupied = new Set();
    for (const j of word.fixed) {
      if (!Number.isInteger(j) || j < 0 || j >= digits.length ||
          (fixed & (1n << Z(j))) || occupied.has(digits[j].e))
        throw Error("invalid fixed positions");
      fixed |= 1n << Z(j);
      occupied.add(digits[j].e);
    }
    const free = all ^ fixed;
    let C = reduce({
      offset: word.offset.map(Z),
      basis: word.basis.map(v => v.map(Z))
    });
    C = windowCut(C, rep(L) + sum(fixed), L, a);
    if (!C) throw Error("input word does not survive depth 1");
    for (const p of [193n, 769n]) {
      if (C.basis.some(v => image(C, v, p) !== 1n))
        throw Error(`nontrivial word image at ${p}`);
      if (mod(pow(2n, a, p) * image(C, C.offset, p) - V, p))
        throw Error(`shadow offset mismatch at ${p}`);
    }
    const rivals = [];
    for (const {mask, sn} of dp.candidates()) {
      if (mask & fixed) continue;
      const value = V + (10n ** L - 1n) * sum(mask) +
        Z(sn) * 10n ** nu * rep(L);
      if (primeCuts(C, value, a, ps192))
        rivals.push({S: ids(mask), sn});
    }
    if (rivals.length)
      return {
        id: input.id, verdict: "NOT_ESTABLISHED",
        reason: "nonshadow candidate passes all level-192 prime cuts",
        word: word.id, rivals, dp_nonshadow_count: dp.count
      };
    let C192 = primeCuts(C, V, a, ps192);
    C192 = windowCut(C192,
      rep(192n) + sum(fixed), 192n, a);
    if (!C192) {
      words.push({
        id: word.id, branches: [],
        diagnostic_fixed_V: "dead_by_192"
      });
      continue;
    }
    const diagnostic = primeCuts(C192, V, a, ps384);
    const diagnosticWindows = [];
    if (diagnostic)
      for (const A of submasks(free)) {
        if (new Set(ids(A).map(j => digits[j].e)).size !== ids(A).length)
          continue;
        const Cw = windowCut(diagnostic,
          rep(384n) + sum(fixed) + 10n ** 192n * sum(A),
          384n, a);
        if (Cw)
          diagnosticWindows.push({
            fixed_at_copy2: ids(A), ...analyze(Cw, U)
          });
      }
    const branches = [];
    for (const T of submasks(free)) {
      for (let sn = 0; sn <= 1; sn++) {
        const value = V + (10n ** 192n - 1n) * sum(T) +
          Z(sn) * 10n ** nu * rep(192n);
        const child = primeCuts(C192, value, a, ps384);
        if (!child) continue;
        for (const A of submasks(T)) {
          if (new Set(ids(A).map(j => digits[j].e)).size !== ids(A).length)
            continue;
          const Cw = windowCut(child,
            rep(384n) + sum(fixed) + 10n ** 192n * sum(A),
            384n, a);
          if (Cw)
            branches.push({
              shifted_to_copy2: ids(T), sn,
              fixed_at_copy2: ids(A), ...analyze(Cw, U)
            });
        }
      }
    }
    words.push({
      id: word.id,
      diagnostic_fixed_V: {
        prime_cut_survives: !!diagnostic,
        windows: diagnosticWindows
      },
      branches
    });
  }
  const branches = words.flatMap(w => w.branches);
  return {
    id: input.id, dp_nonshadow_count: dp.count,
    verdict: !branches.length ? "CLOSED_CUT" :
      branches.every(x => x.above_upper_bound === true) ?
        "CLOSED_SANDWICH" : "OPEN",
    words
  };
}

const fs = require("node:fs");
const input = JSON.parse(fs.readFileSync(0, "utf8"));
const results = (Array.isArray(input) ? input : [input]).map(pattern => {
  try {
    return certificate(pattern);
  } catch (error) {
    return {
      id: pattern.id,
      verdict: "NOT_APPLICABLE",
      reason: error.message
    };
  }
});
console.log(JSON.stringify(results,
  (_, value) => typeof value === "bigint" ? value.toString() : value, 2));
process.exitCode = results.some(x =>
  !["CLOSED_CUT", "CLOSED_SANDWICH"].includes(x.verdict)) ? 1 : 0;
