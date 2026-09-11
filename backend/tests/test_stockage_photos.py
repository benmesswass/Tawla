"""
Le stockage objet des photos (ROADMAP_PRODUCTION.md §P2.2, F8).

**Ce qui était en jeu.** Les photos — plats, bannière de couverture, logo —
étaient des `LargeBinary` dans Postgres, servies par le processus applicatif.
La raison de migrer n'est pas le coût de stockage : `AUDIT_COUTS_PRODUCTION.md`
§4.4 a chiffré quelques dinars par mois, et il avait raison. C'est que **chaque
photo servie immobilise une connexion du pool** le temps de transférer 150 à
300 Ko — la ressource que P1 vient de passer un palier entier à protéger.

Ces tests tournent contre un **vrai serveur S3 en mémoire** (`moto`), pas
contre un bouchon maison : un bouchon vérifie qu'on appelle `boto3` comme on
croit devoir l'appeler, jamais que `boto3` fait ce qu'on croit. La différence
compte ici, parce que personne ne relira ce code avant le jour où une carte
entière part sur R2.

L'ordre des tests suit l'ordre des risques :

1. **le mode par défaut ne bouge pas d'un iota** — sans configuration, les
   photos restent en base ; c'est ce que tourne le reste de la suite, et ce sur
   quoi le pilote tourne ;
2. **la colonne `LargeBinary` se vide vraiment** — sinon on aurait deux copies,
   et la base grossirait quand même ;
3. **l'URL devient absolue** — c'est ce qui fait que le backend n'est plus
   appelé DU TOUT, pas même pour une redirection ;
4. **remplacer ou retirer une photo ne laisse pas d'orphelin** payé à vie ;
5. **une configuration à moitié posée refuse de démarrer**, au lieu de servir
   une carte sans photos que personne ne comprend.
"""
import boto3
import pytest
from moto import mock_aws

from app.core.config import Settings
from app.core.stockage_photos import CACHE_PHOTOS, StockageEnBase
from tests.conftest import auth_headers, create_restaurant, create_staff

BUCKET = "tawla-photos-test"
BASE_PUBLIQUE = "https://photos.tawla.test"
JPEG = b"\xff\xd8\xff\xe0 des octets de photo"


@pytest.fixture()
def stockage_objet(monkeypatch):
    """
    Un `StockageObjet` branché sur un S3 en mémoire. `moto` intercepte boto3,
    donc le code testé est exactement celui de production — aucune injection,
    aucune sous-classe de test.

    Une seule concession : l'endpoint est celui d'AWS et non celui de R2.
    `moto` reconnaît les requêtes à leur hôte et **n'intercepte pas un
    `endpoint_url` personnalisé** — vérifié, la requête part alors vraiment sur
    le réseau. Ce que l'endpoint change, c'est l'adresse ; tout ce que ces
    tests vérifient (construction des clés, de l'URL publique, en-têtes posés
    sur l'objet, suppression) est identique. R2 est compatible S3, c'est
    précisément la raison pour laquelle il a été retenu.
    """
    from app.core import stockage_photos as module

    monkeypatch.setattr(module.settings, "photos_s3_endpoint", "https://s3.amazonaws.com")
    monkeypatch.setattr(module.settings, "photos_s3_bucket", BUCKET)
    monkeypatch.setattr(module.settings, "photos_s3_access_key", "cle")
    monkeypatch.setattr(module.settings, "photos_s3_secret_key", "secret")
    monkeypatch.setattr(module.settings, "photos_public_base_url", BASE_PUBLIQUE)

    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=BUCKET)
        yield module.StockageObjet()


def _objets(bucket: str = BUCKET) -> list[str]:
    reponse = boto3.client("s3", region_name="us-east-1").list_objects_v2(Bucket=bucket)
    return [o["Key"] for o in reponse.get("Contents", [])]


# --- Le mode par défaut -------------------------------------------------


def test_sans_configuration_la_photo_reste_en_base():
    """
    Le comportement d'avant P2.2, intact : c'est celui du pilote, et celui que
    toute la suite de tests exerce.
    """
    depot = StockageEnBase().deposer("menu-items/1", JPEG, "image/jpeg", "/api/v1/menu-items/1/image?v=abc")

    assert depot.url == "/api/v1/menu-items/1/image?v=abc"
    assert depot.octets == JPEG
    assert depot.type_mime == "image/jpeg"
    assert StockageEnBase().hors_base is False


# --- Le mode objet ------------------------------------------------------


def test_la_photo_part_sur_le_stockage_et_quitte_la_base(stockage_objet):
    """
    **Le test qui compte.** `octets=None` est ce qui vide la colonne
    `LargeBinary` : sans ça on aurait deux copies de chaque photo, la base
    grossirait exactement comme avant, et le chantier n'aurait rien réglé.
    """
    depot = stockage_objet.deposer("menu-items/42", JPEG, "image/jpeg", "/api/v1/menu-items/42/image?v=abc")

    assert depot.octets is None
    assert depot.type_mime is None
    assert len(_objets()) == 1
    assert _objets()[0].startswith("menu-items/42/")


def test_lurl_rendue_est_absolue_donc_le_backend_nest_plus_appele(stockage_objet):
    """
    Une URL absolue, et `mediaUrl()` côté frontend l'utilise telle quelle : le
    client va droit au CDN. Une URL relative aurait laissé passer chaque
    premier chargement par le backend — le défaut qu'on corrige.
    """
    depot = stockage_objet.deposer("menu-items/42", JPEG, "image/jpeg", "/api/v1/menu-items/42/image?v=abc")

    assert depot.url.startswith(f"{BASE_PUBLIQUE}/")
    assert not depot.url.startswith("/")


def test_lobjet_porte_son_type_et_son_cache(stockage_objet):
    """
    Le CDN sert l'octet brut : si le type et le cache ne sont pas posés sur
    l'objet, le navigateur télécharge la photo au lieu de l'afficher, et la
    redemande à chaque vue.
    """
    stockage_objet.deposer("menu-items/42", JPEG, "image/webp", "/x")
    cle = _objets()[0]

    objet = boto3.client("s3", region_name="us-east-1").head_object(Bucket=BUCKET, Key=cle)
    assert objet["ContentType"] == "image/webp"
    assert objet["CacheControl"] == CACHE_PHOTOS
    assert cle.endswith(".webp")


def test_la_meme_photo_redeposee_ne_cree_pas_un_second_objet(stockage_objet):
    """Clé adressée par contenu : redéposer à l'identique est sans effet."""
    stockage_objet.deposer("menu-items/42", JPEG, "image/jpeg", "/x")
    stockage_objet.deposer("menu-items/42", JPEG, "image/jpeg", "/x")

    assert len(_objets()) == 1


def test_deux_plats_avec_la_meme_photo_ont_deux_objets_distincts(stockage_objet):
    """
    Le préfixe par propriétaire n'est pas décoratif : sans lui, deux plats
    portant la même photo partageraient un objet, et retirer la photo de l'un
    ferait disparaître celle de l'autre.
    """
    a = stockage_objet.deposer("menu-items/1", JPEG, "image/jpeg", "/x")
    b = stockage_objet.deposer("menu-items/2", JPEG, "image/jpeg", "/x")

    assert a.url != b.url
    assert len(_objets()) == 2

    stockage_objet.retirer(a.url)
    assert len(_objets()) == 1


def test_retirer_supprime_lobjet(stockage_objet):
    """Une photo retirée de la carte ne doit pas rester payée à vie."""
    depot = stockage_objet.deposer("menu-items/42", JPEG, "image/jpeg", "/x")
    assert len(_objets()) == 1

    stockage_objet.retirer(depot.url)

    assert _objets() == []


def test_retirer_ignore_ce_qui_ne_vient_pas_du_stockage(stockage_objet):
    """
    Une photo encore en base a une URL relative. La confondre avec une clé
    d'objet ferait au mieux un appel inutile, au pire une suppression à
    l'aveugle.
    """
    stockage_objet.deposer("menu-items/42", JPEG, "image/jpeg", "/x")

    stockage_objet.retirer("/api/v1/menu-items/42/image?v=abc")
    stockage_objet.retirer(None)
    stockage_objet.retirer("https://ailleurs.test/photo.jpg")

    assert len(_objets()) == 1


def test_un_retrait_qui_echoue_nempeche_pas_le_manager_de_retirer_sa_photo(stockage_objet, monkeypatch):
    """
    Best-effort assumé : un objet qui survit coûte quelques centimes, une
    exception ici empêcherait de retirer une photo ratée de la carte en plein
    service.
    """
    depot = stockage_objet.deposer("menu-items/42", JPEG, "image/jpeg", "/x")

    def _echoue(**_kwargs):
        raise RuntimeError("stockage injoignable")

    monkeypatch.setattr(stockage_objet._client, "delete_object", _echoue)
    stockage_objet.retirer(depot.url)  # ne lève pas


# --- Le garde-fou de configuration --------------------------------------


def test_une_configuration_a_moitie_posee_refuse_de_demarrer():
    """
    Une variable oubliée enverrait les photos vers un bucket inaccessible :
    carte sans photos chez le client, et aucune erreur nulle part. Mieux vaut
    un conteneur qui refuse de démarrer, pendant qu'on regarde encore les logs
    de déploiement.
    """
    with pytest.raises(ValueError, match="incomplète"):
        Settings(
            photos_s3_endpoint="https://s3.test",
            photos_s3_bucket=BUCKET,
            photos_s3_access_key="cle",
            photos_s3_secret_key="secret",
            # PHOTOS_PUBLIC_BASE_URL oubliée
        )


def test_les_cinq_variables_vides_sont_le_cas_normal():
    reglages = Settings()
    assert reglages.stockage_objet_configure is False


# --- Les routes, bout en bout -------------------------------------------


@pytest.fixture()
def routes_sur_stockage_objet(stockage_objet, monkeypatch):
    """
    Branche les routes sur le stockage objet. Les routeurs importent le
    singleton par son nom (`from ... import stockage_photos`), donc c'est le
    nom DANS CHAQUE MODULE qu'il faut remplacer — patcher le module d'origine
    ne changerait rien, et le test passerait pour de mauvaises raisons.
    """
    from app.modules.menu import router as menu_router
    from app.modules.tenants import router as tenants_router

    monkeypatch.setattr(menu_router, "stockage_photos", stockage_objet)
    monkeypatch.setattr(tenants_router, "stockage_photos", stockage_objet)
    return stockage_objet


def _plat(client, headers, restaurant_id: int) -> dict:
    return client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant_id, "name": "Couscous", "price": 20},
        headers=headers,
    ).json()


def test_une_photo_deposee_ne_laisse_plus_doctets_en_base(client, db_session, routes_sur_stockage_objet):
    """
    **Le test qui compte pour le produit.** Si la colonne gardait les octets,
    la base grossirait exactement comme avant et le chantier n'aurait servi à
    rien — on aurait juste payé un bucket en plus.
    """
    from app.modules.menu.models import MenuItem

    restaurant = create_restaurant(name="Photos", slug="photos-plat")
    headers = auth_headers(create_staff(restaurant.id))
    plat = _plat(client, headers, restaurant.id)

    reponse = client.put(
        f"/api/v1/menu-items/{plat['id']}/image",
        files={"file": ("plat.jpg", JPEG, "image/jpeg")},
        headers=headers,
    )
    assert reponse.status_code == 200, reponse.text

    db_session.expire_all()
    en_base = db_session.get(MenuItem, plat["id"])
    assert en_base.image_data is None, "les octets sont restés en base"
    assert en_base.image_url.startswith(f"{BASE_PUBLIQUE}/")
    assert len(_objets()) == 1


def test_remplacer_une_photo_ne_laisse_pas_dorphelin(client, db_session, routes_sur_stockage_objet):
    """Sinon chaque correction de carte laisse un objet payé à vie."""
    restaurant = create_restaurant(name="Photos", slug="photos-remplace")
    headers = auth_headers(create_staff(restaurant.id))
    plat = _plat(client, headers, restaurant.id)

    client.put(f"/api/v1/menu-items/{plat['id']}/image",
               files={"file": ("a.jpg", JPEG, "image/jpeg")}, headers=headers)
    client.put(f"/api/v1/menu-items/{plat['id']}/image",
               files={"file": ("b.jpg", JPEG + b"autre", "image/jpeg")}, headers=headers)

    assert len(_objets()) == 1


def test_retirer_une_photo_supprime_lobjet(client, db_session, routes_sur_stockage_objet):
    restaurant = create_restaurant(name="Photos", slug="photos-retrait")
    headers = auth_headers(create_staff(restaurant.id))
    plat = _plat(client, headers, restaurant.id)

    client.put(f"/api/v1/menu-items/{plat['id']}/image",
               files={"file": ("a.jpg", JPEG, "image/jpeg")}, headers=headers)
    client.delete(f"/api/v1/menu-items/{plat['id']}/image", headers=headers)

    assert _objets() == []


def test_la_banniere_de_couverture_part_aussi_hors_base(client, db_session, routes_sur_stockage_objet):
    """
    La bannière n'est pas dans la liste de fichiers de la roadmap, mais c'est
    **l'image la plus lourde et la plus chargée** du parcours client : elle
    s'ouvre sur le téléphone de chaque table. La laisser en base aurait laissé
    en place le plus gros contributeur au problème qu'on corrige.
    """
    from app.modules.tenants.models import Restaurant

    restaurant = create_restaurant(name="Photos", slug="photos-couverture")
    headers = auth_headers(create_staff(restaurant.id))

    reponse = client.put(
        f"/api/v1/restaurants/{restaurant.id}/cover-photo",
        files={"file": ("cover.jpg", JPEG, "image/jpeg")},
        headers=headers,
    )
    assert reponse.status_code == 200, reponse.text

    db_session.expire_all()
    en_base = db_session.get(Restaurant, restaurant.id)
    assert en_base.cover_photo_data is None
    assert en_base.cover_photo_url.startswith(f"{BASE_PUBLIQUE}/")


def test_le_logo_part_aussi_hors_base(client, db_session, routes_sur_stockage_objet):
    from app.modules.tenants.models import Restaurant

    restaurant = create_restaurant(name="Photos", slug="photos-logo")
    headers = auth_headers(create_staff(restaurant.id))

    client.put(f"/api/v1/restaurants/{restaurant.id}/logo",
               files={"file": ("logo.png", JPEG, "image/png")}, headers=headers)

    db_session.expire_all()
    en_base = db_session.get(Restaurant, restaurant.id)
    assert en_base.logo_data is None
    assert en_base.logo_url.startswith(f"{BASE_PUBLIQUE}/")


def test_sans_stockage_objet_les_routes_gardent_la_photo_en_base(client, db_session):
    """
    Le chemin par défaut, celui du pilote : rien ne change. Sans ce test, une
    régression sur le mode par défaut passerait inaperçue — tous les autres
    tests de ce fichier configurent le stockage objet.
    """
    from app.modules.menu.models import MenuItem

    restaurant = create_restaurant(name="Photos", slug="photos-defaut")
    headers = auth_headers(create_staff(restaurant.id))
    plat = _plat(client, headers, restaurant.id)

    client.put(f"/api/v1/menu-items/{plat['id']}/image",
               files={"file": ("a.jpg", JPEG, "image/jpeg")}, headers=headers)

    db_session.expire_all()
    en_base = db_session.get(MenuItem, plat["id"])
    assert en_base.image_data == JPEG
    assert en_base.image_url.startswith("/api/v1/menu-items/")

    # Et la photo se sert toujours par le backend.
    photo = client.get(en_base.image_url)
    assert photo.status_code == 200
    assert photo.content == JPEG


# --- Le script de migration ---------------------------------------------


def test_le_script_deplace_les_photos_deja_en_base(client, db_session, stockage_objet, monkeypatch):
    """
    Sans ce script, basculer la configuration ne déplacerait que les
    **nouvelles** photos : une carte déjà remplie resterait servie par le
    backend indéfiniment, et l'intérêt du chantier ne se réaliserait qu'au fil
    des remplacements — c'est-à-dire jamais.
    """
    import scripts.migrer_photos as script
    from app.modules.menu.models import MenuItem
    from tests.conftest import _TestingSessionLocal

    restaurant = create_restaurant(name="Photos", slug="photos-migration")
    headers = auth_headers(create_staff(restaurant.id))
    plat = _plat(client, headers, restaurant.id)
    # Photo déposée AVANT la bascule : elle est donc en base.
    client.put(f"/api/v1/menu-items/{plat['id']}/image",
               files={"file": ("a.jpg", JPEG, "image/jpeg")}, headers=headers)
    client.put(f"/api/v1/restaurants/{restaurant.id}/cover-photo",
               files={"file": ("c.jpg", JPEG + b"cover", "image/jpeg")}, headers=headers)

    monkeypatch.setattr(script, "SessionLocal", _TestingSessionLocal)
    monkeypatch.setattr(script, "stockage_photos", stockage_objet)

    # Simulation : elle compte, elle n'écrit rien.
    comptes = script.migrer(appliquer=False)
    assert comptes == {"plats": 1, "couvertures": 1, "logos": 0}
    assert _objets() == []

    comptes = script.migrer(appliquer=True)
    assert comptes == {"plats": 1, "couvertures": 1, "logos": 0}
    assert len(_objets()) == 2

    db_session.expire_all()
    en_base = db_session.get(MenuItem, plat["id"])
    assert en_base.image_data is None
    assert en_base.image_url.startswith(f"{BASE_PUBLIQUE}/")


def test_le_script_est_idempotent(client, db_session, stockage_objet, monkeypatch):
    """Relancer après une coupure reprend là où ça s'était arrêté, sans
    redéposer ni compter deux fois."""
    import scripts.migrer_photos as script
    from tests.conftest import _TestingSessionLocal

    restaurant = create_restaurant(name="Photos", slug="photos-idempotent")
    headers = auth_headers(create_staff(restaurant.id))
    plat = _plat(client, headers, restaurant.id)
    client.put(f"/api/v1/menu-items/{plat['id']}/image",
               files={"file": ("a.jpg", JPEG, "image/jpeg")}, headers=headers)

    monkeypatch.setattr(script, "SessionLocal", _TestingSessionLocal)
    monkeypatch.setattr(script, "stockage_photos", stockage_objet)

    assert script.migrer(appliquer=True)["plats"] == 1
    assert script.migrer(appliquer=True)["plats"] == 0, "une photo déjà migrée a été redéposée"


def test_le_script_refuse_de_tourner_sans_stockage_configure():
    """
    Sans bascule, il n'aurait rien à faire — mais surtout, un opérateur qui le
    lance croit déplacer ses photos. Mieux vaut un refus net qu'un « 0 photo
    déplacée » qu'on lit comme « c'est déjà fait ».
    """
    import scripts.migrer_photos as script

    with pytest.raises(SystemExit, match="PHOTOS_S3"):
        script.migrer(appliquer=True)

