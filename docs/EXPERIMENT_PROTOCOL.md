# WORLDGROW / WORLDEDGE: COMPLETE DOWNSTREAM EXPERIMENTAL SETTING

> Implementation status: the repository currently provides configuration validation, budget planning, schema validation, scheduled-run scoring and table export. Native simulator/policy adapters and video collection/training/forecast execution remain integration milestones. See [README](../README.md) and [ROADMAP](ROADMAP.md).

Protocol: worldedge_downstream_v1
Status: proposed implementation specification; no experimental results exist in this package.
Audience: the coding agent implementing and running Tables 4 and 5.
The manuscript currently uses WorldEdge table labels; preserve those cross-references.

## 1. OBJECTIVE AND SCOPE

Implement two separate, reproducible studies:
A. Table 4: sustained execution by frozen robot policies in generated worlds.
B. Table 5: control-conditioned video prediction by target-robot-adapted video world models.

The main scientific claim is that generated worlds support sustained, stateful interaction and expose long-horizon execution/prediction failures. This study does not establish that a frozen robot policy learns from feedback, that a video predictor improves planning, or that a finite ten-task test proves literally infinite deployment.

Keep the paper tables compact. Table 4 has SR@5, SR@10, Tasks/10 and Reuse. Table 5 has endpoint LPIPS at 5 s and 30 s, Outcome and Revisit. Runtime, confidence intervals, acceptance yield, annotation quality and coverage belong in supplementary artifacts.

The configuration in configs/experiment.yaml contains proposed defaults. Resolve the explicitly null manifests from real installed code and hardware. Do not invent checkpoint identifiers, action dimensions, benchmark scores, human annotations or execution claims. New CLI commands listed below are implementation targets, not commands already supplied by the inspected repositories.

## 2. SOURCE AUDIT AND EXISTING IMPLEMENTATION GAPS

Read docs/SOURCES.txt and inspect the actual repository revision before modifying it.
The requested Slian22/infinite-task-world URL returned 404 through the available access route. The inspected accessible fork is RunyiYang/infinite-task-world at 4478db064767690ce4d6a6553a4fb1a4d588a3ca. Reconcile it with the team's actual source rather than assuming it is the latest upstream.

At that inspected revision:
- embodied_gen/world/pipeline/session.py accepts only reset_each_attempt and rejects a failed execution that changes the canonical world. The desired protocol needs a reset-free lifetime mode and persistence of every physically valid terminal state, including partial/failed outcomes.
- embodied_gen/world/robot_eval.py contains an OraclePolicy that teleports objects and settles them. It is not a learned robot rollout or a valid manipulation feasibility demonstration.
- worldedge/executor.py has a genuine action-stepping path for a small native task, but that does not establish generated-room deployment for the required embodiments.
- Agent receipts, planner outputs and controller success flags are not independent physical success evidence.
- Goal conjunctions alone cannot verify temporally ordered instructions; add a trace monitor.

The inspected RoomGenBench revision is 30f2e059d046ccd4aa928d0109a09a52f11693b5. It provides room/asset generation and static geometry scoring. Its assembly uses scaled meshes and closed rigid door panels. Build an explicit simulator compilation layer. Preserve movable instance identities; recompute collision geometry and inertia after scaling; ensure open corridors actually have traversable collision geometry. A visually open-looking container with a solid convex collision hull is invalid for containment.

Implement the new protocol alongside existing benchmark modes. Do not silently alter native benchmark semantics or report their old results as WorldEdge results.

## 3. STAGES, STOP CONDITIONS AND DELIVERABLES

G0 Source and dependency audit:
Pin source commits, simulator containers, CUDA/PyTorch versions, robot assets, policy/model weights, native normalization statistics and any paid/remote services. Produce source_lock.json, model_manifests/ and blockers.json. A model row begins as candidate, becomes interface_passed after a real development rollout, and becomes frozen only when all required identities/configurations are pinned.

G1 Native interface verification:
Load each intended checkpoint on its documented embodiment. Verify observations, action semantics, direction/scale, gripper behavior, clipping, timestamps and inference chunks. The adapter may perform deterministic formatting/coordinate/normalization conversions. It must not replace predicted actions with oracle pick/place or navigation. If a planner/skill controller is part of the deployed system, label the whole system and apply the declared helper consistently.

G2 Environment compilation and state persistence:
Compile generated assets, validate physics and task feasibility, and verify append-only growth. Keep generation failures and their causes. A valid reference must execute through the real actuator/controller interface or teleoperation. Object teleportation does not demonstrate feasibility.

If the native simulator cannot add actors after initialization, the finite fixed-stream benchmark may preallocate future-room entities and activate them at the scheduled boundary. They must be absent from rendering, collision, policy observations and controller/perception state before activation. Declare growth_runtime_mode=preallocated_activation and verify equivalence to the intended room-availability schedule. This demonstrates deployment under scheduled growth, not arbitrary live simulator insertion. A live adaptive-generation demonstration needs its own validated loading path. Never reset old-world physical state to work around a loader limitation.

G3 Evaluator verification:
Implement simulator predicates, temporal ordering, frozen denominators and video readout controls. Pass the metric fixture checks included in this package, plus the physical/leakage tests below.

G4 Development pilot:
Use two smoke-test and six additional development worlds per setting. These eight manipulation worlds may be a subset of the twenty video-WM development worlds. Estimate memory, latency, rollout cost, generation yield and semantic readout reliability. Adjust budgets/thresholds only here, record the change, and regenerate the frozen configuration.

G5 Protocol freeze:
Hash the admitted world/task manifests, source/model manifests, split membership, reference branches, thresholds, budgets, inference settings and analysis code. Record the freeze before running test policies or test video predictions. The current inspected defaults are proposals, not already frozen experiments.

G6 Scheduled execution:
Run every scheduled unit. Do not stop after a favorable score, remove hard worlds, rewrite failed goals or select the best seed. Execute independent branches in isolated native environments if simulator versions differ.

G7 Scoring and reporting:
Aggregate exclusively from immutable run artifacts. Complete the annotation audit. Export table4.csv, table5.csv, the two table fragments, world-cluster confidence intervals, raw denominators, coverage, failure breakdowns and resource reports. Incomplete infrastructure runs must be explicit. No final score may be fabricated to fill a table.

An unresolved field blocks only the relevant stage/branch. Continue other authorized work and emit a concrete blocker with the missing artifact or failed check. Do not compensate by changing the embodiment, hiding adaptation, expanding the budget or substituting symbolic execution.

## 4. WORLD POPULATION AND SPLITS

Table 4, per embodiment:
- 30 independent test world bundles.
- Two rollout seeds: 0 and 1.
- Ten consecutive scheduled tasks per lifetime.
- Three task families, ten test worlds each: delivery/recollection, sorting/reorganization, multi-object staging/cleanup.
- Eight development worlds, separate from test.

Manipulation has one generated room/workspace per bundle. Mobile Manipulation has ten connected rooms: R1 is the seed room for task 1, and R2 through R10 are appended before tasks 2 through 10. Do not add an uncounted foyer. Every mobile task must use the newly available room.

The two rollout seeds reuse the exact same geometry, object instances, task goals and room append manifest. They change only declared policy/physics random streams. If a component is deterministic, disclose that the repeat adds no new scene diversity.

Table 5, primary manipulation embodiment:
- Train: 160 world groups x 20 clips = 3,200 clips.
- Development: 20 groups x 20 clips = 400 clips.
- Test: the same 30 manipulation world groups used by Table 4 x 20 clips = 600 clips.
- Two generation seeds, 0 and 1.

A group contains the full source world and all derived snapshots, paraphrases, camera variants, action branches and mesh derivatives. Split groups before collecting clips. Exact generated instance assets must not cross train/development/test. Sharing robot assets and fixed generic construction primitives is permitted. Object categories may repeat. Audit geometry/content hashes and source lineage.

This is held-out evaluation relative to this experiment's training and development data. Do not claim disjointness from every foundation model's unknown pretraining corpus.

WM test worlds can share Table 4 environments, but Table 5 is a separate controlled replay dataset. Do not tune policies on these clips, train WMs on test-policy trajectories, or select WM checkpoints using test outcomes.

## 5. TASK GENERATION AND ADMISSION

For the main protocol, use rigid-object pick/place, visible containment in open receptacles, sorting, rearrangement, transport and delayed reuse. Exclude articulated opening, deformables, pouring and precision insertion until their physical assets/controllers/evaluators pass a separately registered extension. A decorative mesh cabinet door is not an articulated task.

Generate complete task/room streams before comparing policies. Use a nominal physically executed reference trajectory to construct a consistent growth schedule. Every evaluated policy gets its own branch of the same frozen stream, but its physical state is allowed to diverge.

Admission must verify:
- units, axis conventions, transforms, scale and source IDs;
- separate dynamic movable objects and appropriate collision decomposition;
- declared masses/friction/inertia and stable initial supports;
- robot spawn/approach clearance, reachability and traversable mobile portals;
- goal support size and visible, meaningful target regions;
- no unintended task precompletion along the nominal reference;
- actual reference execution of the ten-round sequence under the proposed physical deadlines;
- task text is grounded in perceptually identifiable objects;
- no tested policy's success is used as the admission criterion;
- growth preserves all old entities, object/robot poses, velocities and joint states.

A maximum of five candidate bundle attempts per requested slot is the proposed generation cap. Retain rejected candidates and reasons. A ten-room bundle may require multiple room-generation calls; record both bundle-level and room-level counts. If the cap is exhausted, mark a construction blocker; never silently reduce the test denominator. Room counts stated below refer to accepted outputs only, not generation attempts.

Imported replacement assets are allowed for interface debugging. Primary result assets must have the declared generated provenance; if replacements remain, label the evaluated mixture and report its frequency.

Frozen primary thresholds:
Use a two-second stable dwell for policy placement. Starting development tolerances are support/contact gap <=2 cm, object linear speed <=5 cm/s, angular speed <=0.2 rad/s, and a 1 cm target-footprint margin. Validate these against object scale, contact geometry and the native simulator; freeze an explicit threshold manifest before test evaluation. A gap test alone is not sufficient support: require actual supporting contact or a verified support relation, released gripper state and the task's containment/placement geometry.

For containment, use the correct object volume/footprint inside a defined visible receptacle region, not only distance between bounding-box centers. For grasp/carry ordering, use real contact/motion events. If relevant native predicates exist, audit and reuse them with their exact tolerances.

## 6. TABLE 4: POLICIES, LIFETIME EXECUTION AND TASKS

Candidate frozen rows:
Manipulation / dual ARX X5:
  pi0.5, GR00T N1.7, InternVLA-A1, OpenWAM-alpha, InternW0-Delta.
Mobile Manipulation / Lift2 with R5a arms:
  pi0.5, pi0, InternVLA-A1, OpenWAM-alpha.

Use native RoboDojo/EBench-compatible released checkpoints and verify their actual availability. For OpenWAM use the corresponding Sim-RoboDojo or Sim-EBench checkpoint, not a similarly named real-robot release. Record exact hashes rather than only family names. The row list is a planned run roster, not proof that these models already run inside the generated environments. No WorldEdge robot-policy fine-tuning is included.

"Workstation (dual ARX X5)" denotes a fixed-base dual-arm manipulation platform. It is an embodiment, not a task category. Keep the visible table headings Manipulation and Mobile Manipulation; document the robot here.

One concrete ten-round skeleton:
## 1. Move anchor A from its initial support onto tray T1 in R1.
## 2. Deliver another object B to a support in R2.
## 3. Deliver/sort another object C in R3.
## 4. Retrieve the same A and place it on T4 in R4.
## 5. Deliver/reorganize D in R5.
## 6. Stage one or two non-anchor objects E in R6.
## 7. Retrieve the same A and place it on T7 in R7.
## 8. Sort/rearrange F in R8.
## 9. Complete a non-anchor cleanup/composition task in R9.
## 10. Retrieve the same A and place it on T10 in R10.

For Manipulation, replace room destinations with reachable workspace regions; keep a fixed robot base and unchanged room. For Mobile Manipulation, sources/targets and paths must require the appended room. Objects needed in later rooms may enter with that room. Never insert a replacement for an existing target into an old room.

Reuse pairs are (1,4), (4,7), (7,10). Keep these anchor rounds centered on the identity-specific object change and later reuse, with required physical displacement and release, so their task-success flags define the intended reuse events. Use different scene/object configurations across families. In the other six rounds, vary the number and order of meaningful subgoals; keep the full instruction as the policy input. Do not provide an oracle task decomposer.

Later instructions refer to the same perceptually distinguishable object. They must not assert a successful earlier placement if the policy failed. For example, use "Find the same striped mug used earlier and move it to the new room's tray." Do not reveal its current ground-truth location. If it fell or became inaccessible, keep the exact target and goal. Recovery must occur through ordinary policy actions inside the same task budget.

At every round boundary:
## 1. Pause simulator time, without zeroing velocities.
## 2. Save actual simulator state.
## 3. For mobile rounds 2-10, append the frozen new room. Verify unchanged old-world state.
## 4. Flush queued actions for the previous instruction.
## 5. Supply the new instruction and current permitted observations.
## 6. Resume control and score the real trajectory.
## 7. Stop on confirmed stable success or the physical deadline.
## 8. Preserve the actual terminal state even after failure.
## 9. Continue the remaining scheduled tasks.

Use the same native physical sensor configuration within each embodiment block: head/overlook RGB, wrist RGB and native proprioception where the checkpoint expects it. Different documented preprocessing is allowed. No privileged object poses, instance maps, scene graphs, hidden-room contents, target coordinates or future instructions may enter policy observations. The evaluator may access simulator truth in a separate process/interface.

Preserve native policy recurrent state/history across tasks when supported. If a checkpoint resets its cache on instruction change, document that native behavior. Never reset the physical world. Log any external planner/navigation module as part of the evaluated system; no hidden oracle support.

Timing:
- Manipulation: 120 simulated seconds per task.
- Mobile Manipulation: 300 simulated seconds per task.
- Main capability evaluation pauses physics while waiting for inference.
- Report wall time, inference latency, action counts and chunks separately.
- The inspected ARX runtime uses 250 Hz physics and 25 Hz observation/action delivery.
- The inspected EBench/OpenWAM protocol uses 30 Hz physics with one bridge step per simulator step.
- Resolve these against installed revisions. Native chunk duration is actions divided by actual delivery frequency, not one generic "step."

A successful task requires all terminal predicates simultaneously, required historical events in order, release where specified, the stable dwell and any explicit protection constraints. Lock success at the accepted task boundary. A later instructed relocation does not retroactively invalidate an earlier success. A generic non-anchor goal already true at the next boundary is recorded as pre_satisfied; do not move objects to make it harder. Anchor tasks require actual displacement, avoiding spurious reuse credit.

A pre_satisfied non-anchor task receives y=1 only after the normal dwell and all required trace events are satisfied. If a required action/event has not occurred, the policy still must execute it. Do not automatically skip or fail such a task.

If the robot/world becomes permanently unusable due to policy behavior, terminate physical execution and score all remaining scheduled tasks as zero. Ordinary task failure does not terminate the lifetime.

## 7. TABLE 4 METRICS AND DENOMINATORS

Let y[i,t] be binary success for lifetime i, task t, including zero for unreached tasks.

SR@K = 100/N * sum_i product_{t=1..K} y[i,t], K in {5,10}.
This is strict success on all first K complete instructions, not primitive count.

Tasks/10 = 1/N * sum_i sum_{t=1..10} y[i,t].
It counts later recovery successes after an earlier failure. It is not the successful-prefix length.

Reuse = 100/(3N) * sum_i [
  y[i,1]y[i,4] + y[i,4]y[i,7] + y[i,7]y[i,10]
].
The denominator contains all scheduled pairs, even after anchor failure or termination.
Do not divide by only the anchors a policy happened to complete.

The supplied worldedge_eval.metrics implements these reductions. The caller must independently reconcile all scheduled policy run IDs before supplying a success matrix. No unlabelled reducer can detect an omitted lifetime.

Stationary Reuse measures sustained instance-specific interaction; if the object remains visible, it does not isolate memory. Mobile Reuse also requires returning/searching older spaces. Do not overclaim a pure memory benchmark without a separate controlled visibility ablation.

## 8. TABLE 5: EMBODIMENT, MODELS AND ACTION ADAPTATION

Primary matched comparison:
- Cosmos-Predict2.5-2B, robot/action-conditioned variant.
- DreamDojo-2B.
Optional capacity extension:
- DreamDojo-14B.

Run all primary models on the same dual-ARX manipulation world/data split. A mobile video-WM experiment requires separate target-robot adaptation and a separate table panel; do not pool it into this primary table.

The released Cosmos action interface inspected is Bridge 7D. DreamDojo documents native GR-1, G1, AgiBot and YAM post-trained models. This does not establish native ARX/Lift2 compatibility. Numeric padding alone is insufficient.

Implement a dedicated 10 Hz WM collector:
- Each issued full bimanual command is held for 100 ms.
- Apply an incoming relative increment once, resolve the controller target, and hold that target for the interval. Never reapply a delta at all 25 physics substeps. Log both raw commands and the resolved issued targets with their conversion contract.
- The ARX physics/controller integration executes 25 physics substeps at 250 Hz per command interval.
- Verify this runtime path; the Table 4 native 25 Hz wrapper cannot simply be relabelled 10 Hz.
- Preserve native command semantics, both arms and grippers, verified dimensions, units, coordinate frames, absolute/relative flags, bounds and controller configuration.
- Log the command immediately before application, after deterministic conversion/clipping.
- Render the reference at t=0,0.1,...,30.0 seconds.

Table 4 snapshots and action paths may seed collection. If actions are resampled or held differently, replay them in simulation and generate new reference video/labels. Do not combine 10 Hz subsampled commands with the original 25 Hz trajectory video.

For each video model, replace only the incompatible action-input projection, load compatible pretrained weights, and train the action path plus video transformer using the declared target-robot data. Audit missing/unexpected checkpoint keys. Non-action incompatibilities require an explicit implementation decision and manifest update, not ignored load warnings. Verify gradients reach the action projection and that changing commands reaches the conditioning path.

The primary model receives initial RGB I0 plus the complete issued command sequence. Initial proprioception, future realized joint/EEF positions, object state and future-video-derived latent actions are excluded from this primary input. Store them only as privileged reference records. A future-state corruption test must leave serialized model inputs unchanged when reference frames/states after t=0 are randomized but commands are kept fixed.

Use the same fixed empty text prompt during adaptation and prediction for both models. Disable implicit native captions, stage-instruction conditioning and goal-description conditioning in the predictor. The independent video reader may receive the stage instruction. Override inherited Bridge state-to-action extraction, native action scaling and incompatible fixed-FPS assumptions; use the declared 10 Hz clock and train-only normalization.

Record this as target-embodiment post-training followed by frozen evaluation. If adaptation cannot be completed, leave the primary row unavailable. Separate native-robot demonstrations are possible but are not matched ARX comparisons.

## 9. TABLE 5 DATASET AND CONTROLLED BRANCHES

Each world contributes ten success/failure pairs, twenty clips:
- Placement: 3 pairs.
- Sorting: 2 pairs.
- Multi-object ordering: 2 pairs.
- Delayed revisit: 3 pairs.

Each pair has the same initial simulator snapshot, initial RGB, camera, task-stage goal and physical properties. One executed command sequence satisfies the stage goal; the other does not. Select/control the branches without looking at any video-WM output. Failure examples can use real failed policies or command interventions such as wrong placement, incomplete motion or premature release. Record the source. Never create a hidden change in physics to manufacture a failure.

Freeze a stage goal before execution. It must be false at the start, visibly decidable, and meaningful within thirty seconds. At 30 s, the required terminal predicates must have held for the final 0.5 s, and any required ordering events must have occurred. A long parent task's eventual success is not the label of an arbitrary thirty-second window. Never label "not finished yet" as failure of an entire multi-minute task.

Compute dwell and temporal ordering from the full physics/event trace, not only from the ten rendered frames per second.

The test set contains 300 successful and 300 failed clips. Ninety pairs, or 180 clips, are revisit cases. This balanced diagnostic population does not estimate natural operational failure prevalence; report that limitation.

The entire world group, including derived policy snapshots, belongs to one split. Before freeze, reject branches with unobservable labels or invalid physics and retain rejection reasons. After freeze, do not replace clips because models predict them poorly.

## 10. POST-TRAINING AND ROLLOUT

Proposed fixed adaptation budget per model:
- 20,000 optimizer updates; effective batch 32; training seed 42.
- 13 frames per sample at 10 Hz: one conditioning frame plus 12 future frames.
- Common image resolution 480 high x 640 wide.
- AdamW, learning rate 1e-5, 1,000 warm-up updates, cosine decay to 1e-6.
- AdamW betas (0.9, 0.999), epsilon 1e-8.
- Weight decay 0.01, gradient clipping 1.0, BF16.
- Train video transformer and action-conditioning parameters; freeze text encoder/video codec.
- Keep each method's native prediction objective and record all losses/weights. This is matched data/update/optimizer budget, not identical objectives or equal compute.

Use training-only action normalization. Never infer target normalization from test traces. The suggested budget is a bounded initial study, not a guarantee of sufficient adaptation. Poor development performance is a result/diagnostic; do not secretly remove a weak but valid model or grant it an unreported larger budget.

Save 5k, 10k and 20k checkpoints. Before training, freeze a 100-clip balanced development subset spanning all twenty development worlds. Select the checkpoint with lowest mean endpoint LPIPS@30 s at generation seed 0 on this subset; tie-break by fewer updates. It must have complete generated coverage. If no checkpoint is valid, report a training/inference blocker.

Before the primary test, pin native denoising steps, guidance, context/memory handling, optimizations and hardware. Native settings can differ, but must be reported. Compare deployed systems under matched input/data, not architecture causality. One training seed means test uncertainty is conditional on that adapted checkpoint.

Generate two fixed samples per test clip, seeds 0 and 1; score both. For the 13-frame interface, generate 25 chunks, each adding twelve new frames. Keep the initial frame once and remove each later chunk's duplicated conditioning frame. Produce exactly 301 timestamped frames at 10 Hz. Validate codec padding and remove the same fixed padding before scoring.

Only generated frames and native generated memory can condition later chunks. Never inject reference RGB within the thirty-second scored interval. No room insertion occurs inside the interval. A new room can be observed before starting a new clip, but that is a new conditioning boundary, not continuous prediction through unseen exogenous geometry.

The study predicts recorded execution conditioned on issued controls. A command sequence originally produced by a feedback policy can encode information correlated with later state. This is legitimate conditional replay, but does not demonstrate prospective planning at t=0 or closing a policy loop through imagined observations. A separate fixed candidate-action planning study would be needed for that claim.

## 11. VIDEO OUTCOME AND DELAYED REVISIT

LPIPS:
Use pinned official LPIPS, AlexNet, version 0.1, RGB in [-1,1]. Resize reference/prediction identically to 240x320 with fixed antialiased bilinear interpolation. Compare frame 50 at 5 s and frame 300 at 30 s. These are endpoint values, not averages over the preceding interval. No optical-flow alignment, best-frame search, per-model crop or best-of-N sample choice.

Outcome:
An independent blinded reader sees the prediction, stage instruction and required visible events. It does not see the simulator label or model identity. Return success, failure or unknown, with evidence timestamps.
Outcome = 50 * (positive-class correct fraction + negative-class correct fraction).
Average the two generation seeds within each clip first. Unknown is incorrect for both classes. Do not convert unknown into failure.

Revisit:
Use a manipulable rigid occluder; no articulated asset is required.
- Identity visible initially.
- Both branches physically change the target state during approximately 2-8 s.
- Target hidden for at least five consecutive seconds.
- The three revisit pairs in each world target 5, 10 and 15 seconds of occlusion respectively. Verify actual visibility intervals from reference rendering; retain the achieved durations in the frozen case manifest.
- Target revealed during 25-30 s.
- Identical nonreactive reveal suffix across both branches; no target-directed reaching that discloses its hidden location.
- Score at the fixed final endpoint using the final reveal window as visual evidence.
A valid prediction must jointly preserve the target identity, actual location/containment and any specified visible state. The failed task branch may place the object on the wrong tray; predicting that wrong-but-actual state correctly earns Revisit credit. Missing/duplicated/wrong/unreadable targets fail. Average over all 180 scheduled clips and both seeds.

For Revisit, the reader first extracts the visible identity, count, location/relation and specified state from the generated video. The scorer compares this structured readout with simulator-derived reference facts. Do not give the reader the ground-truth future state or ask the predictor to grade itself.

Do not provide a reference return frame before generating the reveal. With a fixed overlook camera, this is controlled disappearance/reappearance persistence. It is not yet cross-room mobile revisit; that requires the separate mobile extension.

Reader qualification:
Pin one video judge/checkpoint, decoding settings, frame sampling and rubric before test. Calibrate on 200 balanced development reference clips against simulator truth, requiring >=95% balanced accuracy and >=90% sensitivity/specificity, plus a separately validated revisit rubric. Use two independent human annotators and adjudication for the calibration audit. The judge's field of view and temporal sampling must expose every required event.

Audit all unknown test predictions and a fixed stratified 20% of generated test videos, balanced across model, outcome and case type. If disagreement exceeds 10% in a category, adjudicate the entire affected category. Keep original and final labels. If the reader cannot pass calibration, export a blinded human-annotation package and mark semantic scores pending. The coding agent must not manufacture missing human judgments.

Required diagnostic controls, primarily supplementary:
- Reference self-comparison: near-zero LPIPS and correct labels.
- Repeat the first frame.
- Loop an earlier segment.
- Replay pre-interaction/stale state at the return.
- Shuffle actions on dynamic cases.
- Duplicate the target.
Verify that the actual scoring system detects the intended semantic failures. LPIPS alone may reward static backgrounds.

## 12. ERRORS, RETRIES AND COMPLETENESS

Distinguish generation invalidity, policy/model behavior, and infrastructure faults.
Policy mistakes, invalid actions, physical timeouts and policy-induced unusable states remain failures.
Visual distortion, hallucination or disappearance in a decodable prediction is model behavior and is scored normally.

A transport retry must not create another physical attempt. Pause physics, reuse the same observation/state/RNG, and allow one deterministic retry. If exact policy-state restoration is impossible, restart the whole lifetime from its fixed seed under a recorded infrastructure rerun rule. Retain the failed record and never select the better outcome. A deterministic inference timeout on otherwise healthy hardware is model-side budget failure; a worker/network outage is infrastructure.

Disable native automatic resets that would repair failed tasks. Do not inherit an EBench failed-step reset loop as a lifetime reset.

Video infrastructure: one same-seed retry. Persistent missing/invalid video remains scheduled and contributes incorrect Outcome/Revisit predictions. Because LPIPS has no universal worst-value constant, a horizon cell is NR if any scheduled sample lacks its required frame. Do not average over only completed videos. Finish the missing jobs or explicitly label the row incomplete. If a scenario has a confirmed simulator defect, apply the same exclusion/rerun policy to all paired methods and publish the amendment.

## 13. STATISTICS, RUN COUNTS AND RESOURCE BUDGETS

Use independent world groups as clusters. Policy repeats and ten tasks are nested within a world. Video action pairs, clips and two generation samples are also nested. Use 10,000 paired bootstrap resamples over worlds, stratified by the three task families for Table 4. Report 95% intervals and paired differences in the supplement; keep means in the main tables. If worlds share a source parent, cluster at that parent instead.

Without additional rollouts, export a strict SR@k curve for k=1..10 and a video endpoint-LPIPS curve at 1, 5, 10, 20 and 30 seconds. Also break down Revisit by the three declared occlusion durations. These plots show degradation with horizon while keeping the main tables to four metrics.

A zero observed chain-success rate can produce a degenerate bootstrap interval. Report raw counts and a finite-population caveat or a conservative world-level event bound. Do not interpret zero observed events as zero underlying probability.

Full nine-row Table 4:
5 manipulation rows x 30 worlds x 2 seeds = 300 lifetimes, up to 3,000 tasks.
4 mobile rows x 30 worlds x 2 seeds = 240 lifetimes, up to 2,400 tasks.
Total = 540 lifetimes and at most 5,400 task attempts.
Maximum scored simulated time = 100 manipulation hours + 200 mobile hours = 300 hours.
This is not GPU wall time.

Accepted test room outputs = 30 manipulation rooms + 30 mobile worlds x 10 rooms = 330.
WM train/development adds 160+20 manipulation rooms = 180.
The eight manipulation policy-development rooms are a subset of WM development.
Eight mobile development worlds add 80 rooms.
Thus the combined default accepted room-output target is 590, excluding rejected candidates and optional demos.
A WM group may use one compiled room with derived snapshots, not twenty independently generated rooms.

Primary Table 5:
3,200 train + 400 dev + 600 test reference clips = 4,200 thirty-second clips.
600 test clips x 2 generation seeds x 2 primary models = 2,400 predicted videos.
Optional DreamDojo-14B adds 1,200 predictions and one separate adaptation run.
Each primary model requires one 20k-update training run plus three development checkpoint-evaluation campaigns.

Estimate wall time from real development measurements:
- rollout seconds and inference calls per task;
- generation/admission cost per accepted room;
- training seconds/update and peak memory;
- seconds per generated 12-frame block, multiplied by 25 blocks/video;
- annotation throughput and audit size.
Measure compressed artifact size; uncompressed 480x640 RGB storage is large. Use lossless reference/video storage or an explicitly fixed codec policy with timestamps, rather than dumping every frame as an unbounded collection of files.
Do not promise hardware/GPU-hour totals without the measured pilot.

## 14. OPTIONAL ADAPTIVE LOOP DEMONSTRATION

Disabled in the main configuration. If enabled after the primary implementation works:
Use three new mobile world seeds, one already validated frozen policy (default pi0.5), and at most twenty rounds each.
Generate the next task from actual terminal state and logged success/failure.
Preserve failed physical state; cap generation attempts; record the complete uncut trace and all failures.
Report valid generated tasks, admitted rooms, completed tasks, failure/recovery examples and total time.
Do not insert its raw success rate into the matched-policy table, since tasks differ adaptively.
A frozen policy plus an adaptive task generator demonstrates task selection/failure discovery, not policy learning.

For a video-WM-driven extension, feedback must be prediction error, a stage-outcome mismatch or a revisit-state mismatch against an executed simulator reference. The model's own predicted success is not a world-state receipt. New adaptive cases stay in the auxiliary stream or a later training split; they never retroactively modify the frozen Table 5 test set. If paper claims include the full live generation/feedback loop, complete one of these bounded demonstrations after the primary evaluation works.

## 15. IMPLEMENTATION CONTRACT

Suggested new package layout:

```text
worldedge_eval/
  cli.py
  manifests.py
  worlds/compiler.py
  worlds/admission.py
  worlds/append.py
  runtime/persistent_world.py
  policies/base.py
  policies/robodojo.py
  policies/ebench.py
  goals/predicates.py
  goals/trace_monitor.py
  policy_runner.py
  wm/collector.py
  wm/action_adapter.py
  wm/posttrain.py
  wm/forecast.py
  scoring/policy.py
  scoring/video.py
  scoring/bootstrap.py
  reporting.py
```

Logical interfaces to implement:

```text
WorldRuntime.reset_to_bundle(snapshot)
WorldRuntime.append_room(delta) -> old_state_preservation_report
WorldRuntime.observe(sensor_manifest) -> allowed_observation
WorldRuntime.step(executed_command, physical_duration)
WorldRuntime.snapshot() -> physical_state_record
Policy.reset_lifetime(seed)
Policy.set_instruction(text, preserve_memory=True)
Policy.act(allowed_observation) -> timestamped_action_chunk
GoalMonitor.update(privileged_state, contacts, events, timestamp)
GoalMonitor.result() -> terminal_predicates, temporal_events, success
VideoPredictor.predict(initial_rgb, issued_controls, seed, timestamps)
Reporter.aggregate(immutable_schedule, completed_run_records)
```

The policy observation interface must not expose the privileged state consumed by GoalMonitor. A successful controller return value cannot mutate state or bypass the monitor.

Future backend CLI contract (NOT implemented by this repository yet, except preflight):
The currently executable commands are documented in README.md. These commands are the intended contract for future simulator/model adapters, not a claim that the full backend exists:

```bash
python -m worldedge_eval preflight --config configs/experiment.yaml
python -m worldedge_eval build-worlds --config configs/experiment.yaml --split dev
python -m worldedge_eval verify --config configs/experiment.yaml --suite all
python -m worldedge_eval pilot --config configs/experiment.yaml
python -m worldedge_eval build-worlds --config configs/experiment.yaml --split all
python -m worldedge_eval collect-wm --config configs/experiment.yaml --split all
python -m worldedge_eval train-wm --config configs/experiment.yaml --models primary
python -m worldedge_eval freeze --config configs/experiment.yaml
python -m worldedge_eval run-policy --config configs/experiment.yaml --split test --models all
python -m worldedge_eval forecast-wm --config configs/experiment.yaml --split test --models primary
python -m worldedge_eval annotate --config configs/experiment.yaml --export-audit
python -m worldedge_eval score --config configs/experiment.yaml --suite all
python -m worldedge_eval report --config configs/experiment.yaml --require-complete
```

Training data/splits and dev selection are frozen before train-wm. The final freeze pins selected checkpoints and inference settings before test prediction. Raw test reference labels are evaluator-only, inaccessible to training/checkpoint selection.

Required artifact hierarchy:

```text
manifests/ source lock, models, splits, worlds, tasks, action contracts, thresholds, run schedule
worlds/ visual/collision assets, snapshots, admission and growth-preservation reports
policy_runs/ one directory per model/world/seed with timestamped observations/actions/state/goal traces
wm_dataset/ split/group/pair/branch with initial image, issued controls, reference video/state/labels
wm_checkpoints/ adapted weights plus training/selection logs
wm_predictions/ model/world/clip/seed with video, timestamps and inference manifest
annotations/ blinded tasks, automatic outputs, human audit, adjudicated labels
results/ per-run/per-clip values, coverage, paired CIs, CSVs and LaTeX
reports/ blockers, generation yield, failure causes, runtime/storage and protocol amendments
```

Store paths plus SHA256 content hashes. Separate sim_state, observations, proposed_plan, controller_status and goal_evaluation. Log every set_pose/reset operation; allow only initialization or declared unscored reference preparation, never ordinary evaluation success handlers. Preserve actual issued controls as well as raw model outputs.

Scheduled growth also permits initialization/activation of the new room's explicitly declared entities at their frozen coordinates. This exception never permits moving, respawning or resetting an entity that was previously active.

Schema-to-metric mapping: wm_case.case_id maps to clip_id; world_bundle_id maps to world_id. reference_outcome.status=success maps to ref_outcome=1; failure or partial maps to 0. category=delayed_revisit maps to revisit_expected=true, with a non-null revisit record; all other categories use revisit=null. The prediction reader's unknown label is distinct from a reference partial outcome. policy_run.rounds supply the ordered ten binary outcomes only after the scheduled run manifest is reconciled. Preserve source_group_id separately for clustering if multiple world bundles share a parent.

## 16. MEANINGFUL ACCEPTANCE TESTS

Physical/policy:
- Correct object placed/released/stable passes; wrong object fails.
- Holding an object above a goal fails placement.
- A planner claiming success without physical motion fails.
- Correct final arrangement with wrong required event order fails.
- A goal achieved then undone before acceptance fails.
- No actions do not cause semantic object teleportation.
- Append preserves old IDs, poses, velocities and robot state.
- A failed round's actual terminal state is the next round's initial state.
- Task failure followed by successful recovery contributes to Tasks/10.
- A policy-induced fatal state produces explicit zero slots for remaining rounds.
- A policy cannot access the evaluator's privileged state.
- The same initial bundle/seed is replayable within declared numerical tolerances.

Video:
- The 10 Hz command is truly held/applied through the intended 25 physics substeps.
- Changing command values changes model conditioning inputs.
- Future-reference corruption does not change model input hashes.
- A 25-chunk rollout has exactly 301 unique timestamps; no duplicated boundary frame.
- Frame 50 and frame 300 correspond to 5.0 and 30.0 simulated seconds.
- Unknown is incorrect even for negative outcomes.
- Missing videos remain in denominators and make LPIPS unavailable.
- Duplicate or unexpected clip/seed outputs are rejected.
- Revisit negative branches are scored against their actual changed state.
- Required corrupted-video controls are identified by the reader.

Run the included synthetic metric tests as a quick contract check:
python -m unittest -v test_worldedge_eval.metrics
Run from the repository root after installing the package. These tests do not validate simulator physics, model adapters, annotation or experiment completion.

## 17. DONE DEFINITION

The work is complete only when all selected rows have:
(a) frozen compatible checkpoint/interface manifests;
(b) the complete scheduled raw evidence or explicitly declared incomplete status;
(c) audited simulator/video labels;
(d) reproducible metric reductions with world-level uncertainty;
(e) generated paper tables and resource/failure reports.

The optional 14B row and mobile-video extension must remain visibly unmeasured if disabled. Do not render disabled/unrun rows as zero, and do not bold a placeholder as a winner.
