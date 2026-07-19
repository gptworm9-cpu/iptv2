import os
from flask import Flask, render_template, request

# Use absolute paths so Flask finds static/template folders regardless of import location
current_dir = os.path.dirname(__file__)
static_folder = os.path.join(current_dir, "..", "static")
template_folder = os.path.join(current_dir, "..", "templates")

app = Flask(__name__, static_folder=static_folder, template_folder=template_folder)


@app.route('/')
def index():
    # Example channel list — replace URLs with real IPTV streams
    streams = [
        {"id": 1, "name": "News Channel", "url": "https://example.com/stream1.m3u8"},
        {"id": 2, "name": "Sports Channel", "url": "https://example.com/stream2.m3u8"},
        {"id": 3, "name": "Movies", "url": "https://example.com/stream3.m3u8"},
    ]
    return render_template('index.html', streams=streams)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
