"""
Tenue sous commandes simultanées — le test N0 (ROADMAP_PRODUCTION.md §P1.1, §P1.9).

Ce que ce test empêche de revenir, mesuré le 2026-09-10 sur le code d'alors :

    40 requetes simultanees sur POST /orders -> 1/40 OK en 70.8s
    puis /health INJOIGNABLE, definitivement (seul un redemarrage recupere)

La cause n'était pas la base — la même rafale sur un endpoint déclaré `def`
passait 40/40 en 0,6 s, serveur sain. C'était le modèle d'exécution : un
handler `async def` qui exécute du SQLAlchemy **synchrone** bloque la boucle
d'événements à chaque appel base. Une session garde sa connexion jusqu'à son
`close()`, donc à travers les `await` du handler (diffusion WebSocket…) : à
chaque suspension, une autre requête démarre et prend une connexion de plus.
Le pool s'épuise, l'attente d'une connexion se produit *dans* la boucle, et
plus rien ne peut libérer quoi que ce soit puisque libérer demande que la
boucle avance. Interblocage, pas dégradation.

**Deux pièges rencontrés en écrivant ce test**, tous deux donnant un faux
négatif — un test vert des DEUX côtés de la correction, donc sans valeur :

1. `TestClient` sérialise les requêtes derrière son portail : 40 appels y
   passent un par un, chacun rendant sa connexion avant que le suivant
   démarre. Il faut de vraies sockets et un vrai `uvicorn`, lancé comme en
   production.
2. 40 threads clients ne suffisent pas non plus : le GIL les étale sur des
   dizaines de millisecondes, et le serveur draine entre deux. Il faut de la
   concurrence **réelle** côté client — `asyncio.gather` sur un client async,
   qui écrit les 40 requêtes sur les sockets en quelques microsecondes.

Vérifié : sur le code d'avant correction, ce test échoue (0/40, serveur mort) ;
avec des threads, il passait.

Postgres réel obligatoire, même parti pris que `test_pool_connexions.py`.
"""
import asyncio
import os
import socket
import subprocess
import sys
import time

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.modules.menu.models import MenuItem
from app.modules.orders.models import Order
from app.modules.tables.models import Table
from app.modules.tenants.models import Restaurant, SubscriptionTier

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

besoin_de_postgres = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL non posée — test de concurrence ignoré (voir docstring du module)",
)

# La rafale du scénario mesuré. 40 commandes simultanées, ce n'est pas un test
# de stress : c'est deux restaurants un vendredi soir. La cible est 100.
RAFALE = 40

# Pool volontairement plus petit que la rafale — sinon rien ne serait mis à
# l'épreuve : c'est la contention qui déclenchait l'interblocage, pas le volume.
POOL_SIZE = 5
MAX_OVERFLOW = 5

# Large : on cherche « est-ce que ça se verrouille », pas une performance fine.
# Le cas défaillant mettait 70 s pour 1 requête sur 40, et ne revenait jamais.
DELAI_MAX = 60.0


def _port_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _preparer_la_salle(url: str) -> dict:
    engine = create_engine(url)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    restaurant = Restaurant(
        name="Le vendredi soir",
        slug="vendredi-soir",
        is_active=True,
        subscription_tier=SubscriptionTier.BUSINESS,
        has_paid_for_subscription=True,
    )
    db.add(restaurant)
    db.flush()
    tables = [Table(restaurant_id=restaurant.id, label=f"Table {i}") for i in range(RAFALE)]
    plat = MenuItem(restaurant_id=restaurant.id, name="Couscous", price=20.0, category="Plats")
    db.add_all([*tables, plat])
    db.commit()
    contexte = {
        "restaurant_id": restaurant.id,
        "qr_tokens": [t.qr_token for t in tables],
        "plat_id": plat.id,
    }
    db.close()
    engine.dispose()
    return contexte


@pytest.fixture()
def serveur_reel():
    """
    Un vrai `uvicorn`, lancé comme le `CMD` du Dockerfile, contre le Postgres
    de test et avec un pool étroit. Rendu : `(url_de_base, contexte, Session)`.
    """
    contexte = _preparer_la_salle(TEST_DATABASE_URL)
    port = _port_libre()
    env = {
        **os.environ,
        "DATABASE_URL": TEST_DATABASE_URL,
        "ENV": "development",
        "DB_POOL_SIZE": str(POOL_SIZE),
        "DB_MAX_OVERFLOW": str(MAX_OVERFLOW),
        "DB_POOL_TIMEOUT": "5",
        # Les envois réels (push, e-mail) sont déjà désactivés sans clés ; on
        # ne veut surtout pas qu'un appel réseau entre dans la mesure.
        "VAPID_PUBLIC_KEY": "",
        "VAPID_PRIVATE_KEY": "",
        "RESEND_API_KEY": "",
        "POSTHOG_API_KEY": "",
    }
    processus = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port),
         "--log-level", "warning"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        limite = time.monotonic() + 60
        while time.monotonic() < limite:
            if processus.poll() is not None:
                raise RuntimeError(f"uvicorn s'est arrêté au démarrage :\n{processus.stdout.read()}")
            try:
                if httpx.get(f"{base}/health", timeout=2).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.3)
        else:
            raise RuntimeError("uvicorn n'a pas démarré en 60 s")

        engine = create_engine(TEST_DATABASE_URL)
        yield base, contexte, sessionmaker(autocommit=False, autoflush=False, bind=engine)
        engine.dispose()
    finally:
        processus.terminate()
        try:
            processus.wait(timeout=10)
        except subprocess.TimeoutExpired:
            processus.kill()


async def _rafale_async(appel) -> tuple[list, float]:
    """
    Lance `RAFALE` appels **vraiment** simultanés : un seul client async, un
    seul `gather`. Voir le piège n°2 de la docstring du module — des threads
    ne reproduisent pas la contention.
    """
    async with httpx.AsyncClient(timeout=DELAI_MAX) as client:
        debut = time.monotonic()
        resultats = await asyncio.gather(
            *[appel(client, i) for i in range(RAFALE)], return_exceptions=True
        )
        duree = time.monotonic() - debut
    return [r if isinstance(r, int) else type(r).__name__ for r in resultats], duree


@besoin_de_postgres
def test_quarante_commandes_simultanees_aboutissent_toutes(serveur_reel):
    """
    Le test de non-régression de l'interblocage.

    Avant correction : 1 commande sur 40, puis un backend définitivement mort.
    """
    base, ctx, Session = serveur_reel

    async def _commander(client: httpx.AsyncClient, index: int) -> int:
        reponse = await client.post(
            f"{base}/api/v1/orders",
            json={
                "qr_token": ctx["qr_tokens"][index],
                "items": [{"menu_item_id": ctx["plat_id"], "quantity": 1}],
                "client_order_id": f"rafale-{index}",
            },
            # Une salle entière commande derrière le même Wi-Fi, mais chaque
            # téléphone a son IP publique : sans ça on mesurerait le limiteur
            # de débit au lieu de la tenue en charge.
            headers={"CF-Connecting-IP": f"41.226.0.{index}"},
        )
        return reponse.status_code

    resultats, duree = asyncio.run(_rafale_async(_commander))

    assert len(resultats) == RAFALE, (
        f"{RAFALE - len(resultats)} requête(s) ne sont jamais revenues en {DELAI_MAX} s — "
        "signature de l'interblocage : la boucle d'événements ne repart pas"
    )
    reussites = [r for r in resultats if r == 201]
    assert len(reussites) == RAFALE, (
        f"{len(reussites)}/{RAFALE} commandes abouties en {duree:.1f}s — "
        f"issues observées : {sorted(set(map(str, resultats)))}"
    )

    # Aucune commande perdue ni dupliquée.
    db = Session()
    assert db.query(Order).count() == RAFALE
    db.close()

    # Le vrai critère : le serveur est encore vivant APRÈS la rafale. C'est ce
    # que le défaut cassait — il ne revenait jamais, même sans aucun client.
    debut = time.monotonic()
    sante = httpx.get(f"{base}/health", timeout=15)
    latence = time.monotonic() - debut
    assert sante.status_code == 200, "le backend ne répond plus après la rafale"
    assert latence < 5.0, f"/health met {latence:.1f}s après la rafale — la boucle est engorgée"


@besoin_de_postgres
def test_la_lecture_de_carte_tient_la_meme_rafale(serveur_reel):
    """
    Le témoin de la mesure d'origine : cette rafale-ci passait déjà 40/40 en
    0,6 s AVANT correction, parce que l'endpoint est déclaré `def` et tourne
    donc dans le threadpool. Si elle se met à échouer, c'est que la correction
    a cassé le monde qui marchait, pas qu'elle a réparé l'autre.
    """
    base, ctx, _Session = serveur_reel

    async def _lire_la_carte(client: httpx.AsyncClient, index: int) -> int:
        reponse = await client.get(f"{base}/api/v1/menu-items/by-table/{ctx['qr_tokens'][index]}")
        return reponse.status_code

    resultats, duree = asyncio.run(_rafale_async(_lire_la_carte))

    assert len(resultats) == RAFALE
    assert all(r == 200 for r in resultats), (
        f"issues observées : {sorted(set(map(str, resultats)))} en {duree:.1f}s"
    )
    assert httpx.get(f"{base}/health", timeout=15).status_code == 200
