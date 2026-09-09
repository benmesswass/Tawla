"""
Les chiffres qu'un restaurateur voit en ouvrant la démo.

Ce que ces tests protègent : un tableau de bord de démonstration à zéro ne
montre aucune des fonctionnalités du manager, et une page de preuve dont la
semaine « après » ressort moins bonne que la semaine « avant » retourne
l'argument de vente contre le produit. La garde inverse compte autant : ces
chiffres n'ont jamais été mesurés, ils ne doivent atteindre ni un vrai
restaurant, ni les agrégats de l'opérateur.
"""
from datetime import date, datetime, timedelta, timezone

import pytest

from app.core.dates import service_day_start
from app.core.markets import FRANCE, TUNISIA
from app.modules.demo import historique, service
from app.modules.orders.models import Order, OrderItem, OrderStatus, PaymentStatus
from app.modules.staff.models import StaffRole
from app.modules.tenants.models import Restaurant, SubscriptionTier

from tests.conftest import create_restaurant


def ouvrir_demo(client):
    reponse = client.post("/api/v1/demo/sessions")
    assert reponse.status_code == 201, reponse.text
    return reponse.json()


def entetes(demo):
    return {"Authorization": f"Bearer {demo['access_token']}"}


def test_le_tableau_de_bord_souvre_avec_des_chiffres(client):
    demo = ouvrir_demo(client)
    stats = client.get(
        f"/api/v1/stats/dashboard/{demo['restaurant_id']}", headers=entetes(demo)
    ).json()

    # Les deux chiffres de tête (RecetteDuJour.tsx) : sans eux, la première
    # chose que voit le restaurateur est un « 0,000 DT » en gros caractères.
    assert stats["revenue_today"] > 0
    assert stats["timing"]["avg_wait_confirmation_seconds"] is not None

    # Le reste des écrans chiffrés du manager (/dashboard/stats).
    assert stats["top_items"], "aucun plat vendu : le classement des ventes est vide"
    assert stats["orders_by_hour"], "aucune heure de pointe : l'histogramme est vide"
    assert stats["active_orders_count"] == 4
    assert len(stats["staff_active_load"]) == 2, "un seul serveur en charge : rien à comparer"
    assert all(etape is not None for etape in stats["timing"].values())


def test_les_deux_serveurs_se_comparent(client):
    demo = ouvrir_demo(client)
    stats = client.get(
        f"/api/v1/stats/dashboard/{demo['restaurant_id']}", headers=entetes(demo)
    ).json()

    prises = sorted(ligne["orders_taken"] for ligne in stats["staff_performance"])
    assert len(prises) == 2
    assert prises[0] > 0
    # Deux colonnes identiques ne diraient rien au manager qui vient
    # justement voir qui porte le service.
    assert prises[0] != prises[1]


def test_la_page_de_preuve_montre_une_progression(client):
    demo = ouvrir_demo(client)
    preuve = client.get(
        f"/api/v1/stats/preuve/{demo['restaurant_id']}", headers=entetes(demo)
    ).json()
    courante, precedente = preuve["current"], preuve["previous"]

    # Sans « avant », les trois chiffres de la page ne prouvent rien : la
    # période de comparaison doit être garnie, elle aussi.
    assert courante["orders_count"] > 0
    assert precedente["orders_count"] > 0

    # Les trois écarts que la page met en avant, dans le bon sens. Ils sont
    # structurels (voir historique.py) — un tirage aléatoire aurait pu les
    # inverser devant un restaurateur.
    assert courante["avg_order_to_kitchen_seconds"] < precedente["avg_order_to_kitchen_seconds"]
    assert courante["avg_basket_amount"] > precedente["avg_basket_amount"]
    taux = lambda p: p["cancelled_orders_count"] / p["orders_count"]  # noqa: E731
    assert taux(courante) < taux(precedente)

    # Le couple de chiffres qui produit l'argument « +X % de panier moyen ».
    assert courante["orders_with_suggestion_count"] > 0
    assert courante["avg_basket_with_suggestion"] > courante["avg_basket_without_suggestion"]


def test_le_rapport_dequipe_a_de_quoi_asseoir_une_prime(client, db_session):
    demo = ouvrir_demo(client)
    # Le rapport d'équipe est réservé à Business ; la démo s'ouvre en Pro, et
    # le visiteur peut simuler la montée de palier depuis l'écran d'offre.
    restaurant = db_session.get(Restaurant, demo["restaurant_id"])
    restaurant.subscription_tier = SubscriptionTier.BUSINESS
    db_session.commit()

    rapport = client.get(
        f"/api/v1/stats/equipe/{demo['restaurant_id']}", headers=entetes(demo)
    ).json()

    assert len(rapport["staff"]) == 2
    for ligne in rapport["staff"]:
        assert ligne["orders_taken"] > 0
        assert ligne["total_amount_handled"] > 0
        assert ligne["avg_seconds_to_claim"] is not None
    assert sum(ligne["total_tips_collected"] for ligne in rapport["staff"]) > 0


def test_les_suggestions_de_la_carte_existent_vraiment(client):
    """Le chiffre « panier moyen avec suggestion » doit renvoyer à une
    fonctionnalité que le restaurateur peut retrouver sur sa carte."""
    demo = ouvrir_demo(client)
    suggestions = client.get(
        f"/api/v1/menu-items/by-restaurant/{demo['restaurant_id']}/suggestions", headers=entetes(demo)
    )
    assert suggestions.status_code == 200, suggestions.text
    assert suggestions.json()


def test_jamais_dhistorique_sur_un_vrai_restaurant(db_session):
    """
    La garde qui compte le plus de ce module : ces commandes n'ont jamais eu
    lieu. Sur un vrai établissement elles seraient un chiffre inventé, et sur
    la page de preuve un mensonge signé (ROADMAP.md §23.2).
    """
    restaurant = create_restaurant(name="Vrai client")
    with pytest.raises(ValueError):
        historique.poser_historique(
            db_session,
            restaurant=db_session.get(Restaurant, restaurant.id),
            tables=[],
            serveurs=[],
            articles=[],
            market=TUNISIA,
        )
    assert db_session.query(Order).filter(Order.restaurant_id == restaurant.id).count() == 0


def test_la_purge_emporte_tout_lhistorique(client, db_session):
    demo = ouvrir_demo(client)
    rid = demo["restaurant_id"]
    assert db_session.query(Order).filter(Order.restaurant_id == rid).count() > 0

    restaurant = db_session.get(Restaurant, rid)
    restaurant.demo_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()

    assert service.purger_demos_expirees(db_session) == 1
    assert db_session.query(Order).filter(Order.restaurant_id == rid).count() == 0
    assert (
        db_session.query(OrderItem)
        .filter(OrderItem.order_id.in_(db_session.query(Order.id).filter(Order.restaurant_id == rid)))
        .count()
        == 0
    )


def test_les_commandes_passees_sont_coherentes(client, db_session):
    """
    Une démo dont les commandes se contredisent (payée mais annulée, servie
    avant d'être confirmée) casse les écrans qui les lisent, et se voit à
    l'œil nu sur l'écran serveur.
    """
    demo = ouvrir_demo(client)
    commandes = db_session.query(Order).filter(Order.restaurant_id == demo["restaurant_id"]).all()
    maintenant = datetime.now(timezone.utc)

    for commande in commandes:
        # Aucun horodatage dans le futur : une commande passée il y a cinq
        # minutes et déjà encaissée porterait un paiement qui n'a pas encore
        # eu lieu, compté dans « Ventes du jour ».
        for horodatage in (
            commande.created_at, commande.taken_at, commande.confirmed_at,
            commande.sent_to_kitchen_at, commande.served_at, commande.paid_at,
        ):
            if horodatage is not None:
                assert horodatage.replace(tzinfo=timezone.utc) <= maintenant
        if commande.status == OrderStatus.CANCELLED:
            assert commande.payment_status == PaymentStatus.UNPAID
            assert commande.sent_to_kitchen_at is None
        if commande.payment_status == PaymentStatus.PAID:
            assert commande.status == OrderStatus.SERVED
            assert commande.served_at <= commande.paid_at
        if commande.served_at:
            assert commande.confirmed_at <= commande.sent_to_kitchen_at <= commande.served_at


def test_une_demo_francaise_numerote_ses_notes(db_session):
    """
    France : la note est obligatoire au-dessus du seuil, et sa séquence est
    continue par restaurant (core/invoice_number.py). Une démo qui montre des
    commandes payées sans numéro montrerait un produit non conforme.
    """
    restaurant, _, _ = service.creer_demo(db_session, market=FRANCE)
    payees = (
        db_session.query(Order)
        .filter(Order.restaurant_id == restaurant.id, Order.payment_status == PaymentStatus.PAID)
        .all()
    )
    numeros = [c.invoice_number for c in payees]
    assert all(numeros)
    assert len(set(numeros)) == len(numeros)


def test_une_demo_tunisienne_ne_numerote_rien(db_session):
    restaurant, _, _ = service.creer_demo(db_session, market=TUNISIA)
    payees = (
        db_session.query(Order)
        .filter(Order.restaurant_id == restaurant.id, Order.payment_status == PaymentStatus.PAID)
        .all()
    )
    assert payees
    assert all(c.invoice_number is None for c in payees)


def test_le_jeton_serveur_reste_celui_du_premier_serveur(client, db_session):
    """L'équipe compte deux serveurs ; le lien « écran serveur » du bandeau de
    démo doit ouvrir un compte, pas un compte au hasard entre les deux."""
    demo = ouvrir_demo(client)
    moi = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {demo['waiter_access_token']}"}
    ).json()
    assert moi["role"] == StaffRole.WAITER.value
    assert moi["name"].startswith(("Sami", "Thomas"))


def test_une_demo_ouverte_avant_le_service_a_quand_meme_des_ventes_du_jour():
    """
    « Ventes du jour » est le premier chiffre que voit le restaurateur. Une
    démo ouverte à 6 h 30 — avant le service de midi — le trouverait à zéro si
    l'historique s'en tenait aux créneaux habituels : les commandes du jour se
    replient alors sur les heures déjà écoulées de la journée de service.
    """
    matin = datetime(2026, 9, 9, 6, 30, tzinfo=TUNISIA.timezone).astimezone(timezone.utc)
    horaires = historique._horaires_aujourdhui(date(2026, 9, 9), 18, TUNISIA, matin)

    assert len(horaires) >= historique.MINIMUM_AUJOURDHUI
    # Jamais dans le futur (une vente pas encore faite), jamais avant le début
    # de la journée de service (elle appartiendrait à la veille).
    assert all(heure <= matin for heure in horaires)
    assert all(heure >= service_day_start(matin, TUNISIA) for heure in horaires)
