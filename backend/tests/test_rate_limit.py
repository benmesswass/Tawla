from app.core.config import settings
from app.core.rate_limit import _hits

_LOGIN = {"email": "ratelimit@test.local", "password": "whatever123"}


def _login(client, forwarded_for: str | None = None):
    headers = {"X-Forwarded-For": forwarded_for} if forwarded_for else {}
    return client.post("/api/v1/auth/login", json=_LOGIN, headers=headers)


def test_login_blocked_after_threshold(client):
    _hits.clear()
    try:
        payload = {"email": "ratelimit@test.local", "password": "whatever123"}
        for _ in range(20):
            res = client.post("/api/v1/auth/login", json=payload)
            assert res.status_code == 401  # unknown email, but not yet rate-limited

        res = client.post("/api/v1/auth/login", json=payload)
        assert res.status_code == 429
        assert res.json()["detail"]["code"] == "RATE_LIMITED"
    finally:
        _hits.clear()


def test_login_and_register_are_limited_independently(client):
    _hits.clear()
    try:
        for _ in range(20):
            client.post("/api/v1/auth/login", json={"email": "x@test.local", "password": "x"})

        res = client.post(
            "/api/v1/auth/register",
            json={
                "restaurant_name": "Rate Limit Café",
                "manager_name": "Manager",
                "email": "owner@ratelimit.test",
                "password": "secret1234",
            },
        )
        assert res.status_code == 201
    finally:
        _hits.clear()


def test_deux_clients_derriere_le_proxy_ne_partagent_pas_le_compteur(client, monkeypatch):
    """
    Le défaut T3 : en production le seul pair TCP est le proxy de
    l'hébergeur, donc tout le parc partageait un compteur de 20 requêtes par
    minute. Le premier téléphone à en abuser bloquait le restaurant entier.
    """
    monkeypatch.setattr(settings, "forwarded_allow_ips", "testclient")

    for _ in range(20):
        assert _login(client, "41.226.0.1").status_code == 401
    assert _login(client, "41.226.0.1").status_code == 429

    # Le téléphone de la table d'à côté n'a rien fait : il passe.
    assert _login(client, "41.226.0.2").status_code == 401


def test_en_tete_forwarded_ignore_quand_il_ne_vient_pas_du_proxy(client, monkeypatch):
    """Sans proxy déclaré, l'en-tête vient de n'importe qui : le croire
    reviendrait à offrir un compteur neuf à chaque requête, donc à supprimer
    le limiteur."""
    monkeypatch.setattr(settings, "forwarded_allow_ips", "")

    for i in range(20):
        assert _login(client, f"41.226.0.{i}").status_code == 401
    assert _login(client, "41.226.0.99").status_code == 429


def test_un_client_ne_peut_pas_se_forger_une_ip_neuve_a_chaque_appel(client, monkeypatch):
    """
    Le client envoie son propre `X-Forwarded-For` ; le proxy y ajoute l'IP
    réelle qu'il a constatée. C'est la dernière valeur qui fait foi — lire la
    première rendrait le limiteur contournable en une ligne de code client.
    """
    monkeypatch.setattr(settings, "forwarded_allow_ips", "testclient")

    for i in range(20):
        assert _login(client, f"9.9.9.{i}, 41.226.0.7").status_code == 401
    assert _login(client, "9.9.9.200, 41.226.0.7").status_code == 429
