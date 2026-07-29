import uuid
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


# ---------------------------------------------------------------------------
# 5.1 Utilisateurs
# ---------------------------------------------------------------------------
class Utilisateur(AbstractUser):
    """
    Étend le modèle utilisateur standard de Django.
    Django gère déjà : username/email, mot de passe haché, date_joined,
    last_login, is_active (= statut du compte).
    On ajoute uniquement les champs propres au cahier des charges (Ch. 5.1).
    """

    class Role(models.TextChoices):
        UTILISATEUR = "utilisateur", "Utilisateur"
        NUTRITIONNISTE = "nutritionniste", "Nutritionniste"
        DIETETICIEN = "dieteticien", "Diététicien"
        MEDECIN = "medecin", "Médecin"
        ADMINISTRATEUR = "administrateur", "Administrateur"
        COMITE_SCIENTIFIQUE = "comite_scientifique", "Comité scientifique"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date_naissance = models.DateField(null=True, blank=True)

    class Sexe(models.TextChoices):
        HOMME = "H", "Homme"
        FEMME = "F", "Femme"
        AUTRE = "A", "Autre / non précisé"

    sexe = models.CharField(max_length=1, choices=Sexe.choices, blank=True)
    telephone = models.CharField(max_length=30, blank=True)
    photo_profil = models.ImageField(upload_to="profils/", null=True, blank=True)
    langue = models.CharField(max_length=10, default="fr")
    pays = models.CharField(max_length=100, blank=True)
    role = models.CharField(max_length=30, choices=Role.choices, default=Role.UTILISATEUR)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"


# ---------------------------------------------------------------------------
# 5.2 Profils de santé (une entrée = état courant)
# ---------------------------------------------------------------------------
class ProfilSante(models.Model):
    class NiveauActivite(models.TextChoices):
        SEDENTAIRE = "sedentaire", "Sédentaire"
        LEGER = "leger", "Léger"
        MODERE = "modere", "Modéré"
        INTENSE = "intense", "Intense"

    class Objectif(models.TextChoices):
        PERTE_POIDS = "perte_poids", "Perte de poids"
        MAINTIEN = "maintien", "Maintien"
        PRISE_MASSE = "prise_masse", "Prise de masse"
        EQUILIBRE = "equilibre", "Équilibre alimentaire"
        SUIVI_MEDICAL = "suivi_medical", "Suivi médical"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profil_sante"
    )
    taille_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    poids_actuel_kg = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    poids_cible_kg = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    niveau_activite_physique = models.CharField(
        max_length=20, choices=NiveauActivite.choices, blank=True
    )
    objectif_nutritionnel = models.CharField(max_length=20, choices=Objectif.choices, blank=True)
    grossesse = models.BooleanField(default=False)
    allaitement = models.BooleanField(default=False)
    date_maj = models.DateTimeField(auto_now=True)

    @property
    def imc(self):
        """Calculé à la volée, jamais stocké en dur (voir Chapitre 5, §5.2)."""
        if self.taille_cm and self.poids_actuel_kg:
            taille_m = float(self.taille_cm) / 100
            return round(float(self.poids_actuel_kg) / (taille_m ** 2), 1)
        return None

    def __str__(self):
        return f"Profil santé de {self.utilisateur}"


# ---------------------------------------------------------------------------
# Allergies / pathologies / traitements déclarés (Ch. 5.5)
# ---------------------------------------------------------------------------
class AllergieUtilisateur(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="allergies"
    )
    allergene = models.CharField(max_length=100)
    gravite = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.allergene} ({self.utilisateur})"


class PathologieUtilisateur(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pathologies"
    )
    pathologie = models.CharField(max_length=150)
    date_declaration = models.DateField(auto_now_add=True)
    statut = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.pathologie} ({self.utilisateur})"


class TraitementUtilisateur(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="traitements"
    )
    medicament = models.CharField(max_length=150)
    dose = models.CharField(max_length=100, blank=True)
    frequence = models.CharField(max_length=100, blank=True)
    date_debut = models.DateField(null=True, blank=True)
    date_fin = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.medicament} ({self.utilisateur})"


# ---------------------------------------------------------------------------
# 5.7 Aliments
# ---------------------------------------------------------------------------
class Aliment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=150)
    nom_local = models.CharField(max_length=150, blank=True)
    categorie = models.CharField(max_length=100, blank=True)
    origine = models.CharField(max_length=100, blank=True)
    photo = models.ImageField(upload_to="aliments/", null=True, blank=True)
    portion_standard_g = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)

    # Valeurs nutritionnelles pour 100 g
    calories = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    proteines = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    glucides = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    lipides = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    fibres = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    sodium_mg = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    sucres = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    graisses_saturees = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    potassium_mg = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    vitamine_k_mcg = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    index_glycemique = models.PositiveSmallIntegerField(null=True, blank=True)

    allergenes = models.CharField(
        max_length=255, blank=True, help_text="Liste séparée par des virgules, ex: arachide,lait"
    )
    niveau_confiance = models.CharField(
        max_length=20,
        choices=[("faible", "Faible"), ("moyen", "Moyen"), ("eleve", "Élevé")],
        default="moyen",
    )
    source_donnee = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return self.nom


# ---------------------------------------------------------------------------
# 5.8 Repas / Repas_Aliments
# ---------------------------------------------------------------------------
class Repas(models.Model):
    class TypeRepas(models.TextChoices):
        PETIT_DEJ = "petit_dejeuner", "Petit-déjeuner"
        DEJEUNER = "dejeuner", "Déjeuner"
        DINER = "diner", "Dîner"
        COLLATION = "collation", "Collation"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="repas"
    )
    date = models.DateField()
    heure = models.TimeField()
    type_repas = models.CharField(max_length=20, choices=TypeRepas.choices)
    commentaire = models.TextField(blank=True)
    photo = models.ImageField(upload_to="repas/", null=True, blank=True)

    class Meta:
        ordering = ["-date", "-heure"]

    def __str__(self):
        return f"{self.get_type_repas_display()} du {self.date} ({self.utilisateur})"


class RepasAliment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    repas = models.ForeignKey(Repas, on_delete=models.CASCADE, related_name="aliments_consommes")
    aliment = models.ForeignKey(Aliment, on_delete=models.PROTECT)
    quantite_g = models.DecimalField(max_digits=6, decimal_places=1)

    def __str__(self):
        return f"{self.quantite_g} g de {self.aliment} dans {self.repas}"


# ---------------------------------------------------------------------------
# Règles nutritionnelles (R01 à R18) — Ch. 5.10 et liste des règles fournie
# ---------------------------------------------------------------------------
class RegleNutritionnelle(models.Model):
    class Niveau(models.TextChoices):
        INFO = "info", "🟢 Info"
        VIGILANCE = "vigilance", "🟡 Vigilance"
        RISQUE_ELEVE = "risque_eleve", "🔴 Risque élevé"

    class Statut(models.TextChoices):
        BROUILLON = "brouillon", "Brouillon"
        VALIDEE = "validee", "Validée"
        RETIREE = "retiree", "Retirée"

    identifiant = models.CharField(max_length=10, unique=True, help_text="Ex: R01")
    nom = models.CharField(max_length=150)
    description = models.TextField()
    niveau_alerte = models.CharField(max_length=20, choices=Niveau.choices)
    message = models.TextField()
    reference_scientifique = models.TextField(blank=True)
    version = models.CharField(max_length=20, default="1.0")
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.BROUILLON)
    date_validation = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.identifiant} — {self.nom}"


# ---------------------------------------------------------------------------
# Alertes générées par le moteur d'analyse
# ---------------------------------------------------------------------------
class Alerte(models.Model):
    class Statut(models.TextChoices):
        ACTIVE = "active", "Active"
        RESOLUE = "resolue", "Résolue"
        IGNOREE = "ignoree", "Ignorée"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="alertes"
    )
    regle = models.ForeignKey(RegleNutritionnelle, on_delete=models.PROTECT)
    repas = models.ForeignKey(
        Repas, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Repas ayant déclenché l'alerte, si applicable",
    )
    date_generation = models.DateTimeField(auto_now_add=True)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.ACTIVE)

    class Meta:
        ordering = ["-date_generation"]

    def __str__(self):
        return f"Alerte {self.regle.identifiant} pour {self.utilisateur} ({self.statut})"


# ---------------------------------------------------------------------------
# Scores (Ch. 5.11) — V1 : uniquement "alimentaire" et "indice_fiabilite"
# ---------------------------------------------------------------------------
class Score(models.Model):
    class TypeScore(models.TextChoices):
        ALIMENTAIRE = "alimentaire", "Score alimentaire"
        ACTIVITE = "activite", "Score activité"  # activé en V2
        EVOLUTION_CORPORELLE = "evolution_corporelle", "Score évolution corporelle"  # V2
        INDICE_FIABILITE = "indice_fiabilite", "Indice de fiabilité"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="scores"
    )
    type_score = models.CharField(max_length=30, choices=TypeScore.choices)
    valeur = models.DecimalField(max_digits=5, decimal_places=1)
    date_calcul = models.DateField(auto_now_add=True)
    detail = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-date_calcul"]

    def __str__(self):
        return f"{self.get_type_score_display()} = {self.valeur} ({self.utilisateur})"
