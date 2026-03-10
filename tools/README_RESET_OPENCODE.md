Reset and restart OpenCode web (tools/reset_and_restart_opencode.sh)
===============================================================

Overview
--------
This script helps reset and restart the OpenCode web application inside a tmux session named "a".

Location
--------
tools/reset_and_restart_opencode.sh

Usage
-----

Dry-run (recommended):

  ./tools/reset_and_restart_opencode.sh

Perform actions (stop/start, backup):

  ./tools/reset_and_restart_opencode.sh --yes --backup-dir "$HOME/state/backups/opencode"

What it does
------------
- Ensures tmux session 'a' exists (creates if missing)
- Backs up ~/.config/opencode to the provided --backup-dir (if given)
- Stops processes in the tmux session by sending Ctrl-C, then SIGTERM, then SIGKILL
- Starts the OpenCode web server in a tmux window named 'opencode_web'
- Defaults to starting with: npx opencode web --hostname 0.0.0.0 --port 6868
- Writes logs to ~/state/logs/opencode_web.stdout.log and ...stderr.log

Safety notes
------------
- Default is dry-run. Use --yes to actually perform stop/start
- The script will not perform git operations or remote pushes
- Make sure tmux is installed
- The script may attempt to use package.json start script if present

Troubleshooting
---------------
- If npx opencode is not available in your environment, set a project-specific start command inside the script or ensure the start script exists in package.json
- Check logs in ~/state/logs for stdout/stderr output
