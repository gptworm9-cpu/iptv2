from flask import Flask, render_template, request

app = Flask(__name__, static_folder="../static", template_folder="../templates")


@app.route('/')
def index():
    # Example channel list — replace URLs with real IPTV streams
    streams = [
        {"id": 1, "name": "News Channel", "url": "https://example.com/stream1.m3u8"},
        {"id": 2, "name": "Sports Channel", "url": "https://example.com/stream2.m3u8"},
        {"id": 3, "name": "Movies", "url": "https://example.com/stream3.m3u8"},
    ]
    return render_template('index.html', streams=streams)


# Vercel WSGI handler
try:
    from vercel_wsgi import handle_request

    def handler(request):
        return handle_request(app, request)
except Exception:
    # Local dev fallback
    if __name__ == '__main__':
        app.run(host='127.0.0.1', port=5000, debug=True)
