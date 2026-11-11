"""Update only the WakaTime section; credentials are read from runner environment."""
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

START = '<!--START_SECTION:waka-->'
END = '<!--END_SECTION:waka-->'


def render_stats(data):
    if data.get('is_up_to_date') is False:
        raise ValueError('WakaTime statistics are still being calculated; try again later.')
    languages = data.get('languages', [])
    if not languages:
        if data.get('total_seconds', 0) > 0:
            raise ValueError('WakaTime returned coding time without language details.')
        return 'No coding activity recorded in the last seven days.'
    rows = []
    for item in languages[:8]:
        name = str(item.get('name', 'Other')).replace('\n', ' ').replace('`', '')
        duration = str(item.get('text', '')).replace('\n', ' ').replace('`', '')
        percent = max(0, min(100, float(item.get('percent', 0))))
        bar = '#' * round(percent / 5)
        rows.append(f'{name:<18} {duration:<18} {bar:<20} {percent:5.1f}%')
    total = str(data.get('human_readable_total', '')).replace('\n', ' ').replace('`', '')
    return '```text\n' + '\n'.join(rows) + '\n```' + (f'\n\nTotal coding time: {total}' if total else '')


def replace_section(readme, content):
    if readme.count(START) != 1 or readme.count(END) != 1:
        raise ValueError('README must contain exactly one WakaTime marker pair.')
    before, rest = readme.split(START, 1)
    _, after = rest.split(END, 1)
    return before + START + '\n\n' + content + '\n\n' + END + after


def main():
    token = os.environ.get('WAKATIME_OAUTH_TOKEN', '')
    if not token:
        raise ValueError('WakaTime OAuth token is missing.')
    request = Request(
        'https://wakatime.com/api/v1/users/current/stats/last_7_days',
        headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/json'},
    )
    try:
        with urlopen(request, timeout=45) as response:
            payload = json.load(response)
    except HTTPError as error:
        raise ValueError(f'WakaTime returned HTTP {error.code}. Check the OAuth token and stats-read access.') from None
    except URLError:
        raise ValueError('Unable to reach WakaTime. Please retry the workflow.') from None
    if not isinstance(payload.get('data'), dict):
        raise ValueError('WakaTime did not return a statistics object; README was not changed.')
    path = Path('README.md')
    updated = replace_section(path.read_text(), render_stats(payload['data']))
    path.write_text(updated)
    print('Updated the WakaTime section in README.md.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError) as error:
        raise SystemExit(str(error))
