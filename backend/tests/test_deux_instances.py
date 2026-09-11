"""
Deux instances backend qui servent le même restaurant
(ROADMAP_PRODUCTION.md §P2.1 — le critère de validation de la tâche).

C'est le test qui dit si P2.1 est faite ou non, et rien d'autre ne peut le
dire : tant que le registre WebSocket, le panier de table et le roster vivaient
dans des dicts de module, **une commande passée sur l'instance A n'apparaissait
jamais sur l'écran connecté à l'instance B**, et deux téléphones de la même
table pouvaient tomber sur deux paniers différents. La contrainte « une seule
instance backend » était explicite dans `ROADMAP.md` ; c'est elle qui tombe
ici, et P2 entier est la condition d'existence de P3.

**Deux vrais processus `uvicorn`**, pas deux objets `app` dans le même
interpréteur : deux `app` partageraient les mêmes dicts de module et le test
serait vert avant comme après la correction — exactement le faux négatif
documenté dans `test_concurrence_commandes.py`, sous une autre forme. Ils
partagent un vrai PostgreSQL et un vrai Redis, comme en production derrière un
répartiteur.

Sauté d'office sans `TEST_DATABASE_URL` **et** `TEST_REDIS_URL` : c'est un test
d'infrastructure, il n'a pas sa place sur un poste de dev où `pytest -q` doit
rester une commande sans prérequis.
"""
import asyncio
import json
import os
import socket
import subprocess
import sys
import time

import httpx
import pytest
import websockets
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.modules.menu.models import MenuItem
from app.modules.staff.models import Staff, StaffRole
from app.modules.staff.security import create_access_token, hash_password
from app.modules.tables.models import Table
from app.modules.tenants.models import Restaurant, SubscriptionTier

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
TEST_REDIS_URL = os.environ.get("TEST_REDIS_URL")

besoin_des_deux = pytest.mark.skipif(
    not (TEST_DATABASE_URL and TEST_REDIS_URL),
    reason="TEST_DATABASE_URL et TEST_REDIS_URL requises — test deux instances ignoré",
)

# Large : on cherche « est-ce que ça traverse », pas une latence fine. Un
# message qui n'arrive pas en 15 s n'arrivera jamais.
DELAI_MAX = 15.0


def _port_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _preparer_la_salle() -> dict:
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    restaurant = Restaurant(
        name="Deux instances",
        slug="deux-instances",
        is_active=True,
        subscription_tier=SubscriptionTier.BUSINESS,
        has_paid_for_subscription=True,
    )
    db.add(restaurant)
    db.flush()
    table = Table(restaurant_id=restaurant.id, label="Table 1")
    plat = MenuItem(restaurant_id=restaurant.id, name="Couscous", price=20.0, category="Plats")
    serveur = Staff(
        restaurant_id=restaurant.id, name="Sami", role=StaffRole.WAITER,
        email="sami@deux-instances.test", password_hash=hash_password("un-mot-de-passe-1234"),
    )
    db.add_all([table, plat, serveur])
    db.commit()
    contexte = {
        "restaurant_id": restaurant.id,
        "qr_token": table.qr_token,
        "table_id": table.id,
        "plat_id": plat.id,
        "jeton_serveur": create_access_token(serveur.id, restaurant.id, StaffRole.WAITER.value),
    }
    db.close()
    engine.dispose()
    return contexte


def _demarrer_instance(nom: str, redis_url: str = TEST_REDIS_URL) -> tuple[subprocess.Popen, str]:
    port = _port_libre()
    env = {
        **os.environ,
        "DATABASE_URL": TEST_DATABASE_URL,
        "REDIS_URL": redis_url,
        "ENV": "development",
        "VAPID_PUBLIC_KEY": "",
        "VAPID_PRIVATE_KEY": "",
        "RESEND_API_KEY": "",
        "POSTHOG_API_KEY": "",
    }
    processus = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "warning"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    base = f"http://127.0.0.1:{port}"
    limite = time.monotonic() + 60
    while time.monotonic() < limite:
        if processus.poll() is not None:
            raise RuntimeError(f"instance {nom} arrêtée au démarrage :\n{processus.stdout.read()}")
        try:
            if httpx.get(f"{base}/health", timeout=2).status_code == 200:
                return processus, base
        except httpx.HTTPError:
            time.sleep(0.3)
    processus.kill()
    raise RuntimeError(f"instance {nom} pas prête en 60 s")


@pytest.fixture()
def deux_instances():
    """
    Deux `uvicorn` derrière le même Postgres et le même Redis.

    Redis est vidé au départ, et ce n'est pas du zèle : les compteurs du
    limiteur de débit vivent maintenant **hors du processus pytest**, donc la
    remise à zéro de `conftest.py` ne les atteint plus. Sans ce vidage, deux
    exécutions du même test à moins d'une minute d'intervalle se partagent la
    fenêtre glissante et la seconde part avec un quota déjà entamé.
    """
    import redis

    redis.Redis.from_url(TEST_REDIS_URL).flushdb()
    contexte = _preparer_la_salle()
    processus_a, base_a = _demarrer_instance("A")
    try:
        processus_b, base_b = _demarrer_instance("B")
    except Exception:
        processus_a.kill()
        raise
    try:
        yield base_a, base_b, contexte
    finally:
        for p in (processus_a, processus_b):
            p.kill()
            p.wait(timeout=10)


def _ws(base: str, chemin: str) -> str:
    return base.replace("http://", "ws://") + chemin


async def _attendre(socket_ws, evenement: str) -> dict:
    """Lit jusqu'à l'événement attendu — les canaux envoient aussi des
    rattrapages à la connexion, qui ne sont pas ce qu'on mesure."""
    limite = asyncio.get_event_loop().time() + DELAI_MAX
    while asyncio.get_event_loop().time() < limite:
        restant = limite - asyncio.get_event_loop().time()
        brut = await asyncio.wait_for(socket_ws.recv(), timeout=restant)
        message = json.loads(brut)
        if message.get("event") == evenement:
            return message
    raise AssertionError(f"événement '{evenement}' jamais reçu en {DELAI_MAX} s")


@besoin_des_deux
def test_une_commande_passee_sur_A_arrive_sur_lecran_connecte_a_B(deux_instances):
    """
    **Le critère de sortie de P2.1.** Le client commande depuis le téléphone,
    que le répartiteur envoie sur l'instance A ; le serveur en salle a son
    écran ouvert depuis ce matin, sur l'instance B. Sans état partagé, il ne
    voit jamais la commande — et personne ne s'en aperçoit avant qu'un client
    ne s'impatiente.
    """
    base_a, base_b, ctx = deux_instances

    async def scenario():
        url = _ws(base_b, f"/ws/staff/{ctx['restaurant_id']}?token={ctx['jeton_serveur']}")
        async with websockets.connect(url) as ecran_serveur:
            async with httpx.AsyncClient(timeout=10) as client:
                reponse = await client.post(
                    f"{base_a}/api/v1/orders",
                    json={"qr_token": ctx["qr_token"],
                          "items": [{"menu_item_id": ctx["plat_id"], "quantity": 2}]},
                )
            assert reponse.status_code == 201, reponse.text
            message = await _attendre(ecran_serveur, "order.pending_confirmation")
            return reponse.json(), message

    commande, message = asyncio.run(scenario())
    assert message["order_id"] == commande["id"]
    assert message["table_id"] == ctx["table_id"]


@besoin_des_deux
def test_le_panier_de_table_est_le_meme_des_deux_cotes(deux_instances):
    """
    Deux téléphones de la même tablée, répartis sur deux instances. Celui qui
    ajoute un plat sur A doit le voir apparaître chez celui qui est sur B —
    c'est tout le principe du panier partagé, et c'était impossible tant qu'il
    vivait dans un dict de processus.
    """
    base_a, base_b, ctx = deux_instances

    # Le premier `cart.updated` reçu par B est son propre rattrapage (panier
    # vide) : on boucle jusqu'à voir la ligne ajoutée par A.
    async def scenario():
        url_a = _ws(base_a, f"/ws/table/{ctx['restaurant_id']}/{ctx['qr_token']}")
        url_b = _ws(base_b, f"/ws/table/{ctx['restaurant_id']}/{ctx['qr_token']}")
        async with websockets.connect(url_a) as tel_a, websockets.connect(url_b) as tel_b:
            await tel_a.send(json.dumps({
                "action": "cart.set", "menu_item_id": ctx["plat_id"], "quantity": 3,
            }))
            limite = asyncio.get_event_loop().time() + DELAI_MAX
            while asyncio.get_event_loop().time() < limite:
                message = await _attendre(tel_b, "cart.updated")
                if message["lines"]:
                    return message
            raise AssertionError("le panier de A n'est jamais arrivé sur B")

    message = asyncio.run(scenario())
    assert [(l["menu_item_id"], l["quantity"]) for l in message["lines"]] == [(ctx["plat_id"], 3)]


@besoin_des_deux
def test_le_limiteur_de_debit_est_commun_aux_deux_instances(deux_instances):
    """
    Un compteur par processus n'est pas un plafond, c'est une suggestion : deux
    instances derrière un répartiteur donnaient deux fois le plafond à qui
    tente un brute-force sur l'authentification. Ici on épuise le quota moitié
    sur A, moitié sur B, et le refus doit tomber quand même.
    """
    base_a, base_b, _ctx = deux_instances
    identifiants = {"email": "inconnu@deux-instances.test", "password": "peu-importe-1234"}
    entete = {"CF-Connecting-IP": "41.226.0.42"}

    codes = []
    for i in range(22):
        base = base_a if i % 2 == 0 else base_b
        # Généreux : `/auth/login` compare un hash bcrypt même sur un e-mail
        # inconnu (anti-timing), et deux uvicorn plus Postgres plus Redis
        # tournent sur la même machine que la suite.
        codes.append(
            httpx.post(f"{base}/api/v1/auth/login", json=identifiants, headers=entete, timeout=30).status_code
        )

    assert 429 in codes, (
        "aucune des 22 tentatives n'a été refusée alors que le plafond est de 20 : "
        "chaque instance compte encore pour elle seule"
    )
    # Et le plafond doit tomber au bon endroit, pas n'importe où.
    assert codes.index(429) == 20, f"refus au coup {codes.index(429) + 1} au lieu du 21ᵉ : {codes}"


@besoin_des_deux
def test_temoin_sans_magasin_partage_la_commande_reste_sur_son_instance():
    """
    **Le témoin, et il compte autant que les trois tests ci-dessus.**

    Sans lui, rien ne prouve qu'ils mesurent quoi que ce soit : un test vert
    des deux côtés d'une correction ne vaut rien, et c'est le piège qui a coûté
    deux réécritures à `test_concurrence_commandes.py`. Ici les deux mêmes
    instances démarrent **sans `REDIS_URL`** — donc exactement comme avant
    P2.1, chacune avec ses dicts de module — et la commande passée sur A ne
    doit **pas** arriver sur l'écran connecté à B.

    Si ce test se met un jour à échouer, ce n'est pas lui qu'il faut corriger :
    c'est que le mode mémoire s'est mis à faire quelque chose qu'il ne peut pas
    faire, ou que les trois tests d'à côté passaient pour une autre raison que
    celle qu'ils annoncent.
    """
    contexte = _preparer_la_salle()
    processus_a, base_a = _demarrer_instance("A-sans-redis", redis_url="")
    try:
        processus_b, base_b = _demarrer_instance("B-sans-redis", redis_url="")
    except Exception:
        processus_a.kill()
        raise

    async def scenario():
        url = _ws(base_b, f"/ws/staff/{contexte['restaurant_id']}?token={contexte['jeton_serveur']}")
        async with websockets.connect(url) as ecran_serveur:
            async with httpx.AsyncClient(timeout=30) as client:
                reponse = await client.post(
                    f"{base_a}/api/v1/orders",
                    json={"qr_token": contexte["qr_token"],
                          "items": [{"menu_item_id": contexte["plat_id"], "quantity": 1}]},
                )
            assert reponse.status_code == 201, reponse.text
            # Quelques secondes suffisent : en mode Redis le message arrive en
            # quelques millisecondes.
            try:
                await asyncio.wait_for(ecran_serveur.recv(), timeout=3)
            except asyncio.TimeoutError:
                return "rien reçu"
            return "message reçu"

    try:
        assert asyncio.run(scenario()) == "rien reçu", (
            "l'écran connecté à B a reçu la commande passée sur A alors qu'aucune "
            "des deux instances ne partage son état : les autres tests de ce "
            "fichier ne prouvent donc rien"
        )
    finally:
        for p in (processus_a, processus_b):
            p.kill()
            p.wait(timeout=10)

