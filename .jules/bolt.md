## 2026-02-15 - [Inefficient Log Streaming]
**Learning:** `pathlib.Path.read_text()` reads the entire file into memory every time. When polling a log file (like `tail -f`), this becomes O(N) per tick (total complexity O(N*Time)) which scales poorly as the log grows. Using `open()` with `readline()` keeps the file handle open and reads only new data (O(1) per tick).
**Action:** Always use incremental reading for log streaming or "tailing" files. Avoid `read_text()` inside loops.
