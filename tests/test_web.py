"""Tests for the Storm web API."""

import json
import pytest

from storm.web import app


@pytest.fixture
def client(tmp_path):
    """Create a test client with a temporary SSH config."""
    config_file = tmp_path / "ssh_config"
    config_file.write_text("""Host *
    user defaultuser

Host existing-server
    hostname existing.example.com
    user admin
    port 22
""")

    def get_storm():
        from storm import Storm
        return Storm(str(config_file))

    app.get_storm = get_storm
    app.config['TESTING'] = True

    with app.test_client() as client:
        yield client


class TestWebAPI:
    """Tests for the Flask web API."""

    def test_index(self, client):
        """Test index page returns HTML."""
        response = client.get('/')
        assert response.status_code == 200

    def test_list_keys(self, client):
        """Test list endpoint returns server entries."""
        response = client.get('/list')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, list)
        # Should have the existing-server entry
        hosts = [entry.get('host') for entry in data]
        assert 'existing-server' in hosts

    def test_add_success(self, client):
        """Test adding a new host via API."""
        response = client.post('/add',
            data=json.dumps({
                'name': 'new-server',
                'connection_uri': 'testuser@newserver.com:22'
            }),
            content_type='application/json'
        )
        assert response.status_code == 201

        # Verify it was added
        list_response = client.get('/list')
        data = json.loads(list_response.data)
        hosts = [entry.get('host') for entry in data]
        assert 'new-server' in hosts

    def test_add_with_id_file(self, client):
        """Test adding a host with identity file."""
        response = client.post('/add',
            data=json.dumps({
                'name': 'key-server',
                'connection_uri': 'keyuser@keyserver.com:22',
                'id_file': '/path/to/key.pem'
            }),
            content_type='application/json'
        )
        assert response.status_code == 201

    def test_add_invalid_name_with_at(self, client):
        """Test adding a host with @ in name fails."""
        response = client.post('/add',
            data=json.dumps({
                'name': 'bad@name',
                'connection_uri': 'user@host.com:22'
            }),
            content_type='application/json'
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'cannot be used in name' in data.get('message', '')

    def test_add_duplicate(self, client):
        """Test adding a duplicate host returns error."""
        response = client.post('/add',
            data=json.dumps({
                'name': 'existing-server',
                'connection_uri': 'user@duplicate.com:22'
            }),
            content_type='application/json'
        )
        assert 'message' in json.loads(response.data)

    def test_add_missing_fields(self, client):
        """Test adding with missing fields returns 400."""
        response = client.post('/add',
            data=json.dumps({'name': 'incomplete'}),
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_add_invalid_json(self, client):
        """Test adding with invalid request returns 400."""
        response = client.post('/add',
            data='not json',
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_edit_success(self, client):
        """Test editing an existing host."""
        response = client.put('/edit',
            data=json.dumps({
                'name': 'existing-server',
                'connection_uri': 'newuser@newhost.com:2222'
            }),
            content_type='application/json'
        )
        assert response.status_code == 200

    def test_edit_with_id_file(self, client):
        """Test editing a host to add identity file."""
        response = client.put('/edit',
            data=json.dumps({
                'name': 'existing-server',
                'connection_uri': 'admin@existing.example.com:22',
                'id_file': '/new/key.pem'
            }),
            content_type='application/json'
        )
        assert response.status_code == 200

    def test_edit_remove_id_file(self, client):
        """Test editing a host to remove identity file."""
        # First add a host with id_file
        client.post('/add',
            data=json.dumps({
                'name': 'id-server',
                'connection_uri': 'user@idserver.com:22',
                'id_file': '/key.pem'
            }),
            content_type='application/json'
        )

        # Edit to remove id_file by passing empty string
        response = client.put('/edit',
            data=json.dumps({
                'name': 'id-server',
                'connection_uri': 'user@idserver.com:22',
                'id_file': ''
            }),
            content_type='application/json'
        )
        assert response.status_code == 200

    def test_edit_nonexistent(self, client):
        """Test editing a non-existent host returns 404."""
        response = client.put('/edit',
            data=json.dumps({
                'name': 'nonexistent-server',
                'connection_uri': 'user@host.com:22'
            }),
            content_type='application/json'
        )
        assert response.status_code == 404

    def test_edit_missing_fields(self, client):
        """Test editing with missing fields returns 400."""
        response = client.put('/edit',
            data=json.dumps({'name': 'existing-server'}),
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_delete_success(self, client):
        """Test deleting an existing host."""
        # First verify it exists
        list_response = client.get('/list')
        data = json.loads(list_response.data)
        hosts = [entry.get('host') for entry in data]
        assert 'existing-server' in hosts

        # Delete it
        response = client.post('/delete',
            data=json.dumps({'name': 'existing-server'}),
            content_type='application/json'
        )
        assert response.status_code == 200

        # Verify it's gone
        list_response = client.get('/list')
        data = json.loads(list_response.data)
        hosts = [entry.get('host') for entry in data]
        assert 'existing-server' not in hosts

    def test_delete_nonexistent(self, client):
        """Test deleting a non-existent host returns 404."""
        response = client.post('/delete',
            data=json.dumps({'name': 'nonexistent-server'}),
            content_type='application/json'
        )
        assert response.status_code == 404

    def test_delete_missing_name(self, client):
        """Test deleting with missing name returns 400."""
        response = client.post('/delete',
            data=json.dumps({}),
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_favicon(self, client):
        """Test favicon endpoint."""
        response = client.get('/favicon.ico')
        # May return 200 or 404 depending on file existence
        assert response.status_code in [200, 404]


class TestWebSecurity:
    """Hardening of the local web UI."""

    def test_theme_param_cannot_inject_markup(self, client):
        response = client.get('/?theme=%22%3E%3Cscript%3Ealert(1)%3C/script%3E')
        assert response.status_code == 200
        assert b'<script>alert(1)' not in response.data
        assert b'themes/modern/style.css' in response.data

    @pytest.mark.parametrize("theme", ["modern", "black", "storm"])
    def test_known_themes_are_used(self, client, theme):
        response = client.get(f'/?theme={theme}')
        assert f'themes/{theme}/style.css'.encode() in response.data

    def test_invalid_configured_theme_falls_back(self, client, monkeypatch):
        import storm.web as web
        monkeypatch.setattr(web, "__THEME__", "nonsense")
        response = client.get('/')
        assert b'themes/modern/style.css' in response.data

    @pytest.mark.parametrize("host", ["evil.example.com", "evil.example.com:9002",
                                      "127.0.0.1.evil.com", "localhost.evil.com:80"])
    def test_foreign_host_header_is_refused(self, client, host):
        assert client.get('/list', headers={'Host': host}).status_code == 403
        assert client.post('/delete', json={'name': 'existing-server'},
                           headers={'Host': host}).status_code == 403

    @pytest.mark.parametrize("host", ["localhost", "localhost:9002", "127.0.0.1:9002", "[::1]:9002"])
    def test_local_host_header_is_allowed(self, client, host):
        assert client.get('/list', headers={'Host': host}).status_code == 200

    def test_form_post_is_rejected(self, client):
        # A cross-site HTML form cannot send application/json.
        response = client.post('/delete', data={'name': 'existing-server'})
        assert response.status_code == 415

    def test_add_rejects_injection(self, client):
        response = client.post('/add', json={
            'name': 'evil\n    ProxyCommand touch /tmp/pwned',
            'connection_uri': 'example.com',
        })
        assert response.status_code == 400
        assert b'line breaks' in response.data

    def test_add_bad_port_is_400(self, client):
        response = client.post('/add', json={'name': 'n', 'connection_uri': 'h:notaport'})
        assert response.status_code == 400

    def test_add_uses_host_star_defaults(self, client):
        client.post('/add', json={'name': 'n', 'connection_uri': 'h.example.com'})
        entry = next(e for e in json.loads(client.get('/list').data) if e['host'] == 'n')
        assert entry['options']['user'] == 'defaultuser'

    def test_edit_invalid_value_is_400(self, client):
        response = client.put('/edit', json={
            'name': 'existing-server', 'connection_uri': 'h:99999'})
        assert response.status_code == 400

    def test_edit_remove_id_file_when_none_set(self, client):
        response = client.put('/edit', json={
            'name': 'existing-server', 'connection_uri': 'admin@x.com', 'id_file': ''})
        assert response.status_code == 200


class TestWebRun:
    def test_run_configures_app(self, monkeypatch, tmp_path):
        import storm.web as web

        config = tmp_path / "cfg"
        config.write_text("Host a\n    hostname x\n")
        calls = {}
        monkeypatch.setattr(web.app, "run", lambda **kwargs: calls.update(kwargs))
        monkeypatch.setattr(web, "__THEME__", "modern")

        web.run("9005", 0, "storm", str(config))

        assert calls == {"port": 9005, "debug": False}
        assert web.__THEME__ == "storm"
        assert web.app.get_storm().is_host_in("a")
