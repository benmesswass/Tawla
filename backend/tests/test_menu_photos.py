"""
Photos de la carte, déposées par le manager.

Elles vivent en base et non sur le disque du conteneur : chez Railway comme
chez Render le système de fichiers est éphémère, et la carte perdrait toutes
ses photos au premier redéploiement — un soir, en plein service.
"""
from app.modules.staff.models import StaffRole
from tests.conftest import auth_headers, create_restaurant, create_staff

# Le plus petit PNG valide (1×1 transparent), suffisant pour tout ce qui est
# vérifié ici : c'est le contrat de la route qu'on teste, pas un décodeur.
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000a49444154789c6360000002000100ffff03000006000557bfabd400"
    "00000049454e44ae426082"
)


def _setup(client, slug="dar-chaabane-photos"):
    restaurant = create_restaurant(name="Dar Chaabane", slug=slug)
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    headers = auth_headers(manager)
    item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Couscous", "price": 22.0},
        headers=headers,
    ).json()
    return restaurant, item, headers


def _depose(client, item_id, headers, contenu=PNG, mime="image/png", nom="plat.png"):
    return client.put(
        f"/api/v1/menu-items/{item_id}/image",
        files={"file": (nom, contenu, mime)},
        headers=headers,
    )


def test_le_manager_depose_une_photo_et_le_client_la_voit(client):
    _restaurant, item, headers = _setup(client)

    depot = _depose(client, item["id"], headers)
    assert depot.status_code == 200
    image_url = depot.json()["image_url"]
    assert image_url.startswith(f"/api/v1/menu-items/{item['id']}/image")

    # Servie sans authentification : c'est le client attablé qui la regarde.
    photo = client.get(f"/api/v1/menu-items/{item['id']}/image")
    assert photo.status_code == 200
    assert photo.content == PNG
    assert photo.headers["content-type"] == "image/png"


def test_une_photo_remplacee_change_dadresse(client):
    """
    Sans empreinte dans l'URL, le téléphone du client garderait l'ancienne
    photo en cache et le manager croirait son dépôt sans effet.
    """
    _restaurant, item, headers = _setup(client, slug="photos-cache")
    premiere = _depose(client, item["id"], headers).json()["image_url"]

    autre = PNG + b"\x00"
    seconde = _depose(client, item["id"], headers, contenu=autre).json()["image_url"]

    assert premiere != seconde


def test_un_serveur_ne_peut_pas_deposer_de_photo(client):
    """La photo d'un plat est un acte de gestion, comme son prix."""
    restaurant, item, _headers = _setup(client, slug="photos-role")
    serveur = auth_headers(create_staff(restaurant.id, StaffRole.WAITER))

    assert _depose(client, item["id"], serveur).status_code == 403


def test_un_manager_dun_autre_restaurant_est_refuse(client):
    _restaurant, item, _headers = _setup(client, slug="photos-isolation")
    voisin = create_restaurant(name="Le Voisin", slug="le-voisin-photos")
    manager_voisin = auth_headers(create_staff(voisin.id, StaffRole.MANAGER))

    assert _depose(client, item["id"], manager_voisin).status_code in (403, 404)


def test_un_fichier_qui_nest_pas_une_photo_est_refuse(client):
    """Un SVG est un document exécutable : servi depuis notre domaine, il
    ouvrirait une injection de script chez le client."""
    _restaurant, item, headers = _setup(client, slug="photos-format")

    refus = _depose(
        client, item["id"], headers, contenu=b"<svg onload=alert(1)>", mime="image/svg+xml", nom="x.svg"
    )

    assert refus.status_code == 415
    assert refus.json()["detail"]["code"] == "UNSUPPORTED_IMAGE"


def test_une_photo_trop_lourde_est_refusee(client):
    """Le navigateur redimensionne avant d'envoyer ; ce garde-fou existe pour
    le cas où l'appel ne vient pas de lui."""
    _restaurant, item, headers = _setup(client, slug="photos-taille")

    refus = _depose(client, item["id"], headers, contenu=b"x" * (3 * 1024 * 1024 + 1), mime="image/jpeg")

    assert refus.status_code == 413
    assert refus.json()["detail"]["code"] == "IMAGE_TOO_LARGE"


def test_le_manager_peut_retirer_une_photo_ratee(client):
    _restaurant, item, headers = _setup(client, slug="photos-retrait")
    _depose(client, item["id"], headers)

    retrait = client.delete(f"/api/v1/menu-items/{item['id']}/image", headers=headers)

    assert retrait.status_code == 200
    assert retrait.json()["image_url"] is None
    assert client.get(f"/api/v1/menu-items/{item['id']}/image").status_code == 404


def test_un_plat_sans_photo_repond_404(client):
    _restaurant, item, _headers = _setup(client, slug="photos-absente")

    assert client.get(f"/api/v1/menu-items/{item['id']}/image").status_code == 404
