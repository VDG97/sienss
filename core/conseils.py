"""
Moteur de conseils personnalisés (Chapitre 6 étendu — "Recommandations").

Principe : conseils généraux, non chiffrés, non normatifs — jamais de
calories/grammes cibles (risque de renforcer des comportements alimentaires
à risque). L'objectif est d'orienter vers de bonnes pratiques générales et
des associations d'aliments favorables, en tenant compte du profil déclaré
(objectif, pathologies, allergies), sans jamais remplacer un avis médical.

Ce module ne fait aucun calcul nutritionnel individualisé (pas de calories
cibles, pas de macros précises) — volontairement, pour rester dans le
registre de l'éducation nutritionnelle générale plutôt que de la
prescription, qui reste du ressort d'un professionnel de santé.
"""

HABITUDES_GENERALES = [
    "Buvez de l'eau régulièrement dans la journée, plutôt qu'en une seule fois — la soif est déjà un signe de déshydratation légère.",
    "Essayez de manger à des horaires réguliers : le corps régule mieux la faim et l'énergie avec un rythme stable.",
    "Privilégiez des repas variés plutôt que de répéter souvent les mêmes aliments — la diversité couvre mieux l'ensemble des besoins.",
    "Mangez lentement et sans distraction quand c'est possible : la sensation de satiété met environ 20 minutes à s'installer.",
    "Le mouvement quotidien (marche, tâches physiques, sport) complète une bonne alimentation — les deux se renforcent mutuellement.",
    "Un sommeil suffisant influence directement l'appétit et les choix alimentaires du lendemain.",
]

# Combinaisons alimentaires favorables, organisées par objectif nutritionnel.
# Formulées en principes généraux (associations de familles d'aliments),
# jamais en portions ou calories précises.
COMBINAISONS_PAR_OBJECTIF = {
    "perte_poids": [
        "Associez une source de protéines (poisson, légumineuses, œuf) à des légumes riches en fibres à chaque repas principal : cette combinaison prolonge la sensation de satiété.",
        "Préférez les féculents complets (riz complet, patate douce) aux versions très raffinées : ils ralentissent la digestion et évitent les fringales.",
        "Commencer un repas par une portion de légumes ou une soupe peut naturellement réduire la quantité consommée ensuite, sans effort de restriction.",
        "Limitez les boissons sucrées au profit de l'eau ou d'infusions non sucrées — elles n'apportent pas de satiété malgré leurs calories.",
    ],
    "prise_masse": [
        "Associez systématiquement une source de glucides (céréales, tubercules) à une source de protéines à chaque repas pour soutenir la récupération et la construction musculaire.",
        "Ajoutez des matières grasses de qualité (huile végétale, avocat, noix) pour augmenter la densité énergétique des repas sans les alourdir excessivement.",
        "Répartissez l'apport protéique sur plusieurs repas dans la journée plutôt que de le concentrer sur un seul.",
        "Une collation après une activité physique intense (fruit + source de protéines) favorise la récupération.",
    ],
    "maintien": [
        "Composez vos assiettes selon une répartition simple : environ la moitié de légumes, un quart de protéines, un quart de féculents — un repère visuel plutôt qu'une pesée.",
        "Alternez les sources de protéines dans la semaine (poisson, légumineuses, viande, œuf) pour varier les apports en micronutriments.",
        "Gardez une place occasionnelle pour les aliments plaisir — l'équilibre se construit sur la semaine, pas sur un seul repas.",
    ],
    "equilibre": [
        "Composez vos assiettes selon une répartition simple : environ la moitié de légumes, un quart de protéines, un quart de féculents — un repère visuel plutôt qu'une pesée.",
        "Associez les légumes riches en vitamine C (agrumes, tomate, poivron) aux sources de fer végétal (légumineuses) : cela améliore l'absorption du fer.",
        "Variez les couleurs dans l'assiette — c'est un indicateur simple de diversité en micronutriments.",
    ],
    "suivi_medical": [
        "Suivez en priorité les recommandations spécifiques données par votre professionnel de santé — les conseils généraux ci-dessous les complètent sans les remplacer.",
        "Tenez un journal alimentaire régulier (ce que permet SIENSS) : c'est un outil précieux à partager avec votre professionnel de santé lors du suivi.",
    ],
}

# Combinaisons à limiter/nuancer selon les pathologies déclarées — formulées
# en principes généraux, jamais en interdits stricts (voir Chapitre 6.8 :
# éviter tout message culpabilisant).
CONSEILS_PAR_PATHOLOGIE = {
    "diabete": [
        "Associez toujours une source de glucides à des fibres ou des protéines (ex : féculent + légumes, ou féculent + légumineuses) : cela ralentit l'élévation de la glycémie après le repas.",
        "Répartir les glucides sur plusieurs repas plutôt que de les concentrer aide généralement à mieux stabiliser la glycémie sur la journée.",
    ],
    "hypertension": [
        "Privilégiez les aliments riches en potassium (banane, patate douce, légumineuses, légumes verts) : le potassium contribue à équilibrer les effets du sodium.",
        "Les herbes, épices et le citron sont de bonnes alternatives pour relever le goût des plats sans ajouter de sel.",
    ],
    "insuffisance renale": [
        "Les besoins en potassium, phosphore et protéines varient beaucoup selon le stade et le suivi médical — suivez les repères donnés par votre néphrologue ou diététicien plutôt qu'une règle générale.",
    ],
}


def generer_conseils(utilisateur):
    """
    Retourne un dict avec 3 sections de conseils, adaptées au profil de
    l'utilisateur (objectif nutritionnel, pathologies déclarées).
    Ne fait aucune supposition sur des pathologies ou objectifs non déclarés.
    """
    profil = getattr(utilisateur, "profil_sante", None)
    objectif = profil.objectif_nutritionnel if profil else ""
    pathologies_declarees = {
        p.pathologie.strip().lower() for p in utilisateur.pathologies.all()
    }

    combinaisons = COMBINAISONS_PAR_OBJECTIF.get(objectif, COMBINAISONS_PAR_OBJECTIF["equilibre"])

    attention_particuliere = []
    for cle, conseils in CONSEILS_PAR_PATHOLOGIE.items():
        if any(cle in p for p in pathologies_declarees):
            attention_particuliere.extend(conseils)

    return {
        "habitudes_generales": HABITUDES_GENERALES,
        "combinaisons_alimentaires": combinaisons,
        "attention_particuliere": attention_particuliere,
        "objectif_libelle": dict(
            [("perte_poids", "Perte de poids"), ("prise_masse", "Prise de masse"),
             ("maintien", "Maintien"), ("equilibre", "Équilibre alimentaire"),
             ("suivi_medical", "Suivi médical")]
        ).get(objectif, "Non renseigné"),
    }
