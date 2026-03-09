-- SQLite Schema for Heidi Unified Learning Suite

-- 1. Memories (Fact-based knowledge)
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    tags TEXT, -- JSON array of tags
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP,
    access_count INTEGER DEFAULT 0
);

-- 2. Episodes (Chronological experiences)
CREATE TABLE IF NOT EXISTS episodes (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    task TEXT NOT NULL,
    steps TEXT NOT NULL, -- JSON array of steps
    outcome TEXT, -- success, failure, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Reflections (Synthesized knowledge from episodes)
CREATE TABLE IF NOT EXISTS reflections (
    id TEXT PRIMARY KEY,
    source_episode_ids TEXT, -- JSON array of episodes
    conclusion TEXT NOT NULL,
    confidence REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Rules (Constitutional and procedural laws)
CREATE TABLE IF NOT EXISTS rules (
    id TEXT PRIMARY KEY,
    source_reflection_id TEXT,
    rule_text TEXT NOT NULL,
    rule_type TEXT DEFAULT 'procedure', -- constitutional, procedural, behavioral
    is_active BOOLEAN DEFAULT 1,
    violations_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Reward Events (Ranked outcomes and feedback)
CREATE TABLE IF NOT EXISTS reward_events (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    score REAL NOT NULL, -- -1.0 to 1.0
    reason TEXT,
    feedback_source TEXT DEFAULT 'automatic', -- automatic, user
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Strategy Stats (Performance metrics for different LLM strategies)
CREATE TABLE IF NOT EXISTS strategy_stats (
    strategy_id TEXT PRIMARY KEY,
    total_runs INTEGER DEFAULT 0,
    avg_reward REAL DEFAULT 0.0,
    success_rate REAL DEFAULT 0.0,
    last_used TIMESTAMP
);

-- 7. Run Summaries (Compact metadata for quick retrieval)
CREATE TABLE IF NOT EXISTS run_summaries (
    run_id TEXT PRIMARY KEY,
    task_summary TEXT,
    total_tokens INTEGER,
    duration_ms INTEGER,
    status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. Rule Violations (Tracking constitution breaches)
CREATE TABLE IF NOT EXISTS rule_violations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    rule_id TEXT NOT NULL,
    violation_context TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
