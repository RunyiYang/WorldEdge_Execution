# WorldEdge Execution

Experimental protocol and execution tools for sustained robot deployment and
control-conditioned video prediction in generated worlds.

This repository is the implementation handoff for **Table 4: Robot policy
evaluation** and **Table 5: Video world model evaluation**. It includes the
complete experimental setting, typed evidence formats, runnable CPU tooling,
metric checks and clean LaTeX tables.

## Start here

- [Complete experimental protocol](docs/EXPERIMENT_PROTOCOL.md)
- [Implementation milestones](docs/ROADMAP.md)
- [中文执行入口](docs/QUICKSTART_ZH.md)
- [Native simulator and model integration](docs/ADAPTERS.md)
- [Evidence and scoring formats](docs/DATA_FORMATS.md)
- [Experiment configuration](configs/experiment.yaml)
- [Paper setting](paper/experimental_setting.tex) and [table templates](paper/worldedge_policy_tables.tex)
- [Source references and inspection scope](docs/SOURCES.txt)

## Implementation status

| Component | Status |
|---|---|
| Experimental setting, populations and fixed denominators | Specified |
| Configuration validation and budget planning | Implemented |
| JSON/JSONL schema validation | Implemented |
| Scheduled policy/video score aggregation | Implemented |
| Coverage-aware CSV and LaTeX table export | Implemented |
| Synthetic metric and invalid-input checks | Implemented |
| Generated-room physics compilation and persistent lifetime runner | Integration required |
| Native RoboDojo/EBench policy adapters | Integration required |
| Target-ARX video-WM collection, adaptation and forecasting | Integration required |
| Visual reader calibration and human audit | Required before semantic result publication |
| World-cluster confidence intervals and paired comparisons | Integration required |

The repository contains no measured policy/WM results or model weights.
The implemented commands do not launch a simulator or train a model.
Future backend commands in the protocol are implementation contracts.

## Install

Use Python 3.10 or newer in a dedicated environment:

```bash
git clone https://github.com/RunyiYang/WorldEdge_Execution.git
cd WorldEdge_Execution
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

The CPU tools depend only on PyYAML and jsonschema. Native simulator and model
dependencies belong in their own compatible environments.

## Commands available now

### 1. Check the code and inspect the planned budget

```bash
python -m unittest discover -s tests -v
python -m worldedge_eval plan \
  --config configs/experiment.yaml \
  --output runs/plan.json
```

The default plan gives:

- 30 test worlds × 2 seeds × 10 tasks per policy and setting.
- Five Manipulation rows and four Mobile Manipulation rows.
- 540 lifetimes, at most 5,400 tasks and 300 scored simulation hours.
- 330 accepted test room outputs, or 590 including the specified development
  and WM training populations.
- 3,200/400/600 WM train/development/test reference clips.
- 1,200 test predictions per WM and 2,400 for the two primary 2B models.

These are planned counts. Wall time and GPU-hours require a development pilot.

### 2. Find unresolved configuration fields

```bash
python -m worldedge_eval preflight \
  --config configs/experiment.yaml \
  --output runs/preflight.json
```

The initial configuration intentionally contains unresolved source, checkpoint,
action, threshold and evidence manifests. Preflight exits with status **2**
until required configuration fields are resolved. Inspect its JSON report.
Never replace these fields with invented hashes or placeholder paths to get
a passing status.

A complete configuration does not prove that a checkpoint loads, an artifact
exists or physics is valid. Those checks belong to the integration gates.

### 3. Validate a full evidence record

```bash
python -m worldedge_eval validate \
  --schema schemas/policy_run.schema.json \
  --input /path/to/policy_run.json
```

The input can be one JSON object, a JSON array of records, or JSONL.
Use the corresponding schema for world bundles, model manifests or WM cases.
Schema validation checks structure. It does not validate file hashes or
physical events.

### 4. Score completed records against a frozen schedule

The compact scorer inputs are described in [DATA_FORMATS](docs/DATA_FORMATS.md).
They are exported from the full evidence records and are not interchangeable
with those full schemas.

```bash
python -m worldedge_eval score-policy \
  --manifest /path/to/policy_schedule.jsonl \
  --records /path/to/policy_outcomes.jsonl \
  --model pi05_robodojo \
  --output runs/scores/pi05_robodojo.json

python -m worldedge_eval score-video \
  --manifest /path/to/wm_cases.jsonl \
  --records /path/to/dreamdojo_outputs.jsonl \
  --model dreamdojo_2b \
  --model-seeds 0 1 \
  --output runs/scores/dreamdojo_2b.json
```

Missing output records remain visible. Policy infrastructure gaps do not
produce a publishable mean over a smaller sample. Video unknowns are incorrect
for both outcome classes, and unavailable LPIPS values invalidate that
horizon's complete aggregate. Scoring writes diagnostics and exits with
status 2 when the requested row is not reportable.

### 5. Export clean tables

Create blank templates for the enabled roster:

```bash
python -m worldedge_eval tables \
  --config configs/experiment.yaml \
  --output-dir runs/table_templates
```

Then pass actual score files:

```bash
python -m worldedge_eval tables \
  --config configs/experiment.yaml \
  --policy-scores runs/scores/pi05_robodojo.json \
  --video-scores runs/scores/dreamdojo_2b.json \
  --output-dir runs/tables
```

This writes Table 4/5 CSV and LaTeX plus a coverage report. Unrun rows remain
`--`. Incomplete rows are `NR`. Configured population/seed counts are checked.
Once every enabled row is available, add `--require-complete` to reject any
missing or incomplete row before final export.

These exports contain point estimates. Complete the protocol's independent
physics/annotation audits and world-cluster statistical analysis before
publication. A score file alone is not the full experimental evidence.

The paper templates use only `booktabs`; the setting uses `amsmath`.
`paper/preview.tex` is a minimal compilation entry point. The source has not
been visually compiled as part of this repository handoff.

## Experiment rules

**Table 4.** Preserve actual state throughout ten tasks, including failures.
Keep room additions and task schedules matched across policies. Evaluate
success from simulator state and event traces. Reuse pairs are (1,4), (4,7)
and (7,10), with all scheduled pairs in the denominator.

**Table 5.** Adapt the two primary video models to the same target embodiment,
then freeze them. Collect real 10 Hz command-replay references. Condition on
initial RGB and issued controls without future GT refresh. Outcome refers to
a declared 30-second stage goal. Revisit evaluates actual changed state,
including an incorrect placement in a failed task branch.

The adaptive success/failure-driven generation demo is a separate stream.
Its evolving task distribution is not mixed into the matched policy table.

## Coding-agent handoff

Read [AGENTS.md](AGENTS.md), the protocol and the roadmap. Start with native
interface verification on two development worlds. Resolve the existing
reset-per-attempt/failed-state contract before implementing the persistent
lifetime runner. Integrate actual model and physics outputs into the evidence
formats and use the existing schedule reconciliation.

Keep checkpoints, datasets, generated videos and run artifacts outside Git.
Store their paths, hashes and provenance in versioned manifests when those
artifacts exist. No API keys or machine-specific credentials belong here.
