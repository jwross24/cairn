# M1 baseline skill costs on the build machine

Measured 2026-09-02 with `cairn measure dlp` on the M1 build machine (macOS, Apple silicon,
24 GB, load averages between 5.4 and 6.5 from processes outside this session throughout,
so every per-op figure is an upper bound for a quiet core). Group operations are exact
and reproduce byte-for-byte under a seed; the walls carry the load. Every table below is
the row the skill's `COST_PROFILE` cites, and `tests/unit/test_dlp_profiles.py` pins
the two to each other. "ops" is group operations for the two solvers and toy_curve
tries for the instance-maker. "verify s" is the witness check for rho-dp (a few scalar
multiplications under libpari, so a constant); for the other two, whose cost model is
same_as_production, it is the production wall itself and no second run happens.

## 1. rho-dp, plain walk (the ladder baseline)

`cairn measure dlp --skill rho-dp --sizes 28,30,40 --seeds 10` and
`cairn measure dlp --skill rho-dp --sizes 50 --seeds 3`. The 28-bit row includes the
BSGS second opinion the skill runs at or below `CROSS_CHECK_MAX_BITS`; the 50-bit row
ran three seeds with a pytest session concurrent for part of the first two.

| bits | seeds | mean ops | sd ops | min ops | max ops | per-op us | mean wall s | sd wall s | verify s |
|---|---|---|---|---|---|---|---|---|---|
| 28 | 10 | 17108.2 | 10658.24 | 1671 | 39219 | 1.9364 | 0.0331 | 0.014 | 0.000278 |
| 30 | 10 | 37396.2 | 19210.17 | 9701 | 73522 | 0.7023 | 0.0263 | 0.0126 | 0.000186 |
| 40 | 10 | 1130789.7 | 628392.24 | 298318 | 2050516 | 2.0235 | 2.2881 | 0.9632 | 0.000442 |
| 50 | 3 | 42652406.33 | 12984457.73 | 28001474 | 52736274 | 2.1805 | 93.0025 | 45.177 | 0.005739 |

Expected ops from the birthday bound, 1.2533 sqrt(n): 20531 at 28 bits, 41062 at 30,
1313990 at 40 and 42047696 at 50 (n from the seed-1 instance of each size). The
50-bit mean sits within 2 % of it; the smaller sizes sit below it on ten seeds with a
standard deviation near half the mean, which is the geometric spread of a single walk.

## 2. rho-dp, negation-map variant (a claimant, never the baseline)

`cairn measure dlp --skill rho-dp --negation-map --sizes 28,30,40 --seeds 10`.

| bits | seeds | mean ops | sd ops | min ops | max ops | per-op us | mean wall s | sd wall s | verify s |
|---|---|---|---|---|---|---|---|---|---|
| 28 | 10 | 14028.3 | 8658.69 | 1430 | 26346 | 1.8987 | 0.0266 | 0.0081 | 0.000173 |
| 30 | 10 | 37824.7 | 12229.01 | 18016 | 58222 | 0.8251 | 0.0312 | 0.0084 | 0.000223 |
| 40 | 10 | 1088522.2 | 564794.48 | 166850 | 2112969 | 1.5473 | 1.6843 | 0.8216 | 0.000229 |

The ops ratio plain / negation-map on these ten seeds is 1.22 at 28 bits, 0.99 at 30
and 1.04 at 40. With a standard deviation near half the mean and ten seeds, the
standard error on each mean is about 17 %, so this sample cannot resolve the sqrt(2)
either way. That measurement is control (j)'s, not this note's. Fruitless-cycle escapes
appear in every negation-map run and are counted in the output's `walk` block.

## 3. bsgs (the refutation floor)

`cairn measure dlp --skill bsgs --sizes 28,30 --seeds 10`,
`cairn measure dlp --skill bsgs --sizes 40 --seeds 10` and
`cairn measure dlp --skill bsgs --sizes 50 --seeds 2`. Table entries and bytes are the
skill's own accounting (u64 keys plus a u32 slot table of the next power of two at or
above twice the entries, so 16 to 24 bytes per entry by construction); maxrss is the
process high-water mark read after each size, a diagnostic beside the gate's own RSS
measurement.

| bits | seeds | mean ops | sd ops | min ops | max ops | per-op us | mean wall s | sd wall s | table entries | table bytes | bytes/entry | maxrss MB | verify s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 28 | 10 | 19806.8 | 4305.76 | 13993 | 29116 | 1.4746 | 0.0292 | 0.0098 | 13727.7 | 240893.6 | 17.548 | 77.6 | 0.029206 |
| 30 | 10 | 41226.4 | 9522.34 | 32236 | 61769 | 0.8459 | 0.0349 | 0.0122 | 29396.3 | 497314.4 | 16.918 | 77.7 | 0.034873 |
| 40 | 10 | 1171748.6 | 288195.47 | 807256 | 1807538 | 1.6077 | 1.8838 | 0.5283 | 881489.6 | 15440524.8 | 17.516 | 155.8 | 1.883767 |
| 50 | 2 | 44769554.0 | 8175063.73 | 38988911 | 50550197 | 2.085 | 93.3451 | 20.8691 | 26116919.0 | 477370808.0 | 18.278 | 905.8 | 93.345101 |

Entries follow ceil(sqrt(n)) - 1 exactly at every size (asserted per corpus case in
`tests/unit/test_bsgs.py`). The measured bytes per entry sit between 16.9 and 18.3
across four sizes, inside the declared 16 to 24. At 50 bits the table holds
26116919 entries in 455 MiB
while the process peaks at 906 MiB, the difference
being the interpreter and the key array's growth slack; the §6(4) figure of about
5 x 10^7 operations under 1 GB at 50 bits holds on this machine at
44769554 mean operations.

The 60-bit memory cap, as 2^30 entries times the 50-bit measured bytes per entry
(18.278), is 19625853059 bytes, about 18.3 GiB: an
extrapolation from the measured per-entry figure, not a run at 60 bits. Bead L1 seeds
the ladder plan's floor and cap fields with the §6(4) arithmetic; the values in this
section replace those seeds when the plan exists to write into.

The ladder plan (`bundle/ladder_plan.json`, cairn-m1-cqt.1.1) carries the 30/40/50-bit rows above as its refutation floor, rounded to integers, and one extrapolated 60-bit row: a 2^30-entry table (PLAN §6(4)) at the 50-bit rung's measured 1.7142 ops per entry (44769554 / 26116919) and 18.278 bytes per entry, giving 1840605416 group operations and 19625853059 bytes. Both 60-bit figures derive from that one table size; neither is a run at 60 bits, and PLAN §6(4) tags them CONJECTURE.

## 4. instance-maker

`cairn measure dlp --skill instance-maker --sizes 28,30,40,50,60 --seeds 10`. "ops" is
toy_curve tries; the 28-bit row includes the BSGS second opinion on Q = xP.

| bits | seeds | mean ops | sd ops | min ops | max ops | per-op us | mean wall s | sd wall s | verify s |
|---|---|---|---|---|---|---|---|---|---|
| 28 | 10 | 49.7 | 37.67 | 5 | 131 | 988.4925 | 0.0491 | 0.0074 | 0.049128 |
| 30 | 10 | 45.0 | 46.7 | 9 | 148 | 746.9944 | 0.0336 | 0.004 | 0.033615 |
| 40 | 10 | 55.5 | 38.86 | 3 | 122 | 913.9955 | 0.0507 | 0.0094 | 0.050727 |
| 50 | 10 | 79.2 | 69.22 | 11 | 220 | 2239.772 | 0.1774 | 0.103 | 0.17739 |
| 60 | 10 | 93.6 | 93.9 | 10 | 332 | 8072.7288 | 0.7556 | 0.6728 | 0.755607 |

The maker's wall is toy_curve's plus one scalar multiplication, so it stays a Tier-0
arithmetic skill through the 60-bit completion rung.
