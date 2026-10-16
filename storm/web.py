import json
import re
from pathlib import Path

from flask import (
    Flask,
    Response,
    abort,
    jsonify,
    make_response,
    request,
    send_from_directory,
)

from storm import DELETED_SIGN, Storm, __version__
from storm.defaults import get_default
from storm.parsers.ssh_uri_parser import parse

app = Flask(__name__)
__THEME__ = "modern"
THEMES = ('modern', 'black', 'storm')

# The UI edits ~/.ssh/config, so only answer requests addressed to this
# machine. This stops DNS-rebinding pages from driving the API.
ALLOWED_HOSTS = ('localhost', '127.0.0.1', '[::1]')


@app.before_request
def check_host():
    hostname = re.sub(r':\d+$', '', request.host)
    if hostname not in ALLOWED_HOSTS:
        abort(403)


@app.after_request
def security_headers(resp):
    # The UI only loads its own script and styles, and must not be framed
    # by another site (clickjacking).
    resp.headers['Content-Security-Policy'] = (
        "default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    )
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['X-Frame-Options'] = 'DENY'
    return resp


def render(template, theme):
    static_dir = Path(__file__).parent
    template_path = static_dir / 'templates' / template
    content = template_path.read_text()

    # Only known theme names reach the page; anything else would be
    # reflected into the HTML unescaped.
    requested_theme = request.args.get('theme', theme)
    if requested_theme not in THEMES:
        requested_theme = theme if theme in THEMES else THEMES[0]
    content = content.replace('__THEME__', requested_theme)
    content = content.replace('__VERSION__', __version__)

    return make_response(content)


def response(resp=None, status=200, content_type='application/json'):
    return Response(response=resp, status=status, content_type=content_type)


@app.route('/')
def index():
    return render('index.html', __THEME__)


@app.route('/list', methods=['GET'])
def list_keys():
    storm_ = app.get_storm()
    return response(json.dumps(storm_.list_entries(True, only_servers=True)))


@app.route('/add', methods=['POST'])
def add():
    storm_ = app.get_storm()

    try:
        name = request.json['name']
        connection_uri = request.json['connection_uri']
        id_file = None
        if 'id_file' in request.json:
            id_file = request.json['id_file']

        if '@' in name:
            msg = 'invalid value: "@" cannot be used in name.'
            return jsonify(message=msg), 400

        user, host, port = parse(
            connection_uri,
            user=get_default("user", storm_.defaults),
            port=get_default("port", storm_.defaults)
        )
        storm_.add_entry(name, host, user, port, id_file)
        return response(status=201)
    except ValueError as exc:
        return jsonify(message=str(exc)), 400
    except (KeyError, TypeError):
        return response(status=400)


@app.route('/edit', methods=['PUT'])
def edit():
    storm_ = app.get_storm()

    try:
        name = request.json['name']
        connection_uri = request.json['connection_uri']
        id_file = None
        if 'id_file' in request.json:
            id_file = request.json['id_file']
            if id_file == '':
                id_file = DELETED_SIGN

        if not storm_.is_host_in(name):
            return jsonify(message=f"{name} doesn't exist in your sshconfig."), 404

        user, host, port = parse(
            connection_uri,
            user=get_default("user", storm_.defaults),
            port=get_default("port", storm_.defaults)
        )
        storm_.edit_entry(name, host, user, port, id_file)
        return response()
    except ValueError as exc:
        return jsonify(message=str(exc)), 400
    except (KeyError, TypeError):
        return response(status=400)


@app.route('/delete', methods=['POST'])
def delete():
    storm_ = app.get_storm()

    try:
        name = request.json['name']
        storm_.delete_entry(name)
        return response()
    except ValueError as exc:
        return jsonify(message=str(exc)), 404
    except (TypeError, KeyError):
        return response(status=400)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        str(Path(app.root_path) / 'static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )


def run(port, debug, theme, ssh_config=None):
    global __THEME__
    port = int(port)
    debug = bool(debug)
    __THEME__ = theme

    def get_storm():
        return Storm(ssh_config)

    app.get_storm = get_storm

    app.run(port=port, debug=debug)
