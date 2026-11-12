# Instructions for coding agents

## Objective

Implement the experimental setting in `docs/EXPERIMENT_PROTOCOL.md` and
`configs/experiment.yaml`. The repository currently provides CPU planning,
validation, score aggregation and table export. Native simulator and model
execution are the next milestones in `docs/ROADMAP.md`.

## Scientific contracts

- Preserve actual physical states after failed tasks. Do not reset, teleport
  or respawn old entities to make the next task work.
- Keep simulator truth separate from observations, plans and skill status.
  Only the independent state/trace evaluator establishes task success.
- Freeze the common test schedule before testing policies. Keep adaptive
  generation in its own stream.
- Use every scheduled unit in accounting. Never select favorable seeds,
  drop poor runs or turn missing results into measured zeros.
- WM inputs contain initial RGB and issued commands. Future GT images,
  realized future poses and future-video-derived latent actions are forbidden.
- Execute resampled controls to obtain matching reference videos. Apply a
  relative command once, then hold its resolved target for the interval.
- Record exact sources, checkpoints, action semantics, normalization,
  timing, physical thresholds, inference settings and training provenance.
- Unknown video outcomes are incorrect for both classes.
- Do not publish synthetic fixture values as experimental results.

## Working conventions

- Keep source under `src/worldedge_eval/`, tests under `tests/`, settings under
  `configs/`, record schemas under `schemas/`, and paper sources under `paper/`.
- Use local/native training and inference environments. External simulator
  stacks can have separate environments with explicit adapter boundaries.
- Run `python -m unittest discover -s tests -v` for meaningful code changes.
- Keep README commands aligned with actual implemented commands. Planned
  backends must remain labelled as integration work.
- Keep checkpoints, data, videos, private paths and credentials out of Git.
- Do not alter protocol thresholds or populations after inspecting test
  results. Record any legitimate protocol revision and its development basis.
