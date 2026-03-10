OpenCode Watchdog
=================

This watchdog ensures the OpenCode web server is running on port 6868. It periodically checks and uses the reset script to restart OpenCode if it's not running.

Usage
-----

Start manually:

  mkdir -p ~/state/run ~/state/logs
  chmod +x tools/opencode_watchdog.sh
  nohup tools/opencode_watchdog.sh > ~/state/logs/opencode_watchdog.out 2>&1 & echo $! > ~/state/run/opencode_watchdog.pid

Install on boot (example using crontab):

  (crontab -l 2>/dev/null; echo "@reboot /home/heidi/work/heidi-cli/tools/opencode_watchdog.sh > /home/heidi/state/logs/opencode_watchdog.out 2>&1 &") | crontab -

Logs: ~/state/logs/opencode_watchdog.log
