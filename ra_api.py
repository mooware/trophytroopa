"""Discord API client for game lists and random games, caches the game lists locally."""

import urllib.request
import urllib.error
import sys
import os
import json
import random
import time
import re

class RetroAchievementsApi:
    """Discord API client for game lists and random games, caches the game lists locally."""

    _BASE_URL = 'https://retroachievements.org/'
    _API_URL = _BASE_URL + 'API/'
    _SUBSET_RE = re.compile(r'\[Subset[^\]]+\]$')
    _HACK_STR = '~Hack~'

    def __init__(self, user: str, key: str, cache_dir: str):
        self.auth_user = user
        self.auth_key = key
        self.cache_dir = cache_dir
        self.all_games = None
        self.all_nonempty_games = None
        self.db_timestamp = 0
        # some short well-known aliases to make system filtering easier
        with open('system_aliases.json', 'rb') as f:
            self.system_aliases = json.load(f)
        # adult games are part of the hub "Theme - Mature",
        # but I can't get that data over the API, so I manually scraped it from the website.
        # use this expression in the browser dev console on the mature hub:
        #   Array.from(document.querySelectorAll("table td.py-2 a"))
        #     .map(x => '"' + x.href.split("/")[4] + "\": \"" + x.parentElement.outerText.split("\n")[0].trim() + "\"").join(",\n")
        # scrape date: 2024-03-06
        with open('mature_games.json', 'rb') as f:
            self.mature_games = {int(x) for x in json.load(f)}

    def _load_db(self):
        path = os.path.join(self.cache_dir, 'systems.json')
        if os.path.exists(path):
            mtime = os.stat(path).st_mtime
            if mtime == self.db_timestamp:
                return # already loaded
            self.db_timestamp = mtime
        print('reload db')
        self.all_games = []
        self.all_nonempty_games = []
        for system in self.get_systems():
            sysid = int(system['ID'])
            # ignore non-game systems, like "Hubs" and "Events"
            if sysid >= 100:
                continue
            for game in self.get_gamelist(sysid):
                if self._is_ignored_game(game):
                    continue
                if game["NumAchievements"]:
                    self.all_nonempty_games.append(game)
                self.all_games.append(game)

    def _is_ignored_game(self, game: dict):
        if game['ID'] in self.mature_games:
            return True
        # subsets are additional groups of achievements for a game, usually specialized
        title = game['Title']
        if title.endswith(']') and self._SUBSET_RE.search(title):
            return True
        return False

    def _request(self, url: str, args=None, cache_path=None):
        full_url = self._API_URL + url + f'?z={self.auth_user}&y={self.auth_key}'
        if args:
            full_url += '&'
            full_url += args
        if cache_path:
            full_cache_path = os.path.join(self.cache_dir, cache_path)
        json_resp = None
        if not cache_path or not os.path.exists(full_cache_path):
            req = urllib.request.Request(full_url)
            req.add_header("User-Agent", "TrophyTroopa")
            json_resp = urllib.request.urlopen(req).read()
            if cache_path:
                os.makedirs(os.path.dirname(full_cache_path), exist_ok=True)
                with open(full_cache_path, 'wb') as f:
                    f.write(json_resp)

        if not json_resp:
            with open(full_cache_path, 'rb') as f:
                json_resp = f.read()

        return json.loads(json_resp)

    def get_systems(self):
        """get the list of known systems"""
        return self._request('API_GetConsoleIDs.php', cache_path='systems.json')

    def get_gamelist(self, system_id: int):
        """get the game list for a specific system"""
        sysid = int(system_id)
        cache_path = os.path.join('gamelist', f'{sysid}.json')
        # will also return games without achievements
        return self._request('API_GetGameList.php', f'i={sysid}', cache_path=cache_path)

    def get_game_details(self, game_id: int, ignore_error=False):
        """get details for a game, will not be cached"""
        gid = int(game_id)
        try:
            return self._request('API_GetGame.php', f'i={gid}')
        except urllib.error.HTTPError:
            if not ignore_error:
                raise

    def get_full_gamelist(self, allow_empty=False) -> list:
        """get the full list of games with achievements, or of any games if allow_empty=True"""
        self._load_db()
        if allow_empty:
            return self.all_games
        else:
            return self.all_nonempty_games

    def _filter_hacks(self, games: list, get_more, max_iterations=10) -> list:
        target_count = len(games)
        for _ in range(max_iterations):
            # filter the list in-place
            for i in range(len(games) - 1, -1, -1):
                g = games[i]
                if self._HACK_STR in g['Title']:
                    games.pop(i)
            if len(games) >= target_count:
                break
            # re-fill to desired length
            missing_count = target_count - len(games)
            more_games = get_more(missing_count)
            ids = [r['ID'] for r in games]
            for g in more_games:
                if g['ID'] not in ids:
                    games.append(g)

    def match_system(self, substr: str):
        """return the system that is the closest match for the given substring"""
        s = substr.strip().lower()
        if not s:
            return None
        alias = self.system_aliases.get(s)
        if alias:
            s = alias.lower()
        matches = [x for x in self.get_systems() if s in x['Name'].lower()]
        if not matches:
            return None
        return min(matches, key=lambda x: len(x['Name']) - len(s))

    def get_random_games(self, game_count=1, allow_empty=False, allow_hacks=True, systems=None) -> list:
        """return random games from the cached game list,
           either only games with achievements, or any game when allow_empty=True"""
        games = self.get_full_gamelist(allow_empty)
        if systems:
            # not sure whether I want to cache these lists
            games = [g for g in games if g['ConsoleID'] in systems]
        def sample(count):
            if len(games) < count:
                raise Exception(f'game list is shorter than requested count ({len(games)} < {count})')
            return random.sample(games, count)
        result = sample(game_count)
        # filter out hacks and then non-unique pulls until we have enough again
        if not allow_hacks:
            self._filter_hacks(result, sample)
        return result

    def make_full_url(self, relative_url: str) -> str:
        """return a full url for the relative urls returned by the API, e.g. for images"""
        if relative_url.startswith('/'):
            relative_url = relative_url[1:]
        return self._BASE_URL + relative_url

    def make_game_url(self, game_id: int) -> str:
        """return the url of the game with the given id"""
        return self.make_full_url(f'game/{game_id}')

    def stats(self):
        """return a dict with total and nonempty game counts per system"""
        result = {}
        games = self.get_full_gamelist(allow_empty=True)
        all_total = 0
        all_nonempty = 0
        for game in games:
            key = game['ConsoleName']
            total, nonempty = result.get(key, (0, 0))
            is_nonempty = int(bool(game['NumAchievements']))
            result[key] = (total + 1, nonempty + is_nonempty)
            all_total += 1
            all_nonempty += is_nonempty
        return result, (all_total, all_nonempty)

    def update_cache(self):
        """Download the cached database files again and replace the old database."""
        temp_cache_dir = self.cache_dir + '.update'
        new_db = RetroAchievementsApi(self.auth_user, self.auth_key, temp_cache_dir)
        systems = new_db.get_systems()
        for system in systems:
            games = new_db.get_gamelist(system['ID'])
            print('updated system', system['ID'], system['Name'], 'has', len(games), 'games')
            # the RA API has heavy rate limiting, wait between requests
            time.sleep(1)
        new_db._load_db()
        print('total', len(new_db.all_games), 'games,', len(new_db.all_nonempty_games), 'with achievements')
        # now replace the old data
        os.replace(temp_cache_dir, self.cache_dir)
        self.all_games = new_db.all_games
        self.all_nonempty_games = new_db.all_nonempty_games


def get_api():
    """Create a new RetroAchievementsApi instance with configuration from ra_config.json."""
    with open('ra_config.json', 'rb') as f:
        cfg = json.load(f)
    return RetroAchievementsApi(cfg['api_user'], cfg['api_key'], 'db')

def main():
    """main entry point if script is called directly."""
    cmd = sys.argv[1] if len(sys.argv) > 1 else None
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    api = get_api()
    if cmd == 'random':
        print(*api.get_random_games(count, allow_empty=False), sep='\n')
    elif cmd == 'any':
        print(*api.get_random_games(count, allow_empty=True), sep='\n')
    elif cmd == 'update':
        api.update_cache()
    elif cmd == 'stats':
        stats, (total, nonempty) = api.stats()
        print('System | All Games | Games With Achievements')
        print('Total |', total, '|', nonempty)
        for sysname, (systotal, sysnonempty) in stats.items():
            print(sysname, '|', systotal, '|', sysnonempty)

if __name__ == '__main__':
    main()
