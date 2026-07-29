"""
Commande : python manage.py importer_aliments [chemin_csv]

Importe des aliments depuis un fichier CSV dans la table Aliment.
Par défaut, importe le fichier de départ fourni avec le projet
(core/data/aliments_depart.csv), qui contient des aliments courants
et des aliments béninois/ouest-africains avec des valeurs nutritionnelles
estimées (voir colonne "source_donnee" — beaucoup restent à valider avec
une vraie table de composition alimentaire).

Colonnes attendues (voir aliments_depart.csv pour un exemple) :
nom, nom_local, categorie, origine, portion_standard_g, calories,
proteines, glucides, lipides, fibres, sodium_mg, sucres,
graisses_saturees, potassium_mg, vitamine_k_mcg, index_glycemique,
allergenes, niveau_confiance, source_donnee

--- Pour importer un export Open Food Facts (à faire chez vous, cet ---
--- environnement n'a pas accès à openfoodfacts.org) :
1. Télécharger un export CSV filtré (voir https://world.openfoodfacts.org/data)
2. Adapter le mapping de colonnes ci-dessous à l'export OFF, dont les noms
   de colonnes diffèrent (ex: "product_name", "energy-kcal_100g",
   "proteins_100g", "carbohydrates_100g", "fat_100g", "fiber_100g",
   "sodium_100g", "sugars_100g", "saturated-fat_100g", "allergens", etc.)
3. OFF fournit peu ou pas d'aliments béninois/locaux — c'est pourquoi le
   fichier de départ de ce projet les couvre manuellement en attendant
   une meilleure source.
"""
import csv
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.models import Aliment


def _decimal_ou_none(valeur):
    if valeur is None or valeur.strip() == "":
        return None
    try:
        return Decimal(valeur.strip())
    except InvalidOperation:
        return None


def _int_ou_none(valeur):
    if valeur is None or valeur.strip() == "":
        return None
    try:
        return int(float(valeur.strip()))
    except ValueError:
        return None


class Command(BaseCommand):
    help = "Importe des aliments depuis un fichier CSV (par défaut : le jeu de données de départ)."

    def add_arguments(self, parser):
        parser.add_argument(
            "chemin_csv", nargs="?", default=None,
            help="Chemin du fichier CSV à importer (par défaut : core/data/aliments_depart.csv)",
        )

    def handle(self, *args, **options):
        chemin = options["chemin_csv"] or str(
            settings.BASE_DIR / "core" / "data" / "aliments_depart.csv"
        )

        try:
            fichier = open(chemin, newline="", encoding="utf-8")
        except FileNotFoundError:
            raise CommandError(f"Fichier introuvable : {chemin}")

        creees, mises_a_jour = 0, 0
        with fichier:
            lecteur = csv.DictReader(fichier)
            for ligne in lecteur:
                nom = (ligne.get("nom") or "").strip()
                if not nom:
                    continue

                valeurs = dict(
                    nom_local=(ligne.get("nom_local") or "").strip(),
                    categorie=(ligne.get("categorie") or "").strip(),
                    origine=(ligne.get("origine") or "").strip(),
                    portion_standard_g=_decimal_ou_none(ligne.get("portion_standard_g")),
                    calories=_decimal_ou_none(ligne.get("calories")),
                    proteines=_decimal_ou_none(ligne.get("proteines")),
                    glucides=_decimal_ou_none(ligne.get("glucides")),
                    lipides=_decimal_ou_none(ligne.get("lipides")),
                    fibres=_decimal_ou_none(ligne.get("fibres")),
                    sodium_mg=_decimal_ou_none(ligne.get("sodium_mg")),
                    sucres=_decimal_ou_none(ligne.get("sucres")),
                    graisses_saturees=_decimal_ou_none(ligne.get("graisses_saturees")),
                    potassium_mg=_decimal_ou_none(ligne.get("potassium_mg")),
                    vitamine_k_mcg=_decimal_ou_none(ligne.get("vitamine_k_mcg")),
                    index_glycemique=_int_ou_none(ligne.get("index_glycemique")),
                    allergenes=(ligne.get("allergenes") or "").strip(),
                    niveau_confiance=(ligne.get("niveau_confiance") or "moyen").strip() or "moyen",
                    source_donnee=(ligne.get("source_donnee") or "").strip(),
                )

                obj, cree = Aliment.objects.update_or_create(nom=nom, defaults=valeurs)
                if cree:
                    creees += 1
                else:
                    mises_a_jour += 1

        self.stdout.write(self.style.SUCCESS(
            f"{creees} aliment(s) créé(s), {mises_a_jour} mis à jour depuis {chemin}."
        ))
        self.stdout.write(
            "Rappel : les aliments avec niveau_confiance='faible' ont des valeurs "
            "estimées à valider avec une vraie table de composition alimentaire."
        )
