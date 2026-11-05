# Presentation Guidance for the Public Repository

Status: **OWNER DIRECTION, recorded 2026-11-05. A record, not doctrine. It governs the shape of the public deliverable (plan cut 12); it changes no simulation rule.**

The public repository should read like a technical argument with
executable proof, not like a code dump. The implementation demonstrates
that the design survives contact with reality; the explanation is what
lets a reviewer see how the author thinks. Optimise the finished
repository for explainability first, implementation second, governance
history third. The code is there to make the explanation credible.

## The five questions the public repo answers, in order

1. **What problem did you think you were solving?** Destination dispatch
   under discrete-time, capacity, direction, no-look-ahead and
   immediate-assignment constraints.
2. **What decisions did you make where the brief was ambiguous?** Tick
   order, boarding direction, reversal behaviour, capacity deferral,
   tie-breaking, output semantics.
3. **How does the scheduler work?** Baselines first, then the cost-based
   policy, why those cost terms exist, and why demand forecasting and
   global optimisation were deliberately not used.
4. **How did you establish that it works?** Invariants, worked examples,
   adversarial cases, Monte Carlo comparisons, the liveness argument, the
   restart witness.
5. **What did you learn?** Where the heuristic wins, where it does not,
   tail behaviour, fairness trade-offs, what would be improved with more
   time.

## Final README shape (an engineering memo, not a normal README)

```text
README
├── 1. Problem and interpretation
├── 2. Design decisions
├── 3. Architecture
├── 4. Scheduling policies
├── 5. Evaluation methodology
├── 6. Results
├── 7. Correctness and edge cases
├── 8. Running the project
└── 9. What I would do next
```

Keep the implementation compact underneath it.

## One public design document

The public repo carries one design document with diagrams and a few
carefully chosen worked examples, rather than exposing the full
constitutional history. The internal corpus (`docs/` as it stands:
constitution, authority model, audits, decisions, repair records) remains
as development evidence; the reviewer should not have to understand OSA
vocabulary before they understand an elevator.

## How the signature appears, without the acronyms

- AIE appears as "which computation is actually worth doing before
  assignment?"
- Monte Carlo appears as "I tested the heuristic across demand regimes
  rather than one trace."
- OSA appears as "the scheduler proposes; the engine owns and commits
  state."
- CPOC appears as "restart correctness means continuation from durable
  state, not replaying from zero."

## Consequences for the plan

Cut 12 produces: the memo-shaped README above; one public design document
(`docs/design.md` or similar) distilled from the governing set with
diagrams and selected worked examples (W-A, W-B, W-C, W-G, W-D at least);
the results section from the committed Experiment; and the walkthrough.
The governing documents are not rewritten for the public reader; they are
linked from the design document as development evidence for those who want
it.

## The interview story (owner note, 2026-11-05)

The finished repo hides the process complexity and showcases the
engineering outcome. What the process buys in the interview is not "look
how much documentation I wrote" but a system where, when probed, the
answers are crisp:

- Why is the tick order this way?
- What exactly is authoritative state?
- Why can't the scheduler peek ahead?
- What happens on a bad assignment proposal?
- How do you know the cost-based policy is better than a baseline?
- What does restart safety actually mean?
- Which assumptions are deliberate simplifications?
- What would you change with more time?

Because those questions were forced early, the author should be hard to
knock off balance. The main risk is presentation: a reviewer who opens the
repo and immediately sees a governance cathedral may hold it against the
work. The final public surface should make the project look simple,
deliberate and empirically evaluated; the deeper doctrine is there only if
someone wants to inspect it.

The strongest onsite story:

> I treated the take-home as a small decision system rather than just a
> routing exercise. I pinned the simulation semantics first, separated the
> scheduler from authoritative state, tested the policy against baselines
> over controlled demand scenarios, and added a bounded restart witness so
> I could distinguish correct continuation from simply rerunning the
> simulation.

That carries AIE, OSA, Monte Carlo and CPOC in one coherent engineering
story without sounding like a compliance framework built around elevators.
