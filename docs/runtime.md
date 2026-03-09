# Runtime Learning

The Runtime Learning module is the "brain" of the Heidi Unified Learning Suite. It enables models to learn from every interaction through a feedback loop of memory, reflection, and reward.

## Memory Architecture

Heidi uses a SQLite-based relational memory store (and placeholder for vector embedding) to persist knowledge:
- **Episodic Memory:** Chronological logs of specific runs and their outcomes.
- **Reflections:** Synthesized conclusions derived from one or more episodes.
- **Rules:** Formalized "laws" (procedural or constitutional) generated from reflections to guide future behavior.

## The Reflection Loop

1.  **Run Completion:** A task is executed by the model host.
2.  **Capture:** The `Episode` is recorded in the database.
3.  **Reflect:** The `ReflectionEngine` analyzes the episode (and historical context) to generate a `Reflection`.
4.  **Rule Generation:** If a new effective pattern is found, a `Rule` is created and marked as active.

## Reward Scoring

Outcomes are quantified using the `RewardScorer`.
- **Automatic:** Success/failure detection in code execution or test runs.
- **User:** Explicit feedback provided via the API or CLI.

Scores are used to update `StrategyStats`, which track the performance of specific models over time.

## Strategy Selection

The `StrategySelector` uses the recorded statistics to choose the best model for a given task, balancing exploration (trying new models) and exploitation (using the best performer).

## CLI Commands

- `heidi memory status`: View database statistics.
- `heidi learning reflect`: Manually trigger the reflection engine.
- `heidi learning status`: (Phase 2 WIP) View learning progress.
