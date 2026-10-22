#!/usr/bin/env python3
"""ESPN fallback. Player and event IDs are ESPN IDs, not NBA IDs."""
import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from fetch_boxscores import get_json, percent

BASE = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/'
TEAMS = {'NO': 'NOP', 'NY': 'NYK', 'GS': 'GSW', 'SA': 'SAS', 'UTAH': 'UTA', 'WSH': 'WAS'}

def number(value):
    if value in (None, '', '--', '-'): return None
    return float(value) if '.' in str(value) else int(value)

def normalize(payload, date, fetched, source):
    competition = payload['header']['competitions'][0]
    # Verify ESPN's event belongs to the requested Eastern basketball date.
    actual_date = datetime.fromisoformat(competition['date'].replace('Z', '+00:00')).astimezone(ZoneInfo('America/New_York')).date().isoformat()
    if actual_date != date: raise ValueError('ESPN returned an event for a different date')
    status = competition['status']['type']
    state = {'pre': 1, 'in': 2, 'post': 3}[status['state']]
    teams = competition['competitors']
    rows = []
    seen = set()
    for team in payload.get('boxscore', {}).get('players', []):
        tid = str(team['team']['id'])
        own = next(x for x in teams if str(x['team']['id']) == tid)
        opp = next(x for x in teams if str(x['team']['id']) != tid)
        for group in team.get('statistics', []):
            labels = group.get('names') or group['labels']
            for player in group.get('athletes', []):
                pid = str(player['athlete']['id'])
                if (tid, pid) in seen: continue
                seen.add((tid, pid))
                values = dict(zip(labels, player.get('stats', [])))
                row = {'date': date, 'game_id': str(payload['header']['id']),
                       'id_namespace': 'ESPN', 'source': 'ESPN',
                       'game_status': status.get('detail') or status['description'],
                       'game_status_code': state,
                       'team': TEAMS.get(own['team']['abbreviation'], own['team']['abbreviation']),
                       'opponent': TEAMS.get(opp['team']['abbreviation'], opp['team']['abbreviation']),
                       'team_score': number(own.get('score')),
                       'opponent_score': number(opp.get('score')),
                       'player_id': pid, 'player': player['athlete']['displayName'],
                       'played': None if state == 1 else not player.get('didNotPlay', False),
                       'starter': player.get('starter'),
                       'not_playing_reason': player.get('reason') if player.get('didNotPlay') else None,
                       'MIN': values.get('MIN'), 'minutes_format': 'ESPN display minutes',
                       'fetched_at_utc': fetched, 'source_url': source}
                for label in ['PTS', 'REB', 'AST', 'TO', 'BLK', 'OREB', 'DREB', 'PF']:
                    row[label] = number(values.get(label))
                row['ST'] = number(values.get('STL'))
                for key, made, attempted, pct in [('FG','FGM','FGA','FG%'),('FT','FTM','FTA','FT%'),('3PT','3PTM','3PTA','3PT%')]:
                    parts = str(values.get(key, '')).split('-')
                    row[made], row[attempted] = [number(x) for x in parts] if len(parts) == 2 else (None, None)
                    row[pct] = percent(row[made], row[attempted])
                rows.append(row)
    if state in (2,3) and not rows: raise ValueError('Started game has no player box score')
    # A final box should reconcile to the team score; avoid accepting incomplete tables.
    if state == 3:
        for team in teams:
            abbrev = TEAMS.get(team['team']['abbreviation'], team['team']['abbreviation'])
            if sum(r['PTS'] or 0 for r in rows if r['team'] == abbrev) != number(team['score']):
                raise ValueError('Player points do not reconcile with final team score')
    return rows, status.get('detail') or status['description']

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date', default=datetime.now(ZoneInfo('America/Chicago')).date().isoformat())
    parser.add_argument('--output', default='data')
    args = parser.parse_args()
    date = datetime.strptime(args.date, '%Y-%m-%d').date().isoformat()
    out = Path(args.output) / date
    raw = out / 'raw' / 'espn'
    raw.mkdir(parents=True, exist_ok=True)
    board = get_json(BASE + 'scoreboard?dates=' + date.replace('-', '') + '&limit=100')
    if 'events' not in board: raise ValueError('ESPN response has no events field')
    (raw / 'scoreboard.json').write_text(json.dumps(board, indent=2))
    games, errors, rows = [], [], []
    for event in board['events']:
        eid = str(event['id'])
        source = BASE + 'summary?event=' + eid
        try:
            payload = get_json(source)
            (raw / (eid + '.json')).write_text(json.dumps(payload, indent=2))
            if str(payload['header']['id']) != eid: raise ValueError('Event ID mismatch')
            fetched = datetime.now(timezone.utc).isoformat()
            game_rows, status = normalize(payload, date, fetched, source)
            rows.extend(game_rows)
            games.append({'game_id': eid, 'id_namespace': 'ESPN', 'status': status, 'source_url': source, 'fetched_at_utc': fetched})
        except Exception as exc:
            errors.append({'game_id': eid, 'error': str(exc)})
    report = {'date': date, 'source': 'ESPN', 'id_namespace': 'ESPN',
              'fetched_at_utc': datetime.now(timezone.utc).isoformat(),
              'complete': not errors, 'requested_games': len(board['events']),
              'games': games, 'errors': errors, 'players': rows}
    (out / 'boxscores.json').write_text(json.dumps(report, indent=2))
    if rows:
        with (out / 'players.csv').open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader(); writer.writerows(rows)
    elif (out / 'players.csv').exists(): (out / 'players.csv').unlink()
    print(json.dumps({'source': 'ESPN', 'games': len(games), 'players': len(rows), 'errors': errors}))
    return 1 if errors else 0

if __name__ == '__main__':
    try: sys.exit(main())
    except Exception as exc:
        print('ESPN fetch failed: ' + str(exc), file=sys.stderr); sys.exit(1)
