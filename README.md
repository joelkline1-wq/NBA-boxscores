# NBA box-score fetcher

Fetch NBA game scores and player box scores on demand using GitHub Actions. Python 3.11+; no external packages or API keys required.

## Refresh the data

Open [Fetch NBA box scores](https://github.com/joelkline1-wq/NBA-boxscores/actions/workflows/boxscores.yml), click **Run workflow**, and leave the fields blank for today in America/Chicago. For another date, enter YYYY-MM-DD. Check that the run finishes successfully before treating files as fresh.

Successful runs commit `data/YYYY-MM-DD/boxscores.json`, `players.csv`, and original source responses under `raw/`. The files uploaded initially at the repository root are older setup snapshots; use dated files under `data/` for subsequent runs.

The workflow also runs when its own configuration or either fetcher changes on main. No recurring schedule is enabled.

## Data sources

The workflow first tries NBA liveData. An initial GitHub-hosted run was rejected by that endpoint with HTTP 403, so it falls back to ESPN's publicly accessible scoreboard and summary JSON endpoints. These endpoints are unofficial integrations and can change or restrict access. No uptime or refresh-delay guarantee is implied.

Every report identifies its source. ESPN event and player IDs differ from NBA IDs: use `id_namespace` before joining IDs across sources. ESPN minutes are display minutes; NBA minutes are ISO durations. Do not assume the two formats are identical.

## Contents

Player names and IDs; teams and opponents; live/final status; starter and playing status; minutes; PTS, FGM/FGA, FTM/FTA, 3PTM/3PTA, OREB, DREB, REB, AST, ST, BLK, TO and PF. Shooting percentages are decimal ratios, with blank/null for zero attempts. For aggregate percentages, sum makes and attempts first. Triple-doubles are not scored.

Raw responses and source URLs are retained, with fetch timestamps. Missing data is not fabricated as zero. ESPN final-game player point totals must match the final team score. Partial failures fail the workflow and do not commit new data; inspect run status and timestamps so an older snapshot is not mistaken for current data. Partial downloads may be available as run artifacts.

No personal fantasy roster is embedded. Capture all players, then filter by the latest league rosters separately.

## Local use

```bash
python fetch_boxscores.py --date 2026-10-21
python fetch_espn.py --date 2026-10-21
```

NBA's scoreboard only supplies its current basketball date. Its historical box-score requests require known NBA game IDs via `--game-ids`. ESPN supports date-based lookup; do not pass NBA game IDs to it.

## References

- https://github.com/swar/nba_api/blob/master/docs/nba_api/live/endpoints/scoreboard.md
- https://github.com/swar/nba_api/blob/master/docs/nba_api/live/endpoints/boxscore.md
- https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow
