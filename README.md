# NBA box-score fetcher

Runs with Python 3.11+; no packages or NBA API key required. Downloads the NBA liveData scoreboard and each game's box score. Availability depends on the NBA endpoint accepting requests from the machine running it. This is an unofficial use of NBA public endpoints, not a guaranteed service.

## Run on your computer

    python fetch_boxscores.py

Today's default date uses America/Chicago. The NBA scoreboard must actually match the requested date; it refuses to relabel another day's results. After midnight, pass the evening's explicit date if the NBA scoreboard still carries those games:

    python fetch_boxscores.py --date 2026-10-21

Historical box scores require known NBA game IDs:

    python fetch_boxscores.py --date 2026-10-21 --game-ids 0022600090,0022600091

## Run on GitHub

1. Create a repository such as `nba-boxscores` (private is fine).
2. Put this folder's contents at its root, including `.github/workflows/boxscores.yml`. Uploading only the ZIP will not install the workflow. Ensure the workflow is on the default branch.
3. In Actions, select **Fetch NBA box scores**, then **Run workflow**. Leave inputs blank for today.
4. Successful runs commit `data/YYYY-MM-DD/boxscores.json`, `players.csv` and `raw/` responses to the repository. The ChatGPT GitHub connector can then read these files if the repository is accessible to it. Organization policy or protected branches may require using the downloadable workflow artifact instead of committing.

This package is manual/on-demand. No recurring schedule is enabled. It contains no personal roster. Keep all NBA players so league availability and roster filters can be maintained separately.

## Output and safeguards

- Player IDs, names, teams, opponents, scores, playing status, starter flags, minutes and game status.
- FGM/FGA, FTM/FTA, 3PTM/3PTA, PTS, OREB, DREB, REB, AST, ST, BLK, TO, PF.
- FG%, FT%, 3PT% are decimal ratios (0.5 means 50%). A zero-attempt percentage is blank/null. For a team total, sum makes and attempts before dividing; never average player percentages.
- Minutes retain the NBA ISO duration format. Missing stats remain blank/null rather than fabricated zeros. Check `played` and availability before interpreting DNP rows.
- Triple-doubles are not scored. This is data collection, not a player ranking or add/drop model.
- Original JSON, source URLs, fetch timestamps and live/final status are preserved. No automatic inference that limited minutes reflect a permanent role change.
- Failed games mark the report incomplete and return a failing exit code. The workflow does not commit partial results, but retains them as an artifact for inspection. Earlier snapshots may remain in the repository after a failed run; always check timestamps and run status.
- Today's scoreboard endpoint is not a historical date lookup. Explicit historical game IDs are supported when NBA retains the box-score JSON.

## Sources

- https://github.com/swar/nba_api/blob/master/docs/nba_api/live/endpoints/scoreboard.md
- https://github.com/swar/nba_api/blob/master/docs/nba_api/live/endpoints/boxscore.md
- https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow

## Validation

See VALIDATION.md for the actual test results from the creation session. Live data files are snapshots, not promises of continuously updated scores.
