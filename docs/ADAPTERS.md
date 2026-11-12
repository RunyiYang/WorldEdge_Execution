# Simulator and model adapters

This document specifies the integration work required to execute the experiments. **The repository's planning, validation and scoring utilities do not provide enabled GPU simulators or pretrained-model backends.** Candidate model names in the configuration are a planned roster. They are not evidence that the models have already run in WorldEdge.

Implement adapters against pinned local source checkouts and real model weights. Record unresolved interfaces as blockers. Do not create fake checkpoint identifiers, success traces, annotations or enabled-integration claims.

## Source bridges to inspect

The inspected sources provide useful starting points, but need the changes described below. Recheck the team's installed revisions before wiring them into a runtime.

| Source and inspected path | Integration purpose | Required distinction |
|---|---|---|
| [infinite-task-world `embodied_gen/world/pipeline/session.py`](https://github.com/RunyiYang/infinite-task-world/blob/4478db064767690ce4d6a6553a4fb1a4d588a3ca/embodied_gen/world/pipeline/session.py) | Session/world lifecycle | The inspected mode resets each attempt and rejects changed canonical state after a failed execution. Add a separate persistent lifetime mode that preserves physically valid failures. |
| [infinite-task-world `embodied_gen/world/robot_eval.py`](https://github.com/RunyiYang/infinite-task-world/blob/4478db064767690ce4d6a6553a4fb1a4d588a3ca/embodied_gen/world/robot_eval.py) | Existing evaluation interface | Its teleport-and-settle `OraclePolicy` is not a learned robot rollout or an actuator-level feasibility demonstration. |
| [infinite-task-world `worldedge/executor.py`](https://github.com/RunyiYang/infinite-task-world/blob/4478db064767690ce4d6a6553a4fb1a4d588a3ca/worldedge/executor.py) | Existing action-stepping path | The inspected small native task does not establish generated-room support for ARX or Lift2. |
| [RoomGenBench `bench/assemble.py`](https://github.com/WorldEdge-Lab/RoomGenBench/blob/30f2e059d046ccd4aa928d0109a09a52f11693b5/bench/assemble.py) | Per-object geometry and room assembly | Preserve object identity and dynamic bodies when converting its visual meshes. Audit scaling, collision geometry, inertia and closed static door panels. |
| [RoomGenBench `bench/score_geom.py`](https://github.com/WorldEdge-Lab/RoomGenBench/blob/30f2e059d046ccd4aa928d0109a09a52f11693b5/bench/score_geom.py) | Static support diagnostics | Ray hits and geometric gaps are not physical stability, grasp or task-success evidence. |
| [RoboDojo `env_cfg/arx_x5.yml`](https://github.com/RoboDojo-Benchmark/RoboDojo/blob/f57e1633ffed59761bc8e568cfe7530c4b33381c/env_cfg/arx_x5.yml), [`env_cfg/sim/sim_config.yml`](https://github.com/RoboDojo-Benchmark/RoboDojo/blob/f57e1633ffed59761bc8e568cfe7530c4b33381c/env_cfg/sim/sim_config.yml), [`env/observation_manager/obs_manager.py`](https://github.com/RoboDojo-Benchmark/RoboDojo/blob/f57e1633ffed59761bc8e568cfe7530c4b33381c/env/observation_manager/obs_manager.py), [`src/eval_client/eval_env.py`](https://github.com/RoboDojo-Benchmark/RoboDojo/blob/f57e1633ffed59761bc8e568cfe7530c4b33381c/src/eval_client/eval_env.py) | ARX robot, sensor and native control contracts | Resolve exact installed rates, observations and action semantics. Table 4 uses the verified native interface; the video collector has its own explicit clock. |
| [EBench](https://github.com/InternRobotics/EBench) and [OpenWAM EBench guide](https://github.com/OpenWAM-Official/OpenWAM/blob/main/benchmarks/ebench/README.md) | Lift2/R5a deployment | Pin actual commits/checkpoints and disable any native automatic failed-step reset inside a scored lifetime. |

The originally requested `Slian22/infinite-task-world` URL was inaccessible through the inspection route. The links above identify the accessible inspected fork, not a claim that it is the latest upstream. Mutable documentation links are discovery references and must be replaced by the executed source lock.

## World compiler and physical truth

Compile visual assets, colliders, rigid-body parameters, semantic IDs and task regions into the native simulator. Preserve generated instance IDs across splitting and collision decomposition. Recompute inertia after scale changes. A visible tray cavity must also exist in its collision geometry.

Keep five channels separate: actual simulator state, permitted observations, proposed plans, controller status, and independent goal evaluation. The policy receives only the permitted observation contract. The shadow goal monitor may use privileged state and contacts through a separate interface.

Success requires the declared physical predicates, temporal events, release conditions and dwell. A controller returning success or a planner updating a symbolic object location is insufficient. Do not teleport objects into destinations, replace inaccessible targets, or repair a failed state in a success handler.

Log every reset or direct pose write. Initialization and declared unscored reference preparation are allowed. Scheduled growth may initialize only the new room's declared entities. It must not move, respawn or reset an entity that was already active.

## Table 4: reset-free policy lifetimes

Use `dual_arx_x5` for fixed-base bimanual manipulation and `lift2_r5a` for mobile manipulation. Verify the exact embodiment-specific checkpoint. No WorldEdge robot-policy fine-tuning is included.

An adapter may perform deterministic preprocessing, coordinate conversion, normalization and command formatting. It must not substitute oracle actions for predicted controls. If a planner, navigation module or skill library is part of the evaluated system, record it in the model manifest and label that complete system.

Reset the physical world once at the start of a scheduled world/seed lifetime. At each of its ten round boundaries:

1. Pause simulated time without zeroing physical velocities and save actual state.
2. For mobile rounds 2–10, append or activate the frozen next room. Verify that old entities, poses, velocities, robot state and persistent IDs are unchanged.
3. Flush queued actions for the old instruction. Preserve permitted policy history/state according to the checkpoint's documented behavior.
4. Issue the new instruction and current allowed observations. Do not reveal a target's privileged current location.
5. Resume actual actuator control. Stop that round at stable success or its fixed physical deadline.
6. Preserve the true terminal state after success, partial progress or failure, and continue the remaining scheduled rounds.

A lost target remains the same target. Recovery uses ordinary actions within the next declared budget. If a policy causes an unusable physical state, terminate explicitly and export zero outcomes for remaining slots. An infrastructure interruption has its separate incomplete status and fixed retry rule.

The manipulation world remains one reachable workspace. A mobile lifetime contains ten rooms: R1 is present for round 1, then R2–R10 become available before their corresponding rounds. Each mobile task uses the newly available room. Do not add an uncounted foyer or replace an old anchor object with a new copy.

If the simulator cannot create actors after initialization, preallocation followed by activation is an allowed declared implementation. Before activation, future entities must be absent from rendering, collision, policy observations and controller/perception state. Record `preallocated_activation` as the growth mode and verify old-state preservation. This does not establish arbitrary live insertion.

Keep physics paused during policy inference under the configured protocol; do not silently change physical action duration to match wall latency. Record both simulated and wall time. Resolve native control rates from installed code rather than assuming the provisional ARX or Lift2 guide values.

## Table 5: dedicated 10 Hz reference collector

The primary video study uses the ARX embodiment and a fixed calibrated overlook camera. It evaluates conditional replay of executed controls. It does not close a robot-planning loop through predicted observations.

For each 30-second reference clip:

1. Restore a pinned physical snapshot and record RGB frame 0 at t=0.
2. Issue one verified native command at each 100 ms boundary, for 300 intervals.
3. If a command is a relative increment, resolve it **once** into the controller target at that boundary. Hold the resolved target; do not reapply the increment at every physics step.
4. Execute 25 physics substeps at 250 Hz while holding that interval's command/target.
5. Record the next frame and privileged state at the boundary. Export exactly 301 frames, t=0 through 30 s, at 10 Hz.

Store raw issued commands, resolved/executed control logs, actual states and camera poses separately. Record dimensions, units, bounds, absolute/relative semantics, gripper encoding and controller configuration. No action dimension or calibration should be guessed.

If Table 4 actions are resampled, held differently or otherwise modified, re-execute them through this collector and regenerate reference video, state and labels. Do not pair downsampled controls with the old native-rate video.

The primary predictor input is RGB I0 plus the complete issued command sequence. Initial proprioception, future measured states, realized joint/EEF trajectories, goal text and future-video-derived latent actions are excluded. Use the same fixed empty text prompt for adaptation and inference. Privileged reference records remain evaluator-only.

Freeze the thirty-second stage goal before executing its branches. Its actual reference outcome is determined at the endpoint, including the declared dwell and event order. A failed/partial reference attempt remains a negative example even when the instruction describes a successful goal.

For `delayed_revisit`, both paired branches must actually change the target state during 2–8 s, contain the required continuous occlusion, and share the same fixed non-target-directed reveal suffix during 25–30 s. Score against each branch's actual terminal state. Ordinary placement/sorting/ordering clips have `revisit=null`.

## Local video-model adaptation and inference

Resolve the official action-conditioned model sources and exact weights locally. Useful entry points are [Cosmos-Predict2.5 robot-action conditioning](https://github.com/nvidia-cosmos/cosmos-predict2.5/blob/main/docs/inference_robot_action_cond.md) and [DreamDojo post-training](https://github.com/NVIDIA/DreamDojo/blob/main/docs/POSTTRAIN.md). These are integration references, not installed backends in this repository.

The native pretrained action interfaces do not establish compatibility with the generated ARX data. Implement the target action projection/loader and perform the declared local target-embodiment post-training. Audit missing/unexpected checkpoint keys, native action scaling, inherited state-to-action extraction and fixed-FPS assumptions. Verify that changing issued commands changes conditioning inputs and that gradients reach the action path.

Follow the frozen data split and training budget in [configs/experiment.yaml](../configs/experiment.yaml). Normalize actions with training data only. Record adapted components, native loss/objective, checkpoints, hardware and development selection. Do not use test clips to select a checkpoint. Leave the row unavailable if adaptation or compatibility remains unresolved.

At test time, produce both scheduled seeds. Under the declared 13-frame interface, each chunk adds twelve new frames. Generate 25 chunks, retain I0 once, remove duplicate chunk-boundary conditioning frames, and export exactly 301 unique timestamps. Continue only from generated frames and native generated memory. Do not inject reference RGB, reset to a future ground-truth state, insert a room inside the scored clip, or select the better sample.

## Record export and acceptance

Implement the exporter alongside each backend. The current schemas describe full records; the scoring CLI accepts the separate compact forms in [DATA_FORMATS.md](DATA_FORMATS.md).

The exporter must:

- Write immutable references and content hashes for snapshots, controls, state traces, goal traces, videos and model/source manifests.
- Preserve all ten policy slots and their reasons, including unattempted zeros. Reconcile them against the independent run schedule.
- Export video cases with their independent reference labels and scheduled generation seeds. Obtain prediction labels from the qualified independent reader or blinded adjudication, not model self-report.
- Retain failures, missing outputs, infrastructure status and retry history. Do not infer the denominator from successful output files.
- Keep source-group identity for split audits and clustered uncertainty.

Before declaring an adapter operational, demonstrate on development fixtures that a failed physical round continues without reset; append preserves old-world state; a symbolic success cannot pass the monitor; relative commands apply once per interval; corrupting future reference states leaves model input hashes unchanged; and a generated rollout contains exactly the prescribed timestamps. Verify that static, repeated and stale-state videos fail the intended semantic checks.

A real local smoke run and pinned interface evidence are required for `interface_passed`. Hashes, completed adaptation when applicable, resolved contracts and an empty unresolved list are required for `frozen`. Schema-valid fabricated logs do not satisfy either gate.
