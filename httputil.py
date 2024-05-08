import urllib.request
import urllib.error
import os
import json

def _cached_request_impl(url: str, cache_path=None):
    json_resp = None
    if not cache_path or not os.path.exists(cache_path):
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "TrophyTroopa")
        with urllib.request.urlopen(req) as resp:
            json_resp = resp.read()
            if cache_path:
                os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                with open(cache_path, 'wb') as f:
                    f.write(json_resp)

    if not json_resp:
        with open(cache_path, 'rb') as f:
            json_resp = f.read()

    return json.loads(json_resp)

def cached_request(url: str, cache_path=None, ignore_error=False):
    """Make an http request and cache the json result."""
    try:
        return _cached_request_impl(url, cache_path)
    except urllib.error.HTTPError:
        if ignore_error:
            return None
        else:
            raise
