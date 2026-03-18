# Trigger Monitor Worker

> **Status: STUB** — This worker is not implemented and is not started by `start_dev.sh`.

## Current State

`workers/trigger_monitor/worker.py` contains an empty infinite loop. It is not
started by `start_dev.sh` and does not process any tasks.

Do not build on this worker without a full implementation plan.

## Original Intent

The trigger monitor was intended to watch active sessions and dispatch clustering
jobs based on count/interval thresholds, preventing over-clustering while ensuring
timely processing. This responsibility is currently handled inline by the
clustering worker itself, which triggers answer generation at milestones {3, 10, 25}.

## Relationship to Clustering Worker

The clustering worker directly enqueues to `QUEUE_ANSWER_GENERATION` at milestones.
See [workers/clustering.md](clustering.md).
