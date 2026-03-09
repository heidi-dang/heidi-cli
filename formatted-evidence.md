# Evidence Summary

## File: sample-config.json
```text
{
  "suite_enabled": true,
  "data_root": "/absolute/path/to/data",
  "model_host_enabled": true,
  "models": [
    {
      "id": "qwen-coder-7b",
      "path": "/path/to/models/qwen",
      "context_length": 8192,
      "backend": "llama.cpp"
    }
  ],
  "memory_sqlite_path": "/path/to/memory.db",
  "vector_index_path": "/path/to/vector.idx",
  "full_retraining_enabled": false,
  "promotion_policy": "beat_stable"
}
```

