# Weekly Review Pulse — local scheduler hook (Windows Task Scheduler).
# Production scheduling is handled by GitHub Actions (.github/workflows/weekly-pulse.yml).
#
# Task Scheduler example (Monday 09:00 IST):
#   Program: python
#   Arguments: -m pulse run --product groww
#   Start in: C:\path\to\AI Agent
#   Ensure .env is loaded (run from project root).

Set-Location $PSScriptRoot\..

python -m pulse run --product groww
