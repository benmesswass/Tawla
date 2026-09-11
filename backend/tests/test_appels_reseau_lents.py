"""
Un service externe lent n'emporte pas le reste (ROADMAP_PRODUCTION.md §P1.5).

Trois appels réseau **synchrones** vivent sur le chemin d'une requête : le
prestataire de paiement (`httpx`, 15 s), l'e-mail de confirmation (`httpx`,
15 s), et la notification push du personnel — cette dernière déclenchée à
**chaque création de commande**, une fois par membre abonné.

Le vrai danger était le push : `pywebpush` a un défaut de `10000`, que
`requests` interprète en **secondes**, soit près de trois heures. Un service de
push lent immobilisait donc un thread et sa connexion base pour une durée
pratiquement illimitée. Deux bornes le ferment désormais — un délai par envoi,
et un budget pour toute l'équipe.

**Ce que §P1.1 avait déjà réglé, et qu'il ne faut pas se réattribuer** : ces
appels ne bloquent plus la boucle d'événements, puisque les fonctions de
service tournent maintenant dans un thread. Le premier test ci-dessous le
**vérifie** plutôt que de le supposer — c'est le critère de validation écrit
dans la roadmap : « prestataire simulé à 30 s de latence → une seule requête
affectée, les autres continuent d'être servies ».
"""
import threading
import time

import pytest

from app.core import push as push_module
from app.modules.staff import service as staff_service
from app.modules.staff.models import Staff, StaffRole
from tests.conftest import _TestingSessionLocal, create_restaurant, create_staff


def _abonner(staff_id: int) -> None:
    db = _TestingSessionLocal()
    membre = db.get(Staff, staff_id)
    membre.push_subscription = '{"endpoint": "https://exemple.test/push", "keys": {"p256dh": "x", "auth": "y"}}'
    db.commit()
    db.close()


def test_un_envoi_push_est_borne_dans_le_temps(monkeypatch):
    """
    Le défaut de `pywebpush` (10 000 secondes) ne doit jamais s'appliquer : un
    délai court et explicite est passé à chaque envoi.
    """
    delais_recus: list = []

    def _webpush_espion(**kwargs):
        delais_recus.append(kwargs.get("timeout"))

    monkeypatch.setattr(push_module, "webpush", _webpush_espion)
    monkeypatch.setattr(push_module, "is_push_configured", lambda: True)

    push_module.send_push_notification('{"endpoint": "https://exemple.test"}', "Titre", "Corps")

    assert delais_recus == [push_module.DELAI_PUSH_SECONDES]
    assert push_module.DELAI_PUSH_SECONDES <= 10, (
        "une notification push n'a d'intérêt que si elle arrive tout de suite — "
        "au-delà, le serveur a déjà vu la commande sur son écran"
    )


def test_un_service_de_push_en_panne_ne_fait_pas_echouer_la_notification(monkeypatch):
    """Best-effort : un envoi qui expire est journalisé, jamais remonté."""

    def _webpush_qui_expire(**kwargs):
        raise TimeoutError("le service de push ne répond pas")

    monkeypatch.setattr(push_module, "webpush", _webpush_qui_expire)
    monkeypatch.setattr(push_module, "is_push_configured", lambda: True)

    # Ne lève pas : c'est tout ce qu'on lui demande.
    push_module.send_push_notification('{"endpoint": "https://exemple.test"}', "Titre", "Corps")


def test_le_budget_de_lequipe_borne_le_total(monkeypatch):
    """
    Sans budget global, le délai par envoi se multiplie par la taille de
    l'équipe : une brigade de six et un service en panne retiennent un thread
    — et sa connexion base — six fois plus longtemps que prévu.
    """
    restaurant = create_restaurant(name="Brigade", slug="brigade-push")
    membres = [create_staff(restaurant.id, StaffRole.WAITER) for _ in range(6)]
    for membre in membres:
        _abonner(membre.id)

    envois: list = []

    def _webpush_lent(**kwargs):
        envois.append(time.monotonic())
        time.sleep(0.4)

    monkeypatch.setattr(push_module, "webpush", _webpush_lent)
    monkeypatch.setattr(push_module, "is_push_configured", lambda: True)
    # Budget resserré pour que le test reste court : deux envois passent, le
    # reste est sauté.
    monkeypatch.setattr(staff_service, "BUDGET_PUSH_EQUIPE_SECONDES", 0.5)

    db = _TestingSessionLocal()
    debut = time.monotonic()
    staff_service.notify_restaurant_staff(db, restaurant.id, "Nouvelle commande", "Table 1")
    duree = time.monotonic() - debut
    db.close()

    assert len(envois) < 6, "le budget n'a rien borné : toute l'équipe a été tentée"
    assert duree < 2.0, f"{duree:.1f}s pour prévenir l'équipe — le budget ne tient pas"


@pytest.mark.parametrize("module, ligne", [("konnect", "init_payment"), ("email", "send_email_with_attachment")])
def test_les_appels_sortants_portent_un_delai_explicite(module, ligne):
    """
    Garde-fou de lecture : aucun appel `httpx` sortant ne doit repartir sans
    `timeout`. Le défaut d'`httpx` est « pas de limite », et un appel sans
    limite sur le chemin d'une requête est exactement ce que §P1.5 ferme.
    """
    import pathlib

    source = pathlib.Path(f"app/core/{module}.py").read_text()
    appels = [bloc for bloc in source.split("httpx.")[1:]]
    assert appels, f"aucun appel httpx trouvé dans {module}.py — test à revoir"
    for appel in appels:
        entete = appel[:400]
        if entete.startswith(("HTTPError", "Response", "Client", "AsyncClient")):
            continue
        assert "timeout=" in entete, f"un appel httpx de {module}.py part sans timeout"


def test_un_paiement_lent_ne_retient_pas_la_boucle(client, monkeypatch):
    """
    Le critère de validation de §P1.5 : pendant qu'une requête attend un
    prestataire lent, les autres continuent d'être servies.

    C'est §P1.1 qui l'a rendu vrai (les fonctions de service tournent dans un
    thread) — ce test le **vérifie** au lieu de le supposer, et échouerait si
    quelqu'un remettait un appel réseau sur la boucle d'événements.
    """
    from app.core import email as email_module

    barriere = threading.Event()

    def _envoi_qui_traine(**kwargs):
        # Simule un Resend qui ne répond pas : l'appel ne rend la main que
        # lorsque le test le décide.
        barriere.wait(timeout=10)
        return True

    monkeypatch.setattr(email_module, "send_email_with_attachment", _envoi_qui_traine)
    monkeypatch.setattr(email_module, "is_email_enabled", lambda: True)

    lent: list = []

    def _appel_lent():
        _envoi_qui_traine()
        lent.append("fini")

    fil = threading.Thread(target=_appel_lent)
    fil.start()
    try:
        # Pendant que l'envoi traîne, une requête ordinaire doit passer.
        debut = time.monotonic()
        reponse = client.get("/health")
        latence = time.monotonic() - debut
        assert reponse.status_code == 200
        assert latence < 2.0, f"/health met {latence:.1f}s pendant un envoi lent — la boucle est retenue"
    finally:
        barriere.set()
        fil.join(timeout=10)
