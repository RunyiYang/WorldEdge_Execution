# Data formats

The repository uses two record layers. **Full records preserve experimental evidence. Compact JSONL exports feed the scoring CLI.** A compact export is not a substitute for the full records, and the four full-record schemas do not validate compact scorer inputs.

All records use UTF-8 JSON. JSONL files contain one JSON object per line, without a header or comments. Use JSON `null` for unavailable values. Do not use `NaN`, infinity, an empty string, or `"NR"` as a numeric value.

## Full records and schemas

| Schema | Record purpose | Required evidence |
|---|---|---|
| [world_bundle.schema.json](../schemas/world_bundle.schema.json) | A generated world and its immutable ten-task schedule | Source group and split, native embodiment, asset references, ten ordered tasks, predicate references, deadlines, reuse anchors, append manifest and admission report |
| [policy_run.schema.json](../schemas/policy_run.schema.json) | One complete scheduled policy lifetime | Model/world identity, seeds, run status, ten round slots, issued instructions, deadlines, actual state hashes, executed-action logs and independent goal traces |
| [wm_case.schema.json](../schemas/wm_case.schema.json) | One simulator reference clip and its control contract | Snapshot, issued commands, separate realized reference logs, camera/timestamps, stage goal, actual reference outcome, category and optional revisit metadata |
| [model_manifest.schema.json](../schemas/model_manifest.schema.json) | Candidate-to-frozen model provenance | Checkpoint source/hash, source commits, observation/action contracts, interface gate, declared adaptation and unresolved items |

Full records refer to larger artifacts through `{ "path": "...", "sha256": "..." }`. Hash the actual content. Pinned worlds and frozen model manifests require real hashes. Draft/candidate records may have explicitly unresolved fields where their schema permits them. Do not invent values to pass validation.

The WM case categories are `placement`, `sorting`, `multiobject_ordering`, and `delayed_revisit`. Only the final category has a non-null `revisit` object. In the default test population, 180 of 600 clips are revisit cases.

Validate full records with:

```bash
python -m worldedge_eval validate \
  --schema schemas/policy_run.schema.json \
  --input /path/to/full_policy_run.json
```

The input may also be a JSONL file of full records. Structural validation cannot establish that referenced files exist, hashes match, physics was executed, split groups are disjoint, or timestamps agree. The adapter/exporter must check these separately.

## Table 4: compact policy inputs

### Frozen schedule: `policy_schedule.jsonl`

Create the schedule before execution. Each row identifies one planned lifetime.

| Field | Type | Meaning |
|---|---|---|
| `run_id` | Nonempty string | Unique lifetime identifier |
| `model_id` | Nonempty string | Benchmark model row ID from the frozen manifest |
| `setting` | String | `manipulation` or `mobile_manipulation` |
| `world_id` | Nonempty string | Full record's `world_bundle_id` |
| `source_group_id` | Nonempty string | Independent source group used for uncertainty and leakage audits |
| `seed` | Nonnegative integer | Scheduled repeat seed, normally 0 or 1 |

The export must resolve `seed` through the frozen run schedule. Do not silently pick either `environment_seed` or `policy_seed` when a full record contains different values. The schedule defines their mapping to a repeat.

### Execution export: `policy_outcomes.jsonl`

Use the same six identity fields, plus:

| Field | Type | Meaning |
|---|---|---|
| `status` | String | `completed`, `terminated_policy`, or `incomplete_infrastructure` |
| `successes` | Array of exactly ten integers | Ordered binary round outcomes, each 0 or 1 |

`completed` means the scheduled lifetime was accounted for. It does not mean all ten tasks succeeded. `terminated_policy` is a scored policy termination: retain all ten slots and put zero in unattempted slots. `incomplete_infrastructure` identifies an interrupted experiment; it must remain explicit and prevents a complete headline result until reconciled under the fixed retry policy.

The full record retains the reason for every unattempted round. Compact zeros do not remove that requirement. A nonfatal task failure does not end the schedule: later successes still count in Tasks/10. A policy-induced fatal state leaves zero outcomes for remaining rounds.

**Synthetic documentation example only.** These records do not describe a real checkpoint, execution or measured result. They are deliberately incomplete as a benchmark population and must not be placed in `results/`.

Schedule line:

```json
{"run_id":"SYNTHETIC_RUN","model_id":"SYNTHETIC_POLICY","setting":"manipulation","world_id":"SYNTHETIC_WORLD","source_group_id":"SYNTHETIC_GROUP","seed":0}
```

Matching outcome line:

```json
{"run_id":"SYNTHETIC_RUN","model_id":"SYNTHETIC_POLICY","setting":"manipulation","world_id":"SYNTHETIC_WORLD","source_group_id":"SYNTHETIC_GROUP","seed":0,"status":"terminated_policy","successes":[0,0,0,0,0,0,0,0,0,0]}
```

Score actual exports with:

```bash
python -m worldedge_eval score-policy \
  --manifest /path/to/policy_schedule.jsonl \
  --records /path/to/policy_outcomes.jsonl \
  --model pi05_robodojo \
  --output runs/scores/pi05.json
```

The manifest establishes the denominator. Reconcile all scheduled IDs before reducing outcomes. Duplicate, unexpected or conflicting records are errors; a missing lifetime must not become an omitted denominator entry. Preserve source groups when exporting values for paired cluster analysis.

Metric interpretation:

- **SR@5:** all first five rounds succeed.
- **SR@10:** all ten rounds succeed.
- **Tasks/10:** the mean number of successful rounds, including successes after earlier failures.
- **Reuse:** both endpoints succeed for each fixed pair `(1,4)`, `(4,7)`, `(7,10)`. An earlier failure does not remove its pair from the denominator.

## Table 5: compact video inputs

### Independent reference manifest: `wm_cases.jsonl`

This is a compact manifest, not a JSONL dump of full `wm_case` objects.

| Field | Type | Meaning |
|---|---|---|
| `world_id` | Nonempty string | Source world/bundle identifier |
| `clip_id` | Nonempty string | Full case's `case_id` |
| `ref_outcome` | Integer 0 or 1 | Actual simulator outcome of the declared thirty-second stage |
| `revisit_expected` | Boolean | Whether this scheduled clip belongs to `delayed_revisit` |
| `source_group_id` | Nonempty string, optional | Parent group if clustering must be broader than `world_id` |

Map full `reference_outcome.status=success` to 1, and `failure` or `partial` to 0. This is the reference stage outcome, not whether a longer parent task might eventually finish. Map `category=delayed_revisit` to `revisit_expected=true`; all other categories map to false.

If several worlds derive from one source, preserve `source_group_id` through downstream analysis. Do not pretend their clips are independent worlds.

### Prediction export: `wm_outputs.jsonl`

One row represents one scheduled model/world/clip/generation-seed combination.

| Field | Type | Meaning |
|---|---|---|
| `model_id` | Nonempty string | Benchmark model row ID |
| `world_id`, `clip_id` | Nonempty strings | Join to the independent reference manifest |
| `model_seed` | Nonnegative integer | Scheduled prediction seed, normally 0 or 1 |
| `ref_outcome` | Integer 0 or 1 | Copied reference label; must match the manifest |
| `revisit_expected` | Boolean | Copied case flag; must match the manifest |
| `pred_outcome` | String | Independent reader label: `success`, `failure`, or `unknown` |
| `valid_video` | Boolean | Whether the output satisfies the declared decoding, frame and timestamp contract |
| `revisit_correct` | Boolean or null | Independent revisit judgment; use null for a non-revisit case or a missing judgment |
| `lpips5`, `lpips30` | Finite nonnegative number or null | Endpoint LPIPS at 5 s and 30 s, not an interval average |

The exporter should always write the final three fields explicitly. The reference reduction also treats absent values as unavailable. A visually wrong but decodable video is not automatically structurally invalid: its semantic error belongs in the independent reader labels. `pred_outcome` must not be copied from the generator's own success claim.

**Synthetic shape examples only, not results.** A one-clip example is insufficient for balanced outcome accuracy or a complete benchmark.

Reference-manifest line:

```json
{"world_id":"SYNTHETIC_WORLD","clip_id":"SYNTHETIC_CLIP","ref_outcome":0,"revisit_expected":true,"source_group_id":"SYNTHETIC_GROUP"}
```

Prediction-export line:

```json
{"model_id":"SYNTHETIC_VIDEO_MODEL","world_id":"SYNTHETIC_WORLD","clip_id":"SYNTHETIC_CLIP","model_seed":0,"ref_outcome":0,"revisit_expected":true,"pred_outcome":"unknown","valid_video":false,"revisit_correct":null,"lpips5":null,"lpips30":null}
```

Score actual exports with:

```bash
python -m worldedge_eval score-video \
  --manifest /path/to/wm_cases.jsonl \
  --records /path/to/wm_outputs.jsonl \
  --model dreamdojo_2b \
  --model-seeds 0 1 \
  --output runs/scores/dreamdojo.json
```

The two default model seeds are scheduled for every manifest clip. Average seeds within each clip before aggregating clips. Never select a preferred generated sample.

Important reduction rules:

- Outcome is balanced accuracy over actual positive and negative stage outcomes. An `unknown` prediction is incorrect for either class.
- Invalid or missing videos are incorrect for Outcome and Revisit, regardless of any supplied prediction label.
- All scheduled revisit clips remain in the Revisit denominator. Do not condition it on successful actions or valid outputs.
- A missing endpoint value makes that model's corresponding aggregate LPIPS horizon unavailable. Do not substitute zero, a fabricated worst score, or an average over completed outputs only.
- Missing outputs remain scheduled and make coverage incomplete. A present-but-invalid output is distinguishable from a missing record.
- Duplicate clip/seed outputs, unscheduled seeds/clips, and copied labels that conflict with the reference manifest are errors.

## Export boundary and completeness

The full-record exporter is part of the simulator/model integration work described in [ADAPTERS.md](ADAPTERS.md). The scoring commands operate on compact exports; they do not generate worlds, run checkpoints, compute video annotations, or verify that the recorded physics actually happened.

Before exporting, validate full records, resolve artifact hashes, reconcile the frozen schedule, and preserve the mapping from every compact row to its complete evidence. Do not infer coverage from whatever files happen to exist in an output directory.

Keep raw evidence and compact exports separate. Documentation examples and synthetic test fixtures must stay outside measured result directories. A completed scoring command establishes a reduction over the supplied inputs, not completion of the experiment.
