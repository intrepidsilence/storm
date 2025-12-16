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
