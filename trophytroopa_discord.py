"""TrophyTroopa discord bot functions for admin tasks like registering the bot and commands."""

from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
import urllib.request
import json

_DISCORD_API_URL = 'https://discord.com/api/v10/'

class DiscordApi:
    def __init__(self, app_id, public_key, bot_token):
        self.app_id = app_id
        self.verify_key = VerifyKey(bytes.fromhex(public_key))
        self.bot_token = bot_token

    def verify_signature(self, data: bytes, signature: str, timestamp: str) -> bool:
        """Verify signatures sent by discord."""
        try:
            self.verify_key.verify(timestamp.encode() + data, bytes.fromhex(signature))
            return True
        except BadSignatureError:
            return False

    def _send_request(self, url, data=None):
        if data:
            method = 'POST'
            body = json.dumps(data).encode()
        else:
            method = None
            body = None
        req = urllib.request.Request(url, data=body, method=method)
        req.add_header('Authorization', 'Bot ' + self.bot_token)
        req.add_header('Accept', 'application/json')
        req.add_header('User-Agent', 'TrophyTroopa')
        if body:
            req.add_header('Content-Type', 'application/json')
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())

    def register_commands(self, guild=None):
        guild_part = f'/guilds/{guild}' if guild else ''
        url = _DISCORD_API_URL + f'applications/{self.app_id}{guild_part}/commands'

        cmds = {
            'name': 'trophygames',
            'type': 1, # CHAT_INPUT
            'description': 'Get random games from the RetroAchievements database',
            'options': [
                {
                    'name': 'count',
                    'description': 'How many games to return (default: 1)',
                    'type': 4, # INTEGER
                    'required': False,
                    'min_value': 1,
                    'max_value': 10 # RetroAchievements quickly rate-limits after ~8 requests
                },
                {
                    'name': 'empty',
                    'description': 'Allow games without achievements? (default: false)',
                    'type': 5, # BOOLEAN
                    'required': False
                },
                {
                    'name': 'hacks',
                    'description': 'Allow romhacks? (default: true)',
                    'type': 5, # BOOLEAN
                    'required': False
                },
            ]
        }

        return self._send_request(url, data=cmds)

    def list_guilds(self):
        return self._send_request(_DISCORD_API_URL + 'users/@me/guilds')

def get_api():
    with open('discord_config.json', 'rb') as f:
        cfg = json.load(f)
    return DiscordApi(cfg['app_id'], cfg['pub_key'], cfg['bot_token'])

if __name__ == '__main__':
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else None
    if cmd == 'register':
        guild_id = int(sys.argv[2]) if len(sys.argv) > 2 else None
        print(get_api().register_commands(guild_id), sep='\n')
    elif cmd == 'guilds':
        print(*get_api().list_guilds(), sep='\n')
    else:
        sys.exit(1)
