"""Discord API client for game lists and random games, caches the game lists locally."""

import urllib.request
import urllib.error
import sys
import os
import json
import random
import time
import re

# adult games are part of the hub "Theme - Mature",
# but I can't get that data over the API, so I manually scraped it from the website.
# use this expression in the browser dev console on the mature hub:
#   Array.from(document.querySelectorAll("table td.py-2 a"))
#     .map(x => x.href.split("/")[4] + ", # " + x.parentElement.outerText.split("\n")[0]).join("\n")
# scrape date: 2024-03-06
_mature_games = set([
    420, # Mario is a Drug Addict
    1123, # Sex 2
    1189, # Dragon Knight 4
    1828, # Mechanized Attack
    2429, # Sextris + Hentai Columns
    2772, # Grand Theft Auto: San Andreas
    2814, # Dragon Knight 4
    3099, # Dragon Knight 4
    3191, # Jackass: The Game
    4132, # Mega Cheril Perils
    4414, # Rings of Power
    4542, # Bubble Bath Babes
    4551, # Gotta Protectors: Amazon's Running Diet
    4565, # Peek-A-Boo Poker
    4569, # Hot Slots
    4851, # Lala the Magical
    5256, # Yun
    5576, # Erika to Satoru no Yume Bouken
    5612, # Guitar Hero II: Deluxe
    5629, # Hong Kong 97 | Hong Kong 1997
    5774, # Papillon Gals
    6235, # Yakyuuken Part II: Gal's Dungeon (FDS)
    6310, # Color Some Shit
    6699, # Sex
    6926, # Nanako Descends to Hell
    6943, # BMX XXX
    6966, # Daraku no Kuni no Angie: Kyokai no Mesudoreitachi
    6976, # YoukaiDen
    6978, # 177
    6996, # YU-NO: Kono Yo no Hate de Koi o Utau Shojo
    6999, # Necronomicon
    7098, # Advanced V.G.
    7241, # Cheril in the Cave
    7388, # Strip Fighter II
    7476, # Mojon Twins Gran Sabiduría: 31 in 1 Real Game
    7555, # Private Stripper
    7565, # Hanafuda Yuukyou Den: Nagarebana Oryuu
    7763, # Sailor Fuku Bishoujo Zukan (FDS)
    8072, # Cheril the Goddess
    8560, # Steam Heart's
    8642, # Super Wakana Land
    8926, # Terrifying 911 | Special Forces 2: Base | Metal Slug
    9565, # Lady Sword: Ryakudatsusareta 10-nin no Otome
    9786, # Welcome to Pia Carrot
    9797, # 2nd Space
    9972, # Honey Peach: Mei Nv Quan
    10802, # 2nd Space
    10961, # Shadow Warrior
    11110, # Harlem Blade: The Greatest of All Time
    11111, # L Elle
    11566, # Grand Theft Auto: San Andreas
    11575, # Pokemon Clover
    11892, # Pipi & Bibis (Whoopee!!)
    12134, # Frisky Tom
    12197, # Lover Boy | Triki Triki
    12203, # Streaking
    12722, # Custer's Revenge
    13263, # Block Gal
    13379, # Divine Sealing
    13437, # LSD: Dream Emulator
    13566, # Pachinko Sexy Reaction
    13567, # Pachinko Sexy Reaction 2
    13743, # Joshi Daisei Private
    13787, # Super Jack
    13792, # Bootèe | Bootee
    13935, # Leisure Suit Larry in the Land of the Lounge Lizards
    13989, # Cyberblock Metal Orange
    14041, # Gabrielle
    14107, # Emmy
    14319, # Sexy Invaders (FDS)
    14753, # Super Maruo
    14759, # Beat 'Em & Eat 'Em
    14956, # My Best Friends: St. Andrew Jogakuin-hen
    15344, # Ultimate Sliding Puzzle: Ecchi Pack
    15349, # Jig-A-Pix: Love Is...
    15787, # Gals Panic S: Extra Edition
    15788, # Gals Panic S2 | Gals Panic SU
    15789, # Gals Panic S3
    15960, # Legend of Iowa, The
    15996, # Wild Woody
    16204, # Fantasia
    16222, # Pokemon Grand Dad Version
    16238, # Panic in the Mushroom Kingdom
    16243, # Panic in the Mushroom Kingdom 2
    16397, # Plumbers Don't Wear Ties
    16467, # Tokimeki Card Paradise: Koi no Royal Straight Flush
    16550, # Mind Teazzer
    16638, # Touhoumon Insane Version
    16840, # NeuroDancer: Journey into the Neuronet!
    16940, # Burning Desire
    17115, # AV Bishoujo Senshi Girl Fighting | AV Pretty Girl Fighting
    17308, # Sex
    17400, # Yellow Lemon
    17458, # Gals Panic
    17459, # Gals Panic 3
    17460, # Gals Panic 4
    17483, # Battle Skin Panic
    17703, # Larry and the Long Look for a Luscious Lover
    18123, # Advanced V.G.
    18165, # V I T A L I T Y
    18237, # Serial Experiments Lain
    18261, # Germs: Nerawareta Machi
    18466, # Girthbound
    18630, # Doki Doki Majo Shinpan!
    18631, # Doki Doki Majo Shinpan 2: Duo
    18632, # Doki Majo Plus
    18644, # Hi-Leg Fantasy
    19093, # 7 Sins
    19220, # Leisure Suit Larry: Magna Cum Laude
    19440, # Jackass: The Game
    19705, # BMX XXX
    19716, # Super Uwol
    19743, # Gun
    20085, # Junkoid
    20240, # Pornoman
    20264, # Yakyuuken Special, The: Kon'ya wa 12-kaisen!!
    20265, # Yakyuuken Special, The: Kon'ya wa 8-kaisen!!
    20266, # Yakyuuken Special, The: Kon'ya wa 12-kaisen!!
    20295, # PhantasM | Phantasmagoria
    20506, # Onee-san to Issho! Janken Paradise
    20507, # Onee-san to Issho! Kisekae Paradise
    20953, # Family Guy: Video Game!
    21056, # Playboy: The Mansion
    21294, # Penthouse Interactive: Virtual Photo Shoot Vol. 1
    21535, # _Summer##
    21542, # 120 Yen no Haru: 120 Yen Stories
    21935, # Dragon Knight
    22063, # Dragon Knight II
    22065, # Dragon Knight & Graffiti
    22081, # Dragon Knight II
    22084, # Macadam: Futari Yogari
    22134, # Simple 2000 Series Ultimate Vol. 15: Love * Ping Pong! | Pink Pong
    22685, # Cheril Perils Classic
    22821, # Simple 2000 Series Vol. 88: The Mini Bijo Keikan
    23799, # Yu-Gi-Oh! Forbidden Memories: Deep Fried Mod
    23922, # Oh No!
    24046, # Guitar Hero II: Deluxe
    24119, # Mega Casanova
    24120, # Mega Casanova 2
    24121, # Mega Casanova 3
    24123, # Hong Kong 97
    24823, # Fairy Pinball: Yousei Tachi no Pinball (FDS)
    24959, # Chiller
    24994, # La Culotte de Zelda
    25045, # Glass
    25068, # SnakeDS
    25167, # Guitar Hero II: Deluxe - Brand New Hero
    25191, # Torrente 3: The Protector | Torrente 3: El Protector
    25300, # He Fucked the Girl Out of Me.
    25612, # Super Junkoid
    25727, # Advanced V.G.
    25816, # Shampoo
    26150, # Ikki Tousen: Shining Dragon
    27322, # Batty Zabella
    28557, # Shuten Douji
    28643 # Tsukihime
])

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
        if game['ID'] in _mature_games:
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

    def get_random_games(self, game_count=1, allow_empty=False, allow_hacks=True) -> list:
        """return random games from the cached game list,
           either only games with achievements, or any game when allow_empty=True"""
        games = self.get_full_gamelist(allow_empty)
        result = random.sample(games, game_count)
        # filter out hacks and then non-unique pulls until we have enough again
        if not allow_hacks:
            while True:
                result = [r for r in result if self._HACK_STR not in r['Title']]
                if len(result) == game_count:
                    break
                more_games = random.sample(games, game_count)
                ids = [r['ID'] for r in result]
                for g in more_games:
                    if g['ID'] not in ids:
                        result.append(g)
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
