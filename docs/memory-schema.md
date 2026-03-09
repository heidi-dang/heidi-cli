# Memory Schema

Heidi persists all learning data in `state/memory/memory.db`.

## Tables

### `memories`
Static facts or long-term knowledge.
- `id`: UUID
- `content`: Textual knowledge
- `tags`: JSON array

### `episodes`
Individual run reports.
- `id`: UUID
- `run_id`: External run reference
- `task`: Task description
- `outcome`: success/failure

### `reflections`
Synthesized insights.
- `source_episode_ids`: JSON list of contributing episodes.
- `conclusion`: The insight text.

### `rules`
Active constraints and procedures.
- `rule_type`: `constitutional` (fixed) or `procedural` (learned).
- `is_active`: Toggle for rule application.

### `reward_events`
Scoring history.
- `score`: -1.0 to 1.0.

### `strategy_stats`
Performance tracking.
- `avg_reward`: Running average of scores.
