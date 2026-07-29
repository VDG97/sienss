"""
Commande : python manage.py charger_regles

Pré-charge les 18 règles nutritionnelles définies dans le document
"Règles nutritionnelles — Moteur d'analyse (v1 prototype)".

Elles sont créées avec le statut "brouillon" : conformément au Chapitre
6.15 du cahier des charges, elles doivent être validées par un(e)
diététicien(ne) ou le comité scientifique avant d'être activées en
production (passer statut='validee' + date_validation).
"""
from django.core.management.base import BaseCommand

from core.models import RegleNutritionnelle as R


REGLES = [
    dict(identifiant="R01", nom="Allergène déclaré détecté", niveau_alerte="risque_eleve",
         description="Allergène présent dans l'aliment saisi = allergène déclaré dans le profil utilisateur.",
         message="Cet aliment contient un allergène que vous avez déclaré dans votre profil. Évitez sa consommation.",
         reference_scientifique="Déclaration directe de l'utilisateur (détection factuelle)."),
    dict(identifiant="R02", nom="Intolérance au lactose", niveau_alerte="vigilance",
         description="Profil = intolérance au lactose ET aliment contient du lactose.",
         message="Cet aliment contient du lactose. Des alternatives sans lactose existent si vous ressentez une gêne digestive.",
         reference_scientifique="Consensus médical standard sur l'intolérance au lactose."),
    dict(identifiant="R03", nom="Intolérance au gluten / maladie cœliaque", niveau_alerte="risque_eleve",
         description="Profil = intolérance/maladie cœliaque ET aliment contient du gluten.",
         message="Cet aliment contient du gluten, à éviter selon votre profil déclaré.",
         reference_scientifique="Recommandations standards sur la maladie cœliaque."),
    dict(identifiant="R04", nom="Excès de sodium", niveau_alerte="vigilance",
         description="Moyenne du sodium sur 7 jours glissants > 2 g/jour.",
         message="Votre apport en sel est élevé cette semaine. Un excès prolongé augmente le risque de tension artérielle élevée.",
         reference_scientifique="Recommandation OMS (< 2 g de sodium/jour, soit ~5 g de sel)."),
    dict(identifiant="R05", nom="Excès de sucres libres", niveau_alerte="vigilance",
         description="Sucres libres cumulés > 10% de l'apport énergétique total sur 7 jours.",
         message="Votre consommation de sucre dépasse le seuil recommandé cette semaine.",
         reference_scientifique="Recommandation OMS sur les sucres libres."),
    dict(identifiant="R06", nom="Excès de graisses saturées", niveau_alerte="vigilance",
         description="Graisses saturées cumulées > 10% de l'apport énergétique total sur 7 jours.",
         message="Votre apport en graisses saturées est élevé. Cela peut, à long terme, affecter la santé cardiovasculaire.",
         reference_scientifique="Recommandations nutritionnelles standards (type ANSES/USDA)."),
    dict(identifiant="R07", nom="Apport insuffisant en fibres", niveau_alerte="info",
         description="Fibres cumulées < 25 g/jour en moyenne sur 7 jours.",
         message="Votre apport en fibres est en dessous du seuil recommandé. Pensez aux légumes, légumineuses et céréales complètes.",
         reference_scientifique="Recommandation standard (25 g/jour minimum, adulte)."),
    dict(identifiant="R08", nom="Apport calorique très insuffisant", niveau_alerte="risque_eleve",
         description="Apport calorique < 70% des besoins estimés du profil, sur 3 jours consécutifs.",
         message="Votre apport calorique semble nettement insuffisant sur plusieurs jours. Nous vous recommandons d'en parler à un professionnel de santé.",
         reference_scientifique="Seuil de sécurité standard, orientation prudente (pas de diagnostic)."),
    dict(identifiant="R09", nom="Aliment à IG élevé, consommation fréquente (diabète)", niveau_alerte="vigilance",
         description="Profil = diabète ET aliment à IG élevé ET fréquence >= 4 fois/semaine.",
         message="Cet aliment a un index glycémique élevé et revient souvent dans votre alimentation. Une répartition plus étalée peut aider à stabiliser la glycémie.",
         reference_scientifique="Littérature sur l'index glycémique et le diabète de type 2."),
    dict(identifiant="R10", nom="Répartition des glucides déséquilibrée (diabète)", niveau_alerte="vigilance",
         description="Profil = diabète ET plus de 60% des glucides journaliers pris en un seul repas.",
         message="La majorité de vos glucides est concentrée sur un seul repas. Une répartition plus régulière est généralement conseillée.",
         reference_scientifique="Recommandations diététiques standards pour le diabète."),
    dict(identifiant="R11", nom="Sodium élevé + hypertension", niveau_alerte="risque_eleve",
         description="Profil = hypertension ET sodium journalier > 1,5 g.",
         message="Votre apport en sodium dépasse le seuil recommandé pour votre profil. Cela peut aggraver une tension artérielle déjà élevée.",
         reference_scientifique="Recommandations OMS spécifiques à l'hypertension (seuil abaissé)."),
    dict(identifiant="R12", nom="Réglisse + hypertension", niveau_alerte="vigilance",
         description="Profil = hypertension ET aliment contient de la réglisse.",
         message="La réglisse peut interférer avec la régulation de la tension artérielle.",
         reference_scientifique="Littérature pharmacologique sur la glycyrrhizine."),
    dict(identifiant="R13", nom="Pamplemousse + traitement à risque", niveau_alerte="risque_eleve",
         description="Traitement déclaré = statines ou antihypertenseurs sensibles ET aliment = pamplemousse/jus.",
         message="Le pamplemousse peut interagir avec votre traitement. Consultez votre médecin ou pharmacien avant d'en consommer régulièrement.",
         reference_scientifique="Interaction enzymatique documentée (CYP3A4), pharmacologie clinique."),
    dict(identifiant="R14", nom="Vitamine K élevée + anticoagulants", niveau_alerte="risque_eleve",
         description="Traitement déclaré = anticoagulant (type warfarine) ET aliment riche en vitamine K.",
         message="Cet aliment est riche en vitamine K, ce qui peut interférer avec l'effet de votre traitement anticoagulant. Maintenez une consommation régulière plutôt que variable, et parlez-en à votre médecin.",
         reference_scientifique="Pharmacologie clinique standard (interaction warfarine/vitamine K)."),
    dict(identifiant="R15", nom="Produits laitiers + certains antibiotiques", niveau_alerte="vigilance",
         description="Traitement déclaré = tétracyclines/quinolones ET aliment = produit laitier, pris à moins de 2h d'intervalle.",
         message="Les produits laitiers peuvent réduire l'absorption de ce type d'antibiotique. Espacez la prise d'au moins 2 heures.",
         reference_scientifique="Pharmacologie clinique standard."),
    dict(identifiant="R16", nom="Potassium élevé + insuffisance rénale", niveau_alerte="risque_eleve",
         description="Profil = insuffisance rénale ET aliment riche en potassium. Message générique tant que non validé par un néphrologue.",
         message="Cet aliment est riche en potassium. Votre situation nécessite un suivi personnalisé — parlez-en à votre néphrologue ou diététicien.",
         reference_scientifique="À valider avec un spécialiste avant déploiement."),
    dict(identifiant="R17", nom="Répétition excessive d'un seul aliment", niveau_alerte="vigilance",
         description="Un même aliment représente > 50% des calories sur 5 jours consécutifs.",
         message="Vous consommez très régulièrement le même aliment. Varier votre alimentation aide à couvrir l'ensemble de vos besoins en nutriments.",
         reference_scientifique="Principe de diversité alimentaire (recommandation standard)."),
    dict(identifiant="R18", nom="Sauts de repas répétés", niveau_alerte="info",
         description="Absence d'enregistrement de repas sur une plage horaire habituelle, 4 jours sur 7.",
         message="Vous semblez sauter des repas régulièrement cette semaine. Si cela n'est pas volontaire, cela peut affecter votre énergie au quotidien.",
         reference_scientifique="Recommandation générale de régularité alimentaire."),
]


class Command(BaseCommand):
    help = "Pré-charge les règles nutritionnelles R01 à R18 (statut brouillon, à valider)."

    def handle(self, *args, **options):
        creees, existantes = 0, 0
        for regle in REGLES:
            obj, cree = R.objects.get_or_create(identifiant=regle["identifiant"], defaults=regle)
            if cree:
                creees += 1
            else:
                existantes += 1
        self.stdout.write(self.style.SUCCESS(
            f"{creees} règle(s) créée(s), {existantes} déjà présente(s)."
        ))
        self.stdout.write(
            "Rappel : toutes les règles sont en statut 'brouillon'. "
            "Faites-les valider par un(e) diététicien(ne) avant de passer leur statut à 'validee'."
        )
