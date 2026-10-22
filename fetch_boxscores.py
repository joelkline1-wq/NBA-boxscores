#!/usr/bin/env python3
"""Fetch NBA live box scores using Python 3.11+ standard library only."""
import argparse
import csv
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

BASE = 'https://cdn.nba.com/static/json/liveData/'
FIELDS = {'PTS': 'points', 'FGM': 'fieldGoalsMade', 'FGA': 'fieldGoalsAttempted',
          'FTM': 'freeThrowsMade', 'FTA': 'freeThrowsAttempted',
          '3PTM': 'threePointersMade', '3PTA': 'threePointersAttempted',
          'OREB': 'reboundsOffensive', 'DREB': 'reboundsDefensive',
          'REB': 'reboundsTotal', 'AST': 'assists', 'ST': 'steals',
          'BLK': 'blocks', 'TO': 'turnovers', 'PF': 'foulsPersonal'}

def get_json(url):
    for attempt in range(3):
        try:
            req = Request(url, headers={'User-Agent': 'Mozilla/5.0',
                                       'Referer': 'https://www.nba.com/'})
            with urlopen(req, timeout=20) as response:
                return json.load(response)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(1 + attempt)

def percent(made, attempted):
    return made / attempted if made is not None and attempted else None

def game_date(game):
    # NBA's gameCode uses its official basketball date, avoiding UTC rollover.
    code = game.get('gameCode', '').split('/')[0]
    return datetime.strptime(code, '%Y%m%d').date().isoformat()

def rows_for(game, fetched, source):
    rows = []
    for side, other in [('homeTeam', 'awayTeam'), ('awayTeam', 'homeTeam')]:
        team = game[side]
        for player in team.get('players', []):
            stats = player.get('statistics') or {}
            row = {'date': game_date(game), 'game_id': game['gameId'],
                   'game_status': game.get('gameStatusText'),
                   'game_status_code': game.get('gameStatus'),
                   'team': team['teamTricode'],
                   'opponent': game[other]['teamTricode'],
                   'team_score': team.get('score'),
                   'opponent_score': game[other].get('score'),
                   'player_id': player['personId'], 'player': player['name'],
                   'played': player.get('played'), 'starter': player.get('starter'),
                   'availability': player.get('status'),
                   'not_playing_reason': player.get('notPlayingReason'),
                   'MIN': stats.get('minutes'), 'fetched_at_utc': fetched,
                   'source_url': source}
            row.update({key: stats.get(value) for key, value in FIELDS.items()})
            for label, made, attempted in [('FG%', 'FGM', 'FGA'),
                                            ('FT%', 'FTM', 'FTA'),
                                            ('3PT%', '3PTM', '3PTA')]:
                row[label] = percent(row[made], row[attempted])
            rows.append(row)
    return rows

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date', default=datetime.now(ZoneInfo('America/Chicago')).date().isoformat())
    parser.add_argument('--game-ids', default='', help='Comma-separated NBA game IDs; allows historical games')
    parser.add_argument('--output', default='data')
    args = parser.parse_args()
    datetime.strptime(args.date, '%Y-%m-%d')
    destination = Path(args.output) / args.date
    raw = destination / 'raw'
    raw.mkdir(parents=True, exist_ok=True)
    fetched = datetime.now(timezone.utc).isoformat()
    errors, rows, games = [], [], []
    if args.game_ids:
        ids = list(dict.fromkeys(x.strip() for x in args.game_ids.split(',') if x.strip()))
        if any(not re.fullmatch(r'\d{10}', x) for x in ids):
            parser.error('Each NBA game ID must contain exactly ten digits.')
    else:
        board = get_json(BASE + 'scoreboard/todaysScoreboard_00.json')
        (raw / 'scoreboard.json').write_text(json.dumps(board, indent=2))
        if board['scoreboard']['gameDate'] != args.date:
            raise ValueError('NBA scoreboard date differs from requested date. Supply --game-ids for that date.')
        ids = [g['gameId'] for g in board['scoreboard']['games']]
    for game_id in ids:
        source = BASE + 'boxscore/boxscore_' + game_id + '.json'
        try:
            payload = get_json(source)
            (raw / (game_id + '.json')).write_text(json.dumps(payload, indent=2))
            game = payload['game']
            if str(game['gameId']) != game_id or game_date(game) != args.date:
                raise ValueError('Returned game ID or date does not match request')
            game_rows = rows_for(game, fetched, source)
            if game.get('gameStatus') in (2, 3) and not game_rows:
                raise ValueError('Started game has no player rows')
            rows.extend(game_rows)
            games.append({'game_id': game_id, 'status': game.get('gameStatusText'),
                          'players': len(game_rows), 'source_url': source})
        except Exception as exc:
            errors.append({'game_id': game_id, 'error': str(exc), 'source_url': source})
    report = {'date': args.date, 'fetched_at_utc': fetched, 'source': 'NBA liveData',
              'complete': not errors, 'requested_games': len(ids),
              'games': games, 'errors': errors, 'players': rows}
    (destination / 'boxscores.json').write_text(json.dumps(report, indent=2))
    if rows:
        with (destination / 'players.csv').open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    elif (destination / 'players.csv').exists():
        (destination / 'players.csv').unlink()
    print(json.dumps({'date': args.date, 'games': len(games), 'players': len(rows), 'errors': errors}))
    return 1 if errors else 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        print('Fetch failed: ' + str(exc), file=sys.stderr)
        sys.exit(1)
