# Documentation index

## Start here

[design.md](design.md) explains the rules, the cost-based decision and the continuation design with diagrams and worked examples. [walkthrough.md](walkthrough.md) is the presentation outline and the interview notes.

## Evidence

The fixed Experiment results quoted in the README are in [../experiments/default_experiment_results.json](../experiments/default_experiment_results.json). The record of the restart witness, with process ids, hashes and comparison results, is in [cpoc/](cpoc/). The [implementation/](implementation/) directory holds one record per build stage with the tests that were run. The most useful to read are the records for the scheduler ([cut_05_cost_based_scheduler.md](implementation/cut_05_cost_based_scheduler.md)), reporting and calibration ([cut_06_reporting_calibration.md](implementation/cut_06_reporting_calibration.md)) and the restart witness ([cut_10_cpoc_witness.md](implementation/cut_10_cpoc_witness.md)).

## Development record

The remaining files in this directory record the specification and the review process used while building the project. They are not required to understand or run the solution. They stay in place because the owner decision records name them by exact path and digest.

The specification files are constitution.md, authority_model.md, simulation_semantics.md, scheduler_design.md, evaluation_design.md, cpoc_design.md, ui_design.md, architecture.md, testing_contract.md and worked_examples.md. The process files are in decisions/, audits/ and plans/, along with current_work.md, assumptions_and_tradeoffs.md, doctrine_adoption.md and presentation_guidance.md. The file [../AGENTS.md](../AGENTS.md) routes each question to the file that owns it.
