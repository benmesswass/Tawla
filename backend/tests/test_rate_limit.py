import app.core.rate_limit as rate_limit_module
from app.core.rate_limit import _WINDOW_SECONDS, _hits, _sweep_expired
from tests.conftest import auth_headers, create_restaurant, create_staff

_LOGIN = {"email": "ratelimit@test.local", "password": "whatever123"}


def _login(client, cf_connecting_ip: str | None = None):
    headers = {"CF-Connecting-IP": cf_connecting_ip} if cf_connecting_ip else {}
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


def test_deux_clients_derriere_cloudflare_ne_partagent_pas_le_compteur(client):
    """
    Le défaut T3 : le pair TCP vu par le conteneur est une adresse interne à
    l'hébergeur, qui change à chaque requête (vérifié en prod, Phase 20/19.3,
    2026-08-18) — impossible de s'y fier. `CF-Connecting-IP`, posé par
    Cloudflare devant Render (y compris sur le sous-domaine onrender.com brut)
    et rejeté en 403 à l'edge s'il est forgé par le client, est la seule
    valeur fiable.
    """
    _hits.clear()
    try:
        for _ in range(20):
            assert _login(client, "41.226.0.1").status_code == 401
        assert _login(client, "41.226.0.1").status_code == 429

        # Le téléphone de la table d'à côté n'a rien fait : il passe.
        assert _login(client, "41.226.0.2").status_code == 401
    finally:
        _hits.clear()


def test_un_x_forwarded_for_force_ne_contourne_pas_le_compteur(client):
    """
    X-Forwarded-For est ignoré, quelle que soit sa valeur : Cloudflare y
    ajoute sa propre entrée sans écraser ce qu'un client y a mis, donc la
    première valeur de la liste est forgeable (vérifié en prod : un
    X-Forwarded-For envoyé par curl survit tel quel en tête de liste).
    CF-Connecting-IP prime toujours sur ce que le client envoie par ailleurs.
    """
    _hits.clear()
    try:
        headers = {"CF-Connecting-IP": "41.226.0.5"}
        for i in range(20):
            headers["X-Forwarded-For"] = f"9.9.9.{i}"
            assert client.post("/api/v1/auth/login", json=_LOGIN, headers=headers).status_code == 401
        headers["X-Forwarded-For"] = "9.9.9.200"
        assert client.post("/api/v1/auth/login", json=_LOGIN, headers=headers).status_code == 429
    finally:
        _hits.clear()


def test_une_ip_qui_ne_revient_jamais_finit_par_etre_oubliee(client):
    """
    S-6 : `_hits` créait une clé par (IP, route) et ne la supprimait jamais,
    même une fois toutes ses requêtes sorties de la fenêtre glissante — fuite
    lente sur une IP qui ne revient jamais (client mobile, IP publique qui
    tourne). Le balayage périodique doit purger une clé entièrement expirée.
    """
    _hits.clear()
    original_last_sweep = rate_limit_module._last_sweep
    try:
        assert _login(client, "41.226.0.99").status_code == 401
        key = ("41.226.0.99", "/api/v1/auth/login")
        assert key in _hits

        # Force le balayage (normalement retardé de _WINDOW_SECONDS) et
        # simule le temps écoulé depuis la seule requête de cette IP —
        # `time.monotonic()` ne repart pas de zéro, il faut donc avancer
        # depuis le timestamp réel enregistré, pas depuis une valeur absolue.
        rate_limit_module._last_sweep = 0.0
        _sweep_expired(now=_hits[key][-1] + _WINDOW_SECONDS + 1)

        assert key not in _hits
    finally:
        rate_limit_module._last_sweep = original_last_sweep
        _hits.clear()


def test_toute_la_salle_derriere_le_meme_wifi_peut_commander(client):
    """
    S-2b : depuis que le limiteur identifie enfin le vrai client (S-2a), tout
    le monde derrière le Wi-Fi du restaurant partage la même IP publique — un
    plafond pensé pour un individu (20/min) bloquerait un coup de feu où
    plusieurs tables commandent à la même minute. Vérifie que la salle peut
    dépasser ce plafond individuel sans être bloquée.
    """
    _hits.clear()
    try:
        headers = {"CF-Connecting-IP": "41.226.0.10"}

        restaurant = create_restaurant(name="Le Rush", slug="rate-limit-rush")
        staff_headers = auth_headers(create_staff(restaurant.id))
        table = client.post(
            "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1"}, headers=staff_headers
        ).json()
        item = client.post(
            "/api/v1/menu-items",
            json={"restaurant_id": restaurant.id, "name": "Couscous", "price": 20},
            headers=staff_headers,
        ).json()

        for _ in range(25):
            res = client.post(
                "/api/v1/orders",
                json={"qr_token": table["qr_token"], "items": [{"menu_item_id": item["id"], "quantity": 1}]},
                headers=headers,
            )
            assert res.status_code == 201, res.text
    finally:
        _hits.clear()
