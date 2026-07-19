import os
import urllib.request
import urllib.error
from flask import Flask, render_template, request, jsonify

# Use absolute paths so Flask finds static/template folders regardless of import location
current_dir = os.path.dirname(__file__)
static_folder = os.path.join(current_dir, "..", "static")
template_folder = os.path.join(current_dir, "..", "templates")

app = Flask(__name__, static_folder=static_folder, template_folder=template_folder)


def parse_m3u_text(m3u_text):
    lines = m3u_text.split('\n')
    channels = []
    current = None

    for line in lines:
        trimmed = line.strip()
        if trimmed.startswith('#EXTINF'):
            match = trimmed.rsplit(',', 1)
            name = match[-1].strip() if len(match) > 1 else 'Unknown Channel'
            current = {'name': name}
        elif trimmed and not trimmed.startswith('#') and current is not None:
            current['url'] = trimmed
            channels.append(current)
            current = None

    return channels


@app.route('/')
def index():
    return render_template('index.html', streams=[])


@app.route('/parse')
def parse_playlist():
    playlist_url = request.args.get('url', '').strip()
    if not playlist_url:
        return jsonify({'error': 'Missing url parameter'}), 400

    try:
        with urllib.request.urlopen(playlist_url, timeout=15) as response:
            raw_data = response.read()
            text = raw_data.decode('utf-8', errors='replace')
    except urllib.error.HTTPError as exc:
        return jsonify({'error': f'HTTP error {exc.code}: {exc.reason}'}), 502
    except urllib.error.URLError as exc:
        return jsonify({'error': f'URL error: {exc.reason}'}), 502
    except Exception as exc:
        return jsonify({'error': f'Failed to fetch playlist: {exc}'}), 502

    channels = parse_m3u_text(text)
    return jsonify({'channels': channels})


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
