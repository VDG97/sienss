from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    Aliment,
    Alerte,
    AllergieUtilisateur,
    PathologieUtilisateur,
    Professionnel,
    ProfilSante,
    RegleNutritionnelle,
    RendezVous,
    Repas,
    RepasAliment,
    Score,
    TraitementUtilisateur,
    Utilisateur,
)


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    list_display = ("username", "email", "role", "is_active", "date_joined")
    list_filter = ("role", "is_active")
    fieldsets = UserAdmin.fieldsets + (
        ("Informations SIENSS", {"fields": ("role", "date_naissance", "sexe", "telephone", "pays")}),
    )


@admin.register(ProfilSante)
class ProfilSanteAdmin(admin.ModelAdmin):
    list_display = ("utilisateur", "taille_cm", "poids_actuel_kg", "imc", "objectif_nutritionnel")


@admin.register(Aliment)
class AlimentAdmin(admin.ModelAdmin):
    list_display = ("nom", "categorie", "origine", "calories", "niveau_confiance")
    search_fields = ("nom", "nom_local")
    list_filter = ("categorie", "niveau_confiance")


@admin.register(Repas)
class RepasAdmin(admin.ModelAdmin):
    list_display = ("utilisateur", "date", "heure", "type_repas")
    list_filter = ("type_repas", "date")


@admin.register(RegleNutritionnelle)
class RegleNutritionnelleAdmin(admin.ModelAdmin):
    list_display = ("identifiant", "nom", "niveau_alerte", "statut", "version")
    list_filter = ("niveau_alerte", "statut")


@admin.register(Alerte)
class AlerteAdmin(admin.ModelAdmin):
    list_display = ("utilisateur", "regle", "statut", "date_generation")
    list_filter = ("statut",)


@admin.register(Score)
class ScoreAdmin(admin.ModelAdmin):
    list_display = ("utilisateur", "type_score", "valeur", "date_calcul")
    list_filter = ("type_score",)


admin.site.register(AllergieUtilisateur)
admin.site.register(PathologieUtilisateur)
admin.site.register(TraitementUtilisateur)
admin.site.register(RepasAliment)


@admin.register(Professionnel)
class ProfessionnelAdmin(admin.ModelAdmin):
    list_display = ("utilisateur", "specialite", "verifie", "accepte_teleconsultation", "date_inscription")
    list_filter = ("specialite", "verifie", "accepte_teleconsultation")
    actions = ["verifier_les_professionnels"]

    @admin.action(description="Marquer comme vérifié(s) — les rend visibles dans l'annuaire")
    def verifier_les_professionnels(self, request, queryset):
        queryset.update(verifie=True)


@admin.register(RendezVous)
class RendezVousAdmin(admin.ModelAdmin):
    list_display = ("patient", "professionnel", "date_heure", "type_rendezvous", "statut")
    list_filter = ("statut", "type_rendezvous")
