"""
Calcul des scores — V1 (MVP) : uniquement "alimentaire" et "indice_fiabilite",
conformément au Chapitre 8 (les scores "activité" et "évolution corporelle"
sont différés à la V2, faute de module de suivi corporel actif en V1).

Chaque score reste volontairement sectoriel (Chapitre 6.13) : pas de score de
santé global unique, pour éviter toute impression de mesure médicale.

Les seuils utilisés ci-dessous sont des repères nutritionnels généraux
(recommandations type OMS/ANSES déjà citées dans les règles R04-R08) — à
recalibrer si besoin après validation par un(e) diététicien(ne).
"""
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from .models import Repas, Score


def _borner(valeur, minimum=0, maximum=100):
    return max(minimum, min(maximum, valeur))


def _repas_periode(utilisateur, jours=7):
    date_debut = timezone.localdate() - timedelta(days=jours - 1)
    return Repas.objects.filter(utilisateur=utilisateur, date__gte=date_debut).prefetch_related(
        "aliments_consommes__aliment"
    )


# ---------------------------------------------------------------------------
# Score alimentaire
# ---------------------------------------------------------------------------
def calculer_score_alimentaire(utilisateur, jours=7):
    repas_periode = list(_repas_periode(utilisateur, jours))

    if not repas_periode:
        return None  # rien à calculer sans historique

    aliments_distincts = set()
    repas_avec_fruit_legume = 0
    fibres_total = sodium_total = sucres_total = graisses_sat_total = Decimal("0")

    for r in repas_periode:
        contient_fruit_legume = False
        for ra in r.aliments_consommes.all():
            a = ra.aliment
            aliments_distincts.add(a.id)
            if a.categorie and ("fruit" in a.categorie.lower() or "légume" in a.categorie.lower() or "legume" in a.categorie.lower()):
                contient_fruit_legume = True
            if a.fibres:
                fibres_total += (a.fibres * ra.quantite_g) / Decimal("100")
            if a.sodium_mg:
                sodium_total += (a.sodium_mg * ra.quantite_g) / Decimal("100")
            if a.sucres:
                sucres_total += (a.sucres * ra.quantite_g) / Decimal("100")
            if a.graisses_saturees:
                graisses_sat_total += (a.graisses_saturees * ra.quantite_g) / Decimal("100")
        if contient_fruit_legume:
            repas_avec_fruit_legume += 1

    # --- Sous-scores (0-100 chacun) ---
    sous_score_diversite = _borner(round(len(aliments_distincts) / 15 * 100))
    sous_score_fruits_legumes = _borner(round(repas_avec_fruit_legume / len(repas_periode) * 100))
    sous_score_fibres = _borner(round(float(fibres_total) / jours / 25 * 100))
    # Pour sodium/sucres/graisses saturées : moins on en consomme, mieux c'est (score inversé)
    sous_score_sodium = _borner(round(100 - (float(sodium_total) / jours / 2000 * 100)))
    sous_score_sucres = _borner(round(100 - (float(sucres_total) / jours / 50 * 100)))
    sous_score_graisses_sat = _borner(round(100 - (float(graisses_sat_total) / jours / 22 * 100)))

    ponderations = {
        "diversite": (sous_score_diversite, 0.20),
        "fruits_legumes": (sous_score_fruits_legumes, 0.20),
        "fibres": (sous_score_fibres, 0.15),
        "sodium": (sous_score_sodium, 0.15),
        "sucres": (sous_score_sucres, 0.15),
        "graisses_saturees": (sous_score_graisses_sat, 0.15),
    }
    valeur_finale = _borner(round(sum(v * p for v, p in ponderations.values())))

    detail = {cle: v for cle, (v, _) in ponderations.items()}
    detail["nb_aliments_distincts"] = len(aliments_distincts)
    detail["nb_repas_analyses"] = len(repas_periode)
    detail["periode_jours"] = jours

    score, _ = Score.objects.update_or_create(
        utilisateur=utilisateur,
        type_score=Score.TypeScore.ALIMENTAIRE,
        date_calcul=timezone.localdate(),
        defaults={"valeur": Decimal(str(valeur_finale)), "detail": detail},
    )
    return score


# ---------------------------------------------------------------------------
# Indice de fiabilité (IFA)
# ---------------------------------------------------------------------------
def calculer_indice_fiabilite(utilisateur, jours=7):
    repas_periode = list(_repas_periode(utilisateur, jours))

    if not repas_periode:
        return None

    # 1. Complétude : proportion de jours de la période où au moins un repas est enregistré
    jours_avec_repas = len({r.date for r in repas_periode})
    sous_score_completude = _borner(round(jours_avec_repas / jours * 100))

    # 2. Nombre de repas par jour (repère : 3 repas/jour)
    nb_repas_par_jour = len(repas_periode) / jours
    sous_score_frequence = _borner(round(nb_repas_par_jour / 3 * 100))

    # 3. Qualité des données alimentaires utilisées (niveau_confiance des aliments)
    total_lignes, lignes_fiables = 0, 0
    for r in repas_periode:
        for ra in r.aliments_consommes.all():
            total_lignes += 1
            if ra.aliment.niveau_confiance in ("moyen", "eleve"):
                lignes_fiables += 1
    sous_score_qualite = _borner(round((lignes_fiables / total_lignes * 100) if total_lignes else 0))

    ponderations = {
        "completude": (sous_score_completude, 0.4),
        "frequence_repas": (sous_score_frequence, 0.2),
        "qualite_donnees_aliments": (sous_score_qualite, 0.4),
    }
    valeur_finale = _borner(round(sum(v * p for v, p in ponderations.values())))

    detail = {cle: v for cle, (v, _) in ponderations.items()}
    detail["jours_avec_repas"] = jours_avec_repas
    detail["periode_jours"] = jours

    score, _ = Score.objects.update_or_create(
        utilisateur=utilisateur,
        type_score=Score.TypeScore.INDICE_FIABILITE,
        date_calcul=timezone.localdate(),
        defaults={"valeur": Decimal(str(valeur_finale)), "detail": detail},
    )
    return score


def mettre_a_jour_scores(utilisateur):
    """Point d'entrée : à appeler après l'enregistrement d'un repas (Chapitre 6.10)."""
    return {
        "alimentaire": calculer_score_alimentaire(utilisateur),
        "indice_fiabilite": calculer_indice_fiabilite(utilisateur),
    }
