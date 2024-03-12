"""Web API for TrophyTroopa, handles browsers, discord embeds and discord bot interactions."""

from bottle import route, post, request, template, redirect, abort, run
import trophytroopa_discord
import ra_api
import os
import time

# use the two primary RetroAchievements colors to mark the embeds
_DISCORD_EMBED_COLORS = [0x1066dd, 0xcc9a00]

HTML_INDEX_TEMPLATE = """
<html>
  <head>
    <title>TrophyTroopa Random Games Bot</title>
  </head>
  <body>
    <h1>TrophyTroopa Random Games Bot</h1>
    <div>games with achievements: {{len(ra.get_full_gamelist(allow_empty=False))}}</div>
    <div>total games: {{len(ra.get_full_gamelist(allow_empty=True))}}</div>
    <div><a href="random">go here for a random game with achievements</a></div>
    <div><a href="any">go here for any random game</a></div>
    <div><a href="stats">game list stats</a></div>
  </body>
</html>
"""

HTML_TOS_TEMPLATE = """
<html>
<head><title>TrophyTroopa - Terms of Service</title></head>
<body>Use of the TrophyTroopa bot is only allowed with the express permission of the developer, dev@mooware.at</body>
</html>
"""

HTML_PRIVACY_TEMPLATE = """
<html>
<head><title>TrophyTroopa - Privacy Policy</title></head>
<body>The TrophyTroopa bot does not store or use any personal data. Any personal data potentially received from the Discord API is ignored.</body>
</html>
"""

HTML_GAME_TEMPLATE = """
<html>
  <head>
    <title>TrophyTroopa Pull: {{game['Title']}}</title>
    <meta property="og:title" content="{{game['Title']}}" />
    <meta property="og:description" content="{{game['Title']}} ({{game['ConsoleName']}}), {{game['NumAchievements']}} achievements" />
    <meta property="og:type" content="website" />
    <meta property="og:url" content="{{ra.make_game_url(game['ID'])}}" />
    <meta property="og:image" content="{{ra.make_full_url(game['ImageIcon'])}}" />
  </head>
  <body>
    <img src="{{ra.make_full_url(game['ImageIcon'])}}" />
    <div>Game: {{game['Title']}}</div>
    <div>System: {{game['ConsoleName']}}</div>
%if details:
    <div>Developer: {{details['Developer']}}</div>
    <div>Publisher: {{details['Publisher']}}</div>
    <div>Genre: {{details['Genre']}}</div>
    <div>Released: {{details['Released']}}</div>
%end
    <div>Achievements: {{game['NumAchievements']}}</div>
    <a href="{{ra.make_game_url(game['ID'])}}">game page</a>
    <div><a href="random">go here for a random game with achievements</a></div>
    <div><a href="any">go here for any random game</a></div>
  </body>
</html>
"""

HTML_STATS_TEMPLATE = """
<html>
  <head>
    <title>TrophyTroopa Stats</title>
    <style>table, th, td { border: 1px solid; }</style>
  </head>
  <body>
    <table>
      <thead><th>System</th><th>With Achievements</th><th>All Games</th></thead>
      <tr><td>Total</td><td>{{nonempty}}</td><td>{{total}}</td></tr>
%for sysname, (systotal, sysnonempty) in stats:
      <tr><td>{{sysname}}</td><td>{{sysnonempty}}</td><td>{{systotal}}</td></tr>
%end
    </table>
  </body>
</html>
"""

_ra = None
def _get_ra_api():
    global _ra
    if not _ra:
        _ra = ra_api.get_api()
        # make sure the list is loaded
        _ra.get_full_gamelist()
    return _ra

_discord = None
def _get_discord_api():
    global _discord
    if not _discord:
        _discord = trophytroopa_discord.get_api()
    return _discord

# flag for printing debug output
_verbose = ("VERBOSE" in os.environ)

@route('/trophytroopa')
@route('/')
def redirect_to_index():
    # we need trailing slash for relative urls
    return redirect('/trophytroopa/')

@route('/trophytroopa/')
def index():
    ra = _get_ra_api()
    return template(HTML_INDEX_TEMPLATE, ra=ra)

@route('/trophytroopa/tos')
def tos():
    return template(HTML_TOS_TEMPLATE)

@route('/trophytroopa/privacy')
def privacy():
    return template(HTML_PRIVACY_TEMPLATE)

@route('/trophytroopa/random')
def random_game_pull():
    return show_random_game(allow_empty=False)

@route('/trophytroopa/any')
def any_game_pull():
    return show_random_game(allow_empty=True)

def show_random_game(allow_empty: bool):
    ra = _get_ra_api()
    game = ra.get_random_games(1, allow_empty=allow_empty)[0]
    details = get_game_details(ra, game['ID'])
    return template(HTML_GAME_TEMPLATE, ra=ra, game=game, details=details)

@route('/trophytroopa/stats')
def stats():
    ra = _get_ra_api()
    table, (total, nonempty) = ra.stats()
    table = sorted(table.items(), key=lambda row: row[1][1], reverse=True)
    return template(HTML_STATS_TEMPLATE, stats=table, total=total, nonempty=nonempty)

@post('/trophytroopa/discord_interaction')
def discord_interaction():
    if _verbose:
        print('discord request:', request.json)
    discord_verify(request)

    req_type = request.json['type']
    if req_type == 1: # PING
        return {'type': 1} # PONG
    elif req_type == 2: # APPLICATION_COMMAND
        cmd = request.json['data']
        if cmd['name'] == 'trophygames':
            return discord_cmd_trophygames(cmd)
        else:
            return abort(400, 'unknown command')
    else:
        return abort(400, 'invalid interaction type')

def discord_verify(request):
    """Check the request signature as required by Discord for interactions."""
    signature = request.headers['X-Signature-Ed25519']
    timestamp = request.headers['X-Signature-Timestamp']
    data = request.body.read()
    discord = _get_discord_api()
    if not discord.verify_signature(data, signature, timestamp):
        abort(401, 'invalid request signature')

def discord_cmd_trophygames(cmd):
    opts = {}
    if 'options' in cmd:
        opts = {opt['name']: opt['value'] for opt in cmd['options']}
    game_count = int(opts.get('count', 1))
    allow_empty = bool(opts.get('empty', False))
    allow_hacks = bool(opts.get('hacks', True))
    ra = _get_ra_api()
    embeds = make_discord_embeds(ra, game_count, allow_empty=allow_empty, allow_hacks=allow_hacks)
    response = {
        'type': 4, # CHANNEL_MESSAGE_WITH_SOURCE
        'data': {
            'content': f'Pulled {game_count} random game{"s" if game_count > 1 else ""} (empty: {allow_empty}, hacks: {allow_hacks})',
            'embeds': embeds
        }
    }
    if _verbose:
        print('discord response:', response)
    return response

def get_game_details(ra: ra_api.RetroAchievementsApi, game_id: int) -> dict:
    # request could fail because of rate limiting or other issues, ignore
    try:
      return ra.get_game_details(game_id)
    except Exception:
      return None

def make_discord_embeds(ra: ra_api.RetroAchievementsApi, game_count: int, allow_empty: bool, allow_hacks: bool) -> dict:
    embeds = []
    games = ra.get_random_games(game_count, allow_empty=allow_empty, allow_hacks=allow_hacks)
    retried = False
    for i, game in enumerate(games):
        details = get_game_details(ra, game['ID'])
        if not details and not retried:
            # RA starts rate-limiting after a few requests,
            # wait once to let it cool down
            time.sleep(1)
            retried = True
            details = get_game_details(ra, game['ID'])
        color = _DISCORD_EMBED_COLORS[i % len(_DISCORD_EMBED_COLORS)]
        embed = make_game_embed(ra, game, details, color)
        embeds.append(embed)
    return embeds

def make_game_embed(ra: ra_api.RetroAchievementsApi, game: dict, details: dict, color: int) -> dict:
    desc = f"**System:** {game['ConsoleName']}\n"
    if details:
        desc += f"**Developer:** {details['Developer']}\n**Publisher:** {details['Publisher']}\n**Genre:** {details['Genre']}\n**Released:** {details['Released']}\n"
    desc += f"**Achievements:** {game['NumAchievements']}"

    embed = {
        'type': 'rich',
        'title': game['Title'],
        'description': desc,
        'color': color,
        'thumbnail': {
            'url': ra.make_full_url(game['ImageIcon'])
        },
        'url': ra.make_game_url(game['ID'])
    }

    if details:
        embed['image'] = {
            'url': ra.make_full_url(details['ImageIngame'])
        }

    return embed

if __name__ == '__main__':
    run(host='localhost', port=8080, debug=True)
