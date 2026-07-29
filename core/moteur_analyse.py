"""
Moteur d'analyse nutritionnelle — version V1 (MVP), règles R01 à R18.

Suit le principe du Chapitre 6 : validation -> calcul -> comparaison au
profil -> exécution des règles (par niveau de priorité) -> génération
d'alertes.

IMPORTANT — limites assumées de cette version V1, à corriger avant mise
en production :
- La détection des interactions médicament/aliment (R13-R15) et des
  aliments "à risque" (réglisse, pamplemousse, produits laitiers, riches
  en vitamine K/potassium) se fait par mots-clés sur le nom/la catégorie
  de l'aliment et le nom du médicament déclaré. C'est fragile — il
  faudra, en V2, remplacer cela par des catégories structurées dans la
  base alimentaire et une liste de médicaments normalisée (DCI). R13 a
  été affinée suite à la revue nutritionnelle pour ne cibler que les
  molécules à interaction forte documentée avec le pamplemousse.
- R08 utilise désormais une estimation calorique Mifflin-St Jeor pondérée par le
  facteur d'activité physique du profil (corrigé suite à la revue nutritionnelle,
  qui avait identifié une sous-estimation systématique pour les profils actifs).
  Reste une estimation générale, pas un calcul personnalisé par un professionnel.
- Toutes ces règles doivent être validées par un(e) diététicien(ne)
  (voir Chapitre 6.15) avant que leur statut passe de "brouillon" à
  "validee" dans l'admin.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone

from .models import Alerte, Repas, RegleNutritionnelle


# ---------------------------------------------------------------------------
# Utilitaires communs
# ---------------------------------------------------------------------------
def _allergenes_utilisateur(utilisateur):
    return {a.allergene.strip().lower() for a in utilisateur.allergies.all()}


def _allergenes_aliment(aliment):
    if not aliment.allergenes:
        return set()
    return {a.strip().lower() for a in aliment.allergenes.split(",")}


def _pathologies_utilisateur(utilisateur):
    return {p.pathologie.strip().lower() for p in utilisateur.pathologies.all()}


def _medicaments_utilisateur(utilisateur):
    return [t.medicament.strip().lower() for t in utilisateur.traitements.all()]


def _repas_semaine(utilisateur, jours=7):
    date_debut = timezone.localdate() - timedelta(days=jours - 1)
    return Repas.objects.filter(utilisateur=utilisateur, date__gte=date_debut)


def _creer_alerte(utilisateur, identifiant_regle, repas=None):
    """Crée une alerte si la règle existe et n'a pas déjà d'équivalent actif."""
    try:
        regle = RegleNutritionnelle.objects.get(identifiant=identifiant_regle)
    except RegleNutritionnelle.DoesNotExist:
        return None

    deja_active = Alerte.objects.filter(
        utilisateur=utilisateur, regle=regle, repas=repas, statut=Alerte.Statut.ACTIVE
    ).exists()
    if deja_active:
        return None

    return Alerte.objects.create(utilisateur=utilisateur, regle=regle, repas=repas)


def _age_utilisateur(utilisateur):
    if not utilisateur.date_naissance:
        return None
    aujourdhui = timezone.localdate()
    dn = utilisateur.date_naissance
    return aujourdhui.year - dn.year - ((aujourdhui.month, aujourdhui.day) < (dn.month, dn.day))


FACTEURS_ACTIVITE = {
    "sedentaire": 1.2,
    "leger": 1.375,
    "modere": 1.55,
    "intense": 1.725,
}


def _besoins_caloriques_estimes(utilisateur):
    """
    Estimation Mifflin-St Jeor, désormais pondérée par le niveau d'activité
    physique déclaré au profil (facteur d'activité standard). Sans cela,
    l'estimation sous-estimait systématiquement les besoins des personnes
    actives (revue nutritionnelle, section R08).
    Si le niveau d'activité n'est pas renseigné, on applique par défaut le
    facteur "sédentaire" (le plus prudent : évite de déclencher R08 à tort
    chez quelqu'un dont on ne connaît pas l'activité réelle).
    """
    profil = getattr(utilisateur, "profil_sante", None)
    age = _age_utilisateur(utilisateur)
    if not profil or not profil.taille_cm or not profil.poids_actuel_kg or age is None:
        return None

    poids, taille = float(profil.poids_actuel_kg), float(profil.taille_cm)
    if utilisateur.sexe == "F":
        bmr = 10 * poids + 6.25 * taille - 5 * age - 161
    else:
        bmr = 10 * poids + 6.25 * taille - 5 * age + 5

    facteur = FACTEURS_ACTIVITE.get(profil.niveau_activite_physique, FACTEURS_ACTIVITE["sedentaire"])
    return bmr * facteur


# ---------------------------------------------------------------------------
# Règles déclenchées à l'échelle d'un repas (Niveau 1 principalement)
# ---------------------------------------------------------------------------
def _regle_R01_allergene(repas, allergenes_user):
    if not allergenes_user:
        return
    for ra in repas.aliments_consommes.select_related("aliment"):
        if _allergenes_aliment(ra.aliment) & allergenes_user:
            return _creer_alerte(repas.utilisateur, "R01", repas)


def _regle_R02_lactose(repas, pathologies_user):
    if "intolerance au lactose" not in pathologies_user:
        return
    for ra in repas.aliments_consommes.select_related("aliment"):
        if "lactose" in _allergenes_aliment(ra.aliment):
            return _creer_alerte(repas.utilisateur, "R02", repas)


def _regle_R03_gluten(repas, pathologies_user):
    if not ({"maladie coeliaque", "maladie cœliaque"} & pathologies_user):
        return
    for ra in repas.aliments_consommes.select_related("aliment"):
        if "gluten" in _allergenes_aliment(ra.aliment):
            return _creer_alerte(repas.utilisateur, "R03", repas)


def _regle_R12_reglisse(repas, pathologies_user):
    if "hypertension" not in pathologies_user:
        return
    for ra in repas.aliments_consommes.select_related("aliment"):
        if "réglisse" in ra.aliment.nom.lower() or "reglisse" in ra.aliment.nom.lower():
            return _creer_alerte(repas.utilisateur, "R12", repas)


# Revue nutritionnelle : toutes les statines ne sont pas concernées de la même
# façon par le pamplemousse. Simvastatine/atorvastatine/lovastatine sont
# significativement affectées (métabolisme CYP3A4) ; pravastatine et
# rosuvastatine le sont beaucoup moins et sont volontairement EXCLUES d'ici
# pour éviter les fausses alertes. Idem pour les antihypertenseurs : seules
# certaines dihydropyridines (félodipine, nifédipine) ont une interaction
# bien documentée — l'amlodipine a une interaction plus faible mais est
# conservée par prudence, le risque de faux positif restant limité.
MOTS_CLES_STATINES_ANTIHYPERTENSEURS = [
    "simvastatine", "atorvastatine", "lovastatine",  # statines à interaction forte
    "felodipine", "félodipine", "nifedipine", "nifédipine", "amlodipine",  # antihypertenseurs
]


def _regle_R13_pamplemousse(repas, medicaments_user):
    if not any(any(mc in med for mc in MOTS_CLES_STATINES_ANTIHYPERTENSEURS) for med in medicaments_user):
        return
    for ra in repas.aliments_consommes.select_related("aliment"):
        if "pamplemousse" in ra.aliment.nom.lower():
            return _creer_alerte(repas.utilisateur, "R13", repas)


MOTS_CLES_ANTICOAGULANTS = ["warfarine", "coumadine", "anticoagulant"]


def _regle_R14_vitamine_k(repas, medicaments_user):
    if not any(any(mc in med for mc in MOTS_CLES_ANTICOAGULANTS) for med in medicaments_user):
        return
    seuil_vitamine_k_mcg = Decimal("50")  # pour 100g — seuil indicatif à valider
    for ra in repas.aliments_consommes.select_related("aliment"):
        if ra.aliment.vitamine_k_mcg and ra.aliment.vitamine_k_mcg > seuil_vitamine_k_mcg:
            return _creer_alerte(repas.utilisateur, "R14", repas)


MOTS_CLES_ANTIBIOTIQUES_SENSIBLES = ["tetracycline", "tétracycline", "quinolone", "ciprofloxacine"]


def _regle_R15_laitages_antibiotiques(repas, medicaments_user):
    if not any(any(mc in med for mc in MOTS_CLES_ANTIBIOTIQUES_SENSIBLES) for med in medicaments_user):
        return
    for ra in repas.aliments_consommes.select_related("aliment"):
        if "lactose" in _allergenes_aliment(ra.aliment) or "produit laitier" in ra.aliment.categorie.lower():
            return _creer_alerte(repas.utilisateur, "R15", repas)


def _regle_R16_potassium_renale(repas, pathologies_user):
    if "insuffisance renale" not in pathologies_user and "insuffisance rénale" not in pathologies_user:
        return
    seuil_potassium_mg = Decimal("300")  # pour 100g — seuil indicatif, à valider avec un néphrologue
    for ra in repas.aliments_consommes.select_related("aliment"):
        if ra.aliment.potassium_mg and ra.aliment.potassium_mg > seuil_potassium_mg:
            return _creer_alerte(repas.utilisateur, "R16", repas)


def _regle_R09_ig_diabete(repas, pathologies_user):
    if "diabete" not in pathologies_user and "diabète" not in pathologies_user:
        return
    seuil_ig = 70
    for ra in repas.aliments_consommes.select_related("aliment"):
        aliment = ra.aliment
        if aliment.index_glycemique and aliment.index_glycemique >= seuil_ig:
            frequence = _repas_semaine(repas.utilisateur).filter(
                aliments_consommes__aliment=aliment
            ).distinct().count()
            if frequence >= 4:
                return _creer_alerte(repas.utilisateur, "R09", repas)


def _regle_R10_repartition_glucides(repas, pathologies_user):
    if "diabete" not in pathologies_user and "diabète" not in pathologies_user:
        return

    def glucides_repas(r):
        total = Decimal("0")
        for ra in r.aliments_consommes.select_related("aliment"):
            if ra.aliment.glucides:
                total += (ra.aliment.glucides * ra.quantite_g) / Decimal("100")
        return total

    glucides_jour = sum(
        (glucides_repas(r) for r in Repas.objects.filter(utilisateur=repas.utilisateur, date=repas.date)),
        Decimal("0"),
    )
    if glucides_jour == 0:
        return
    if glucides_repas(repas) / glucides_jour > Decimal("0.6"):
        return _creer_alerte(repas.utilisateur, "R10", repas)


def _regle_R17_repetition_aliment(repas, jours=5, seuil_part=Decimal("0.5")):
    date_debut = timezone.localdate() - timedelta(days=jours - 1)
    repas_periode = Repas.objects.filter(utilisateur=repas.utilisateur, date__gte=date_debut)

    calories_par_aliment = {}
    calories_totales = Decimal("0")
    for r in repas_periode:
        for ra in r.aliments_consommes.select_related("aliment"):
            if not ra.aliment.calories:
                continue
            cal = (ra.aliment.calories * ra.quantite_g) / Decimal("100")
            calories_totales += cal
            calories_par_aliment[ra.aliment_id] = calories_par_aliment.get(ra.aliment_id, Decimal("0")) + cal

    if calories_totales == 0:
        return
    if any(cal / calories_totales > seuil_part for cal in calories_par_aliment.values()):
        return _creer_alerte(repas.utilisateur, "R17")


# ---------------------------------------------------------------------------
# Règles déclenchées à l'échelle de la semaine (indépendantes d'un repas précis)
# ---------------------------------------------------------------------------
def _regle_R04_sodium(utilisateur):
    seuil_mg_semaine = Decimal("14000")  # ~2 g/jour * 7
    total = Decimal("0")
    for r in _repas_semaine(utilisateur):
        for ra in r.aliments_consommes.select_related("aliment"):
            if ra.aliment.sodium_mg:
                total += (ra.aliment.sodium_mg * ra.quantite_g) / Decimal("100")
    if total > seuil_mg_semaine:
        return _creer_alerte(utilisateur, "R04")


def _regle_R05_sucres(utilisateur):
    seuil_g_semaine = Decimal("350")  # ~10% de 2000 kcal/jour * 7, seuil indicatif
    total = Decimal("0")
    for r in _repas_semaine(utilisateur):
        for ra in r.aliments_consommes.select_related("aliment"):
            if ra.aliment.sucres:
                total += (ra.aliment.sucres * ra.quantite_g) / Decimal("100")
    if total > seuil_g_semaine:
        return _creer_alerte(utilisateur, "R05")


def _regle_R06_graisses_saturees(utilisateur):
    seuil_g_semaine = Decimal("154")  # ~10% de 2000 kcal/jour * 7, seuil indicatif
    total = Decimal("0")
    for r in _repas_semaine(utilisateur):
        for ra in r.aliments_consommes.select_related("aliment"):
            if ra.aliment.graisses_saturees:
                total += (ra.aliment.graisses_saturees * ra.quantite_g) / Decimal("100")
    if total > seuil_g_semaine:
        return _creer_alerte(utilisateur, "R06")


def _regle_R07_fibres(utilisateur):
    seuil_g_jour_moyenne = Decimal("25")
    total = Decimal("0")
    nb_jours = 7
    for r in _repas_semaine(utilisateur, jours=nb_jours):
        for ra in r.aliments_consommes.select_related("aliment"):
            if ra.aliment.fibres:
                total += (ra.aliment.fibres * ra.quantite_g) / Decimal("100")
    if (total / nb_jours) < seuil_g_jour_moyenne:
        return _creer_alerte(utilisateur, "R07")


def _regle_R08_apport_insuffisant(utilisateur):
    besoins = _besoins_caloriques_estimes(utilisateur)
    if not besoins:
        return

    jours_consecutifs_requis = 3
    aujourdhui = timezone.localdate()
    for i in range(jours_consecutifs_requis):
        jour = aujourdhui - timedelta(days=i)
        repas_jour = Repas.objects.filter(utilisateur=utilisateur, date=jour)
        calories_jour = Decimal("0")
        for r in repas_jour:
            for ra in r.aliments_consommes.select_related("aliment"):
                if ra.aliment.calories:
                    calories_jour += (ra.aliment.calories * ra.quantite_g) / Decimal("100")
        if not repas_jour.exists() or calories_jour >= Decimal(str(besoins)) * Decimal("0.7"):
            return  # une seule journée hors seuil suffit à ne pas déclencher l'alerte
    return _creer_alerte(utilisateur, "R08")


def _regle_R11_sodium_hypertension(utilisateur, pathologies_user):
    if "hypertension" not in pathologies_user:
        return
    seuil_mg_jour = Decimal("1500")
    aujourdhui = timezone.localdate()
    total = Decimal("0")
    for r in Repas.objects.filter(utilisateur=utilisateur, date=aujourdhui):
        for ra in r.aliments_consommes.select_related("aliment"):
            if ra.aliment.sodium_mg:
                total += (ra.aliment.sodium_mg * ra.quantite_g) / Decimal("100")
    if total > seuil_mg_jour:
        return _creer_alerte(utilisateur, "R11")


def _regle_R18_sauts_repas(utilisateur):
    date_debut = timezone.localdate() - timedelta(days=6)
    jours_avec_repas = (
        Repas.objects.filter(utilisateur=utilisateur, date__gte=date_debut)
        .values_list("date", flat=True)
        .distinct()
        .count()
    )
    if jours_avec_repas <= 3:  # repas enregistrés au plus 3 jours sur 7
        return _creer_alerte(utilisateur, "R18")


# ---------------------------------------------------------------------------
# Point d'entrée principal
# ---------------------------------------------------------------------------
def analyser_repas(repas: Repas):
    """
    À appeler juste après l'enregistrement d'un repas.
    Exécute les règles par ordre de priorité (Niveau 1 -> 4) et retourne
    la liste des alertes nouvellement créées.
    """
    utilisateur = repas.utilisateur
    allergenes_user = _allergenes_utilisateur(utilisateur)
    pathologies_user = _pathologies_utilisateur(utilisateur)
    medicaments_user = _medicaments_utilisateur(utilisateur)

    verifications = [
        # --- Niveau 1 : sécurité immédiate ---
        lambda: _regle_R01_allergene(repas, allergenes_user),
        lambda: _regle_R02_lactose(repas, pathologies_user),
        lambda: _regle_R03_gluten(repas, pathologies_user),
        lambda: _regle_R13_pamplemousse(repas, medicaments_user),
        lambda: _regle_R14_vitamine_k(repas, medicaments_user),
        lambda: _regle_R15_laitages_antibiotiques(repas, medicaments_user),
        lambda: _regle_R16_potassium_renale(repas, pathologies_user),
        # --- Niveau 2 : pathologies chroniques ---
        lambda: _regle_R09_ig_diabete(repas, pathologies_user),
        lambda: _regle_R10_repartition_glucides(repas, pathologies_user),
        lambda: _regle_R11_sodium_hypertension(utilisateur, pathologies_user),
        lambda: _regle_R12_reglisse(repas, pathologies_user),
        # --- Niveau 3 : analyse nutritionnelle (hebdomadaire) ---
        lambda: _regle_R04_sodium(utilisateur),
        lambda: _regle_R05_sucres(utilisateur),
        lambda: _regle_R06_graisses_saturees(utilisateur),
        lambda: _regle_R07_fibres(utilisateur),
        lambda: _regle_R08_apport_insuffisant(utilisateur),
        # --- Niveau 4 : habitudes alimentaires ---
        lambda: _regle_R17_repetition_aliment(repas),
        lambda: _regle_R18_sauts_repas(utilisateur),
    ]

    alertes_creees = []
    for verification in verifications:
        alerte = verification()
        if alerte:
            alertes_creees.append(alerte)

    return alertes_creees
