"""Client for querying the flashpoint DB API for random games, caches the results locally."""

import sys
import os
import random
import httputil

def _game_id_to_path(game_id: str):
    if len(game_id) != 36:
        raise ValueError('invalid game_id ' + game_id)
    return game_id[:2] + '/' + game_id[2:4] + '/' + game_id

class FlashpointDbApi:
    """Client for querying the flashpoint DB API for random games, caches the results locally."""

    _BASE_URL = 'https://db-api.unstable.life/'
    _DB_URL = 'https://flashpointproject.github.io/flashpoint-database/search/#'
    _ASSET_URL = 'https://infinity.unstable.life/'

    def __init__(self, name: str, query_filter: str, cache_dir: str):
        self.name = name
        self.query_filter = query_filter
        self.cache_dir = cache_dir
        self.db = None

    def _load_db(self):
        self.db = self.get_games()

    def _request(self, url: str, cache_path=None):
        full_url = self._BASE_URL + url
        full_cache_path = os.path.join(self.cache_dir, cache_path) if cache_path else None
        return httputil.cached_request(full_url, full_cache_path)

    def get_games(self):
        """get the list of filtered games"""
        url = 'search?filter=true&fields=id,title,platform&' + self.query_filter
        return self._request(url, cache_path=self.name + '.json')

    def get_random_game(self) -> list:
        """return a random game from the cached game list"""
        if not self.db:
            self._load_db()
        return random.choice(self.db)

    def make_db_url(self, game_id: str) -> str:
        """return the url of the game with the given id"""
        return self._DB_URL + game_id

    def make_logo_url(self, game_id: str) -> str:
        """return the url of the logo for the game with the given id"""
        game_path = _game_id_to_path(game_id)
        return self._ASSET_URL + f'images/Logos/{game_path}.png'
        
    def make_screenshot_url(self, game_id: str) -> str:
        """return the url of the screenshot for the game with the given id"""
        game_path = _game_id_to_path(game_id)
        return self._ASSET_URL + f'images/Screenshots/{game_path}.png'

def get_api(name, query_filter):
    """Create a new FlashpointDbApi instance."""
    return FlashpointDbApi(name, query_filter, 'flashpointdb')

def main():
    """main entry point if script is called directly."""
    cmd = sys.argv[1] if len(sys.argv) > 1 else None
    instance_name = sys.argv[2] if len(sys.argv) > 2 else None
    query_filter = sys.argv[3] if len(sys.argv) > 3 else None
    api = get_api(instance_name, query_filter)
    if cmd == 'random':
        print(api.get_random_game())

if __name__ == '__main__':
    main()
