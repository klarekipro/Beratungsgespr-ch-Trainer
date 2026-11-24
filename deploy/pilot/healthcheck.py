import json
from urllib.request import urlopen

with urlopen('http://127.0.0.1:8100/__pilot_health', timeout=2) as response:
    data = json.load(response)
    if response.status != 200 or data.get('status') != 'ok':
        raise SystemExit(1)
