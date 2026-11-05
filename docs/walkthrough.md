# Walkthrough

This is an outline for a 20 to 25 minute technical presentation. Each section says what to cover and what to show. The numbers come from the fixed Experiment in `experiments/default_experiment_results.json`, the calibration test case, and the restart witness record in `docs/cpoc/`.

The line that connects the sections is this. An exact projection of the committed state leads to a decision. The decision leads to a realized result. The gap between projection and result is measured, and that measurement says whether more prediction is worth building.

## 1. Problem (2 minutes)

Passengers request a ride with an origin and a destination. The dispatcher assigns a car at once, cannot see future requests, and has to respect capacity and direction. Wait and total time are the objectives. I treated the exercise as three separate pieces. They are the rules of motion, the decision, and the measurement of the decision.

Show the screenshot in the README.

## 2. Ambiguities I resolved (3 minutes)

The brief does not say what order things happen in within a tick, which direction a passenger may board, or what a car does at the end of its sweep. I fixed these before writing any policy.

The tick has nine steps in a fixed order, and positions are logged at the start of the tick. A passenger boards only a car that leaves in the passenger's direction. A car at the end of its sweep is free, and the first passenger who boards sets its direction. Without that rule, two passengers who want opposite directions can leave a car turning back and forth forever. Assignments are final, and ties go to the lowest car id.

Show the tick diagram and the end-of-sweep example in `docs/design.md`.

## 3. Scheduler design (4 minutes)

Round Robin and Nearest Car are the baselines. Cost Based projects each car's route with and without the new passenger. The projection uses the same movement functions as the engine, so it is exact for the current committed state. Later assignments can change the route, which the calibration section measures. The cost combines the new passenger's wait, a penalty on waits longer than one sweep, and the effect on passengers already assigned. A car that creates a new capacity deferral is considered only if every car would.

The policy proposes and the engine commits. A policy cannot change state, cannot see the future and keeps nothing between calls.

Show the decision flow diagram and the worked example where Nearest Car and Cost Based choose different cars.

## 4. Evaluation (3 minutes)

One run proves little, so I ran a paired Monte Carlo evaluation. I generated demand in nine patterns with 20 seeds each and ran all three policies on the same Trace for every pattern and seed. That gives 180 paired seeds and 540 runs, and none halted. I fixed the parameters before any result existed. The generator sits outside the decision path, so a policy sees a request only at its request time.

Show the pairing diagram.

## 5. Results (4 minutes)

Use the table in the README. Cost Based has the lowest p95 wait in eight of nine patterns. In the sparse pattern it matches Nearest Car on all 20 seeds. Nearest Car has a lower mean wait than Round Robin on the uniform pattern and a higher p95 wait, which is why I report the tail next to the mean. Capacity stress is the closest comparison with Round Robin, with a mean p95 difference of -0.2 ticks, and Cost Based has a lower maximum wait on all 20 seeds there. Concentrated origin is the pattern where Cost Based loses seeds to Round Robin.

## 6. Calibration (3 minutes)

Walk through the committed case. Passenger r0 is projected to board at tick 6 and arrive at tick 7. A later passenger is assigned to the same car, the route changes, and r0 boards at tick 16 and arrives at tick 17. The errors are +10 and +10. The first projection was exact for what the policy knew, and the error comes from information that arrived afterward.

In the reporting test sweep, 603 assignments had a later assignment to the same car and 30 of them differed from the projection. That is the measurement that decides whether a demand forecast is worth building.

Show the calibration table in the web demo.

## 7. Restart proof (2 minutes)

A run checkpoints at tick 12 and the process is killed. A new process resumes from the saved Snapshot and executes only ticks 12 onward. It finishes with a Simulation History and eight output files identical to an uninterrupted run. The operational log is one continuous sequence, and a finished run cannot be reopened. The evidence covers a local Store on one machine.

## 8. Demo (3 minutes)

Run `python -B -m web`. Start a Cost Based run on the built-in example, step a few ticks, run to the end, move the history slider, open the receipt for one assignment and press Compare policies. Then open the Evaluate page.

## 9. Next steps (1 minute)

Measure whether a demand forecast has positive value using the calibration error. Add door and dwell times. Fit the demand patterns to real building traffic. Evaluate maintenance inputs only if car availability changes dispatch quality. Optimize speed only if building size requires it.

## Whiteboard version

Draw five boxes and keep the arrows few.

1. Requests flow into the engine.
2. The engine builds a SchedulerView and sends it to the policy.
3. The policy returns a proposed car, and the engine validates and commits it.
4. The engine writes the Simulation History, and the reports read only the History.
5. The evaluation harness sits to the side and feeds generated Traces into the engine, never into the policy.

Then draw the continuation path separately. The engine writes a Snapshot to the Store, and a new process reads the Snapshot and resumes.

## Questions to expect

**Why is the tick in this order?** Assignment comes before boarding, so a passenger who arrives at a floor where a car already stands can board in the same tick. Recording comes before the move, so the log shows start-of-tick positions.

**What is authoritative state?** The positions and headings of the cars and the standing of each passenger, held by the engine. Loads, routes and reports are computed from them.

**Why can the scheduler not look ahead?** The brief forbids it, and the SchedulerView contains only revealed requests. A test adds a later request and checks that every earlier decision is unchanged.

**What happens on a bad proposal?** The run halts with a named reason. The engine never repairs or replaces a policy's answer.

**How do you know Cost Based beats a baseline?** I compare the policies on identical Traces, pattern by pattern, and report tail and maximum waits next to the mean. It does not win everywhere, and the results say where.

**What does restart safety mean here?** The run continues from saved state without replaying from tick 0. I tested it by killing a real process and comparing the resumed result with an uninterrupted run.

**Which assumptions are simplifications?** Door and dwell times are zero, the demand patterns are synthetic, the cost weights are fixed, and storage is a local directory.
