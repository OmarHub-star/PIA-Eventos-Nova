"""La interfaz web convive con la API segura sin modificar los permisos."""

from tests.conftest import auth


def test_home_is_a_real_web_portal(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    html = response.text
    assert "<title>Eventos Nova" in html
    assert 'id="loginForm"' in html
    assert 'id="appScreen"' in html
    assert 'id="actionForm"' in html
    assert 'data-nav="eventos"' in html
    assert 'data-nav="solicitudes"' in html
    assert "localStorage" not in html
    assert "sessionStorage" not in html


def test_ui_does_not_open_protected_api_without_token(client):
    assert client.get("/events").status_code == 401
    assert client.get("/requests").status_code == 401
    assert client.get("/catalogs/client").status_code == 401
    assert client.get("/me").status_code == 401
    assert client.get("/me", headers=auth("coord")).json() == {
        "id": "COORD-001",
        "role": "COORDINADOR",
    }
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/health").json()["status"] == "ok"
