import requests


def test_getting_logs_for_nonexisting_notebook_returns_404(base_url, headers):
    response = requests.get(f"{base_url}/logs/non-existing", headers=headers)
    assert response.status_code == 404


def test_deleting_nonexisting_servers_returns_404(base_url, headers):
    response = requests.delete(f"{base_url}/servers/non-existing", headers=headers)
    assert response.status_code == 404


def test_getting_status_for_nonexisting_notebooks_returns_404(base_url, headers):
    response = requests.get(f"{base_url}/servers/non-existing", headers=headers)
    assert response.status_code == 404
