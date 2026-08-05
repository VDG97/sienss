from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import (
    Aliment,
    AllergieUtilisateur,
    PathologieUtilisateur,
    Professionnel,
    ProfilSante,
    RendezVous,
    Repas,
    RepasAliment,
    TraitementUtilisateur,
    Utilisateur,
)


class InscriptionForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Adresse e-mail")
    consentement_donnees_sante = forms.BooleanField(
        required=True,
        label="J'accepte que mes données de santé soient traitées pour l'analyse "
              "nutritionnelle (voir conditions d'utilisation).",
    )

    class Meta:
        model = Utilisateur
        fields = ["username", "email", "password1", "password2"]
        labels = {"username": "Nom d'utilisateur"}


class ProfilSanteForm(forms.ModelForm):
    class Meta:
        model = ProfilSante
        fields = [
            "taille_cm", "poids_actuel_kg", "poids_cible_kg",
            "niveau_activite_physique", "objectif_nutritionnel",
            "grossesse", "allaitement",
        ]
        labels = {
            "taille_cm": "Taille (cm)",
            "poids_actuel_kg": "Poids actuel (kg)",
            "poids_cible_kg": "Poids cible (kg, optionnel)",
            "niveau_activite_physique": "Niveau d'activité physique",
            "objectif_nutritionnel": "Objectif",
            "grossesse": "Grossesse en cours",
            "allaitement": "Allaitement en cours",
        }


class RepasForm(forms.ModelForm):
    class Meta:
        model = Repas
        fields = ["date", "heure", "type_repas", "commentaire"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "heure": forms.TimeInput(attrs={"type": "time"}),
        }
        labels = {
            "date": "Date",
            "heure": "Heure",
            "type_repas": "Type de repas",
            "commentaire": "Commentaire (optionnel)",
        }


class RepasAlimentForm(forms.Form):
    """
    Formulaire volontairement non lié directement au modèle : on ne demande
    plus un poids en grammes (irréaliste pour un utilisateur du grand public),
    mais une taille de portion relative à la portion standard de l'aliment.
    La conversion en grammes se fait dans la vue à partir de
    Aliment.portion_standard_g (voir Chapitre 3.3 : "portion" plutôt que poids
    exact — corrigé suite aux retours utilisateurs).
    """
    PORTION_CHOIX = [
        ("", "—"),
        ("0.5", "Petite portion"),
        ("1", "Portion normale"),
        ("1.5", "Grande portion"),
        ("2", "Très grande portion"),
    ]

    aliment = forms.ModelChoiceField(
        queryset=Aliment.objects.all().order_by("nom"),
        label="Aliment",
        required=False,
        widget=forms.Select(attrs={"class": "aliment-select"}),
    )
    portion = forms.ChoiceField(
        choices=PORTION_CHOIX, label="Quantité", required=False,
    )

    def clean(self):
        """Une ligne vide (ni aliment ni portion) est acceptée : elle sera ignorée
        par le formset plutôt que de bloquer l'enregistrement du repas."""
        cleaned = super().clean()
        aliment = cleaned.get("aliment")
        portion = cleaned.get("portion")
        if aliment and not portion:
            self.add_error("portion", "Choisissez une taille de portion pour cet aliment.")
        if portion and not aliment:
            self.add_error("aliment", "Sélectionnez un aliment pour cette portion.")
        return cleaned


# Formset : jusqu'à 8 aliments par repas dans la V1 (pas de suppression dynamique en JS
# pour rester simple ; l'utilisateur laisse les lignes en trop vides).
RepasAlimentFormSet = forms.formset_factory(RepasAlimentForm, extra=8)


class AllergieForm(forms.ModelForm):
    class Meta:
        model = AllergieUtilisateur
        fields = ["allergene", "gravite"]
        labels = {"allergene": "Allergène", "gravite": "Gravité (optionnel)"}
        widgets = {"allergene": forms.TextInput(attrs={"placeholder": "Ex : arachide, lactose, gluten"})}


class PathologieForm(forms.ModelForm):
    class Meta:
        model = PathologieUtilisateur
        fields = ["pathologie", "statut"]
        labels = {"pathologie": "Pathologie", "statut": "Statut (optionnel)"}
        widgets = {"pathologie": forms.TextInput(attrs={"placeholder": "Ex : diabète, hypertension"})}


class TraitementForm(forms.ModelForm):
    class Meta:
        model = TraitementUtilisateur
        fields = ["medicament", "dose", "frequence", "date_debut", "date_fin"]
        labels = {
            "medicament": "Médicament",
            "dose": "Dose (optionnel)",
            "frequence": "Fréquence (optionnel)",
            "date_debut": "Date de début (optionnel)",
            "date_fin": "Date de fin (optionnel)",
        }
        widgets = {
            "date_debut": forms.DateInput(attrs={"type": "date"}),
            "date_fin": forms.DateInput(attrs={"type": "date"}),
        }


class ProfessionnelForm(forms.ModelForm):
    class Meta:
        model = Professionnel
        fields = ["specialite", "specialite_autre", "bio", "numero_autorisation", "accepte_teleconsultation"]
        labels = {
            "specialite": "Spécialité",
            "specialite_autre": "Précisez (si 'Autre spécialité')",
            "bio": "Présentation courte",
            "numero_autorisation": "Numéro d'autorisation d'exercer (optionnel)",
            "accepte_teleconsultation": "J'accepte les téléconsultations vidéo",
        }
        widgets = {"bio": forms.Textarea(attrs={"rows": 3})}


class RendezVousForm(forms.ModelForm):
    class Meta:
        model = RendezVous
        fields = ["date_heure", "motif", "type_rendezvous"]
        labels = {
            "date_heure": "Date et heure souhaitées",
            "motif": "Motif (optionnel)",
            "type_rendezvous": "Type de rendez-vous",
        }
        widgets = {
            "date_heure": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }
