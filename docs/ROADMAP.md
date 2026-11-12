# Implementation milestones

The existing CPU commands are listed in [README](../README.md). The stages
below connect real native runtimes to the scoring/evidence contracts. None
of the unchecked stages is represented as a completed experiment.

## G0. Resolve sources and model identities

**Inputs:** `configs/experiment.yaml`, `SOURCES.txt`, the team's actual code.

- Pin the world-generation source, RoomGenBench, simulator and robot assets.
- Resolve native RoboDojo/EBench policy checkpoints for the planned rows.
- Record observation/action contracts, normalization and control rates.
- Recheck the inspected fork against the actual upstream. The Slian22 URL
  was not accessible in the original inspection.
- Create candidate model manifests. Resolve facts from installed code.

**Done:** every proposed integration has real source/weight references or a
specific recorded blocker. No training or test deployment is implied.

## G1. Verify native policy and model interfaces

Start with two development worlds for each robot setting.

- Check sensor coverage, action units, frames, absolute/relative conventions,
  gripper semantics, chunk consumption and wall/physical timing.
- Verify that policy outputs reach the actual controller.
- Demonstrate a physical interaction through that path.
- Label external planners/navigation modules as part of the evaluated system.
- Verify the WM action projection, load compatibility, train-only
  normalization and 10 Hz collector timing.

**Done:** real interface evidence is attached to model manifests. Native
benchmark success flags or mock wire-format tests alone do not satisfy this.

## G2. Compile and admit generated worlds

- Preserve generated object identities and separate dynamic bodies.
- Validate collision geometry, support, mass/inertia and robot reachability.
- Verify open portals for mobile tasks.
- Execute a physically valid reference sequence independently of the tested
  policies. Teleport-and-settle oracles are not feasibility evidence.
- Retain rejected candidates and generation yield.

**Done:** admitted shared manifests and physics evidence exist. Test-world
acceptance does not depend on a compared policy's result.

## G3. Implement persistent lifetimes

Add a persistent runtime alongside any native reset-based benchmark mode.
The inspected session contract must retain all physically valid terminal
states, including failed and partial outcomes.

At each round, preserve actual state, append/activate the scheduled room,
flush old-instruction actions, issue the new instruction and execute through
the independent evaluator. Continue after ordinary failure.

If the simulator requires preallocation, declare that mode and ensure
inactive entities cannot affect rendering, collision or policy inputs.
Initialization of new-room entities may not move old active entities.

**Done:** a failure-then-recovery trace and old-state preservation checks
demonstrate the intended continuous semantics on development worlds.

## G4. Implement independent evaluators

- State/contact predicates and required event ordering.
- Stable release/placement and instance correctness.
- Fixed ten-round schedule accounting, including unreached zero slots.
- Separation of privileged evaluator state from policy observations.
- Visual reader calibration and generated-video audit.
- Reference, repeated-frame, stale-state, looping and action-corruption
  controls for video metrics.

The current metric tests establish reduction behavior, not these physical
or visual validity conditions.

**Done:** positive and negative physical fixtures and the semantic reader
audit pass the prespecified requirements.

## G5. Collect WM data and adapt models

Use the declared grouped train/dev/test split. Collect and actually replay
10 Hz bimanual controls. A changed control stream requires new reference
frames and labels. Keep reference state inaccessible to prediction inputs.

For each primary model:

1. Replace and train the incompatible target-action projection.
2. Use the same train/dev worlds and fixed 20k-update budget.
3. Save declared checkpoints and select on the frozen development subset.
4. Record native objective, hardware and normalization.
5. Freeze the selected checkpoint and inference settings before test.

**Done:** real training/checkpoint-selection artifacts and valid recursive
forecasts exist. A padded native-robot action vector is not adaptation.

## G6. Freeze and execute the test campaign

Freeze source, split, checkpoint, scene/task, reference, threshold, retry,
inference and analysis manifests. Keep a run schedule independent of
completed outcomes. Execute all scheduled lifetimes and forecast samples.

Export compact scorer inputs from the full audited evidence. Record both
model behavior and infrastructure incidents. Do not choose the better retry.

**Done:** every scheduled unit is accounted for, with complete evidence or an
explicit incomplete status. Run counts match the frozen configuration.

## G7. Statistics and paper artifacts

- Compute point estimates with the implemented scorers.
- Implement 10,000 paired bootstrap resamples over independent source-world
  groups, retaining repeated seeds, tasks and action branches.
- Preserve policy task-family stratification.
- Export raw numerators/denominators and coverage.
- Export SR@1..10, LPIPS versus time, and Revisit versus occlusion.
- Complete human adjudication where required.
- Generate the compact main tables from completed scores.

**Done:** paired confidence intervals, raw evidence, annotation audit,
coverage, resource/failure reports and CSV/LaTeX agree.

## Optional live feedback demonstration

After the primary path works, use three new mobile worlds and one validated
frozen policy for at most twenty rounds each. Generate subsequent tasks from
actual terminal state and feedback. Keep the entire trace, including
failures. Do not mix its changing distribution into the fixed policy table.

Video-WM feedback must be a discrepancy from an executed reference, not the
predictor's self-reported success.
