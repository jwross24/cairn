## 1. Coherence of the constraint web

### 1. Terminal status conflicts with parked-branch revival · HIGH · §4

**Rationale.** The plan declares parking terminal:

> “every opened branch and every opened claim is a linear obligation that must reach a terminal status (**refuted / parked / promoted / withdrawn**)”

But elsewhere parking is explicitly reversible:

> “park stalls, **revive parked**”

and:

> “PARKED (blocked-not-dead, tagged with blocker → **auto-revived when blocker clears**)”

A state cannot be lifecycle-terminal and automatically transition back to active. More importantly, a worker can satisfy the letter of the leak invariant by parking every obligation, even with a vacuous or immediately clearing blocker. The intended invariant appears to be “every worker exit disposes or hands off its obligations,” not “every branch reaches a terminal lifecycle state.”

```diff
- *Terminal-status invariant:* every opened branch and every opened claim is a linear
- obligation that must reach a terminal status (refuted / parked / promoted / withdrawn).
+ *Worker-disposition invariant:* before a worker exits, every branch or claim it opened
+ must be handed back in one of {active_with_owner, parked_with_valid_blocker, refuted,
+ promoted, withdrawn}. `parked` is not lifecycle-terminal: blocker clearance may return
+ it to `active`. The lifecycle-terminal states are {refuted, promoted, withdrawn}.
+ A park is valid only if its blocker is one of the typed blocker classes and its clearing
+ predicate is present and not already true.
```

This changes a component contract, but preserves immutable epistemics. Evidence: **SPECULATION**, to be validated by M2 fixtures for immediate-clear and missing-predicate parks. Cost: one owner field and stronger transition validation.

### 2. The submission verifier is not bound to the asserted instance · HIGH · §4/§10/§13

**Rationale.** The verifier accepts supplied arithmetic inputs:

> “submission verifier (`xP==Q` subprocess or no submit, ever)”

and M0 accepts based on process output:

> “accepts only `exit == 0` and `stdout == "OK"` and empty stderr”

The egress rule then requires only:

> “a submission … is the verifier’s passing node (§13) or nothing”

Nothing quoted requires the verifier node’s canonical `(curve,n,P,Q)` to equal the instance named by the submitted claim. A worker can verify `xP==Q` on an easy toy instance and attach that passing node to prose about the target instance.

```diff
+ A submission-verifier run takes an immutable instance-node hash, not free-standing
+ arithmetic fields. The egress renderer requires the submission claim's typed target
+ instance hash to equal the verifier run's instance hash and requires the verified
+ `(curve, n, P, Q)` to be read from that node. A mismatch is inadmissible.
```

Add an M0 planted failure: a valid `x` for instance B attached to a claim about instance A must fail. Component: verifier/egress join. Cost: one typed foreign-key comparison and fixture. Evidence: **SPECULATION** until the M0 substitution fixture passes. It strengthens rather than dissolves the verifier.

### 3. Interface-version churn can evade the ledger · MED · §3/§4

**Rationale.** The plan correctly prevents implementation revision churn:

> “the method identity names the interface version and not the implementation revision because the hypothesis is about a method”

But ledger reach requires the same method identity:

> “same method identity failing the same cost model”

A worker can publish the same method under a new interface version, omit a `supersedes` edge, and obtain a fresh method identity. SimHash does not close this: it is only advisory and can be defeated by changing prose.

```diff
+ Admitting a new interface version requires either (a) a human-attested declaration that
+ it is a new method, naming the semantic difference, or (b) a `method_successor` edge to
+ its prior interface version. Ledger preflight follows `method_successor` edges when
+ testing REFUTED reach. Omission parks the branch as `method_identity_review`.
```

Component: ledger preflight. Cost: one edge type, queue class, and review load on genuine interface changes. Evidence: **SPECULATION**, tested at M2 with a semantically identical renamed interface. Calibration and gate authority remain unchanged.

### 4. Milestone dependency audit

**No defect found.** M0 builds the substrate, verifier, pin, tag derivation, and tier-gate skeleton; M1 builds the ladder, replay enforcement, formalization protocol, router, no-go presence check, and disagreement protocol; M2 builds preflight, terminal handling, and the tamper-evident log; M3 builds allocation; M4 builds egress, selector, Librarian, and auditor. Deferred decisions P1–P7 each name a deciding milestone and test criterion.

The apparent M1/M2 overlap around formalization is coherent: M1 builds the mechanical gate and fixtures; M2 adds the Formalizer and statement-review workflow.

---

## 2. Ceremony audit

- **Certificates:** consumed by the reproducibility gate, cache admission, tier tickets, `justify`, and yank handling. **No defect found.** The text also correctly limits the name: “certifies identity and checkability, never truth.”
- **Ledgers:** consumed by funding preflight, branch parking, retry-predicate enforcement, tiering after no-go review, and the negative-results map. **No defect found**, subject to proposal 3.
- **Tag histories:** current derived tags drive `justify`, egress, and promotion, but no running code is stated to branch on the *history* rather than the current tag/evidence graph. The append-only history is presently an audit artifact.
- **Gate plans:** the gate runner branches on ordering, expected exit codes, missing configuration, waiver status, and earlier failures. **No defect found.**
- **Self-tests:** skill launchability and the tier gate branch on certificates/yanks; each gate runs its planted pair before operating. **No defect found.**
- **Receipts:** attempts contain an undefined “execution receipt,” and M0 stores a “derivation receipt,” but no consumer or acceptance predicate is named.
- **Result tables:** consumed by ladder verdict calculation, reproducibility, `justify`, ledger writes, and tier tickets. **No defect found.**
- **Alarms:** P4 calls them “strategy-layer alarms,” but names no scheduler or queue transition that consumes them. P4 does provide a retirement test (“whether either fires on anything the ladder misses”), so only the consumer is missing.

### 5. Cut or operationalize receipts and tag history · LOW · §3/§7/§13

```diff
- execution receipt
+ execution metadata required by replay verification: gate-bundle hash, recipe key,
+ attempt id, start/end monotonic times, process-tree resource totals, exit status, and
+ output-manifest hash
```

Either make replay verification reject missing/mismatched fields, or remove “receipt” as a separate artifact.

```diff
+ Tag history is consumed by the egress/audit query that rejects any rendered promotion
+ whose transition lacks the evidence pointer that derives the current tag.
```

Otherwise cut the separate tag-history structure and reconstruct transitions from immutable evidence records. “Receipt” currently promises attestational value its definition does not deliver.

For P4, add: alarm → typed human-queue item or scheduler diagnostic; it must never alter a tag or ticket. Otherwise cut it when the prototype decision is made.

---

## 3. Gaming the gates as written

### Submission verifier

**Open defect:** easy-instance substitution; proposal 2.

### Ladder

A worker can perform arithmetic through optimized code inside its process, then issue enough dummy calls to the counted group object to appear below the baseline. The clock check only catches excess time:

> “CPU time exceeds what its counted operations would take … marks the rung INCONCLUSIVE”

Fast hidden arithmetic plus plausible dummy counts can pass both predicates. The claim that “the counter cannot see arithmetic done around it, but the clock can” is therefore too strong.

### 6. Require opaque group access in laddered methods · HIGH · §6

```diff
+ A laddered method receives opaque group-element handles and may obtain group results only
+ through the counted gate-owned interface; it receives no curve coordinates or backend
+ object from which independent arithmetic can be reconstructed. M1 includes a planted
+ bypass that attempts local arithmetic plus dummy counted calls and must not reach KEEP.
+ A backend requiring transparent coordinates is INCONCLUSIVE until separately instrumented.
```

Component: ladder operation accounting. Cost: capability-oriented API, serialization overhead, and incompatibility with coordinate-dependent methods; those methods need a separately counted backend. Evidence: **SPECULATION** pending the M1 bypass fixture. This preserves the ladder and makes its stated metric enforceable.

### Formalization gate

**Closed against worker gaming.** The worker cannot write the Challenge, the Solution must name its formal hash, the comparator checks transitive closure, axioms are gate-computed, and PROVEN additionally requires a human-path approval on the exact claim hash. Relevant closing line:

> “`justify` derives PROVEN only from a `lean_artifact` node and an `approve` verdict naming the same statement hash”

Human review error remains possible, but a worker cannot satisfy the gate alone.

### Reproducibility gate

**Open defect:** the generic `Verifiable` grade does not say who approves the verifier. A worker-authored witness and deterministic verifier that always returns success satisfies:

> “Verifiable (a witness checked by a deterministic verifier)”

Rho is tightly specified, but the generic contract is not.

```diff
+ `Verifiable` is assigned only when the gate bundle names the verifier identity and its
+ acceptance predicate, with planted invalid and valid witnesses. A producer-supplied
+ verifier not admitted to the bundle yields `AuditOnly`.
```

Severity **MED**. Cost: verifier admission and fixtures. Evidence: **SPECULATION**, tested by an always-accept verifier. No calibration boundary is weakened.

### Ledger preflight

**Open defect:** interface-version laundering; proposal 3.

### Tier gate

A worker can shard a many-core computation into many individually Tier-1 launches. The gate derives tier per launch:

> “derives the launch’s tier from the profile’s production cost at the launch’s inputs”

It does not classify a gate-visible batch or fan-out by aggregate reserved cost.

### 7. Tier planned fan-out by aggregate cost · HIGH · §5

```diff
+ A parent computation that launches a declared batch/fan-out receives one aggregate cost
+ profile and reservation. The tier gate assigns the batch tier from the sum of child
+ production and verification reservations. A result assembled from undeclared child
+ launches is ineligible as a ticket or justification until the aggregate plan is admitted.
```

Component: tier gate/scheduler. Cost: batch identity, aggregate reservation accounting, and restrictions on dynamic fan-out. Evidence: **SPECULATION**, validated at M1 with a sharded Tier-2 fixture. It enforces cheap-before-expensive without changing evidence classes.

## Three proposals I would stake most on

1. Bind verifier evidence to the submitted instance.
2. Make ladder group access opaque and counted.
3. Tier aggregate fan-out rather than individual shards.

**VERDICT: NOT STEADY — the submission verifier, ladder accounting, and tier gate each admit a concrete letter-of-the-rule bypass.**

**First defect to fix:** bind every submission verifier run to the exact immutable instance named by the submitted claim.

**FRAMING:** “the whole research history is one replayable-or-verifiable DAG” is overstated because the schema explicitly admits `AuditOnly` nodes. It should say “the admissible evidence subgraph.” The broader honest-baseline framing is sound.

**Facts needed:** whether laddered methods receive transparent curve coordinates; whether any generic verifier-admission registry already exists outside this text; and whether the scheduler already has a batch/fan-out identity suitable for aggregate tiering.