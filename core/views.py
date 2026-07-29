from datetime import timedelta

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.db import models
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone

from .forms import (
    AllergieForm,
    InscriptionForm,
    PathologieForm,
    ProfilSanteForm,
    RepasAlimentFormSet,
    RepasForm,
    TraitementForm,
)
from .models import Alerte, Aliment, AllergieUtilisateur, PathologieUtilisateur, ProfilSante, Repas, RepasAliment, Score, TraitementUtilisateur
from .moteur_analyse import analyser_repas
from .scores import mettre_a_jour_scores


def inscription(request):
    if request.user.is_authenticated:
        return redirect("tableau_bord")

    if request.method == "POST":
        form = InscriptionForm(request.POST)
        if form.is_valid():
            utilisateur = form.save()
            ProfilSante.objects.create(utilisateur=utilisateur)
            login(request, utilisateur)
            messages.success(request, "Bienvenue sur SIENSS ! Complétez votre profil de santé pour commencer.")
            return redirect("profil_sante")
    else:
        form = InscriptionForm()

    return render(request, "core/inscription.html", {"form": form})


class ConnexionView(LoginView):
    template_name = "core/connexion.html"
    redirect_authenticated_user = True


@login_required
def profil_sante(request):
    profil, _ = ProfilSante.objects.get_or_create(utilisateur=request.user)

    if request.method == "POST":
        form = ProfilSanteForm(request.POST, instance=profil)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil de santé mis à jour.")
            return redirect("tableau_bord")
    else:
        form = ProfilSanteForm(instance=profil)

    return render(request, "core/profil_sante.html", {"form": form})


@login_required
def tableau_bord(request):
    aujourdhui = timezone.localdate()
    date_debut_semaine = aujourdhui - timedelta(days=6)

    repas_aujourdhui = request.user.repas.filter(date=aujourdhui)
    alertes_actives = request.user.alertes.filter(statut=Alerte.Statut.ACTIVE).select_related("regle")[:10]
    profil = getattr(request.user, "profil_sante", None)

    def _dernier_score(type_score):
        return request.user.scores.filter(type_score=type_score).order_by("-date_calcul").first()

    contexte = {
        "repas_aujourdhui": repas_aujourdhui,
        "nb_repas_semaine": request.user.repas.filter(date__gte=date_debut_semaine).count(),
        "alertes_actives": alertes_actives,
        "profil": profil,
        "score_alimentaire": _dernier_score(Score.TypeScore.ALIMENTAIRE),
        "score_fiabilite": _dernier_score(Score.TypeScore.INDICE_FIABILITE),
    }
    return render(request, "core/tableau_bord.html", contexte)


@login_required
def ajouter_repas(request):
    if request.method == "POST":
        repas_form = RepasForm(request.POST)
        aliment_formset = RepasAlimentFormSet(
            request.POST, queryset=RepasAliment.objects.none(), prefix="aliments"
        )
        if repas_form.is_valid() and aliment_formset.is_valid():
            lignes_remplies = [
                f for f in aliment_formset.forms
                if f.cleaned_data.get("aliment") and f.cleaned_data.get("quantite_g")
            ]
            if not lignes_remplies:
                messages.error(request, "Ajoutez au moins un aliment à ce repas.")
            else:
                repas = repas_form.save(commit=False)
                repas.utilisateur = request.user
                repas.save()

                for f in lignes_remplies:
                    RepasAliment.objects.create(
                        repas=repas,
                        aliment=f.cleaned_data["aliment"],
                        quantite_g=f.cleaned_data["quantite_g"],
                    )

                alertes = analyser_repas(repas)
                mettre_a_jour_scores(request.user)
                if alertes:
                    noms_regles = ", ".join(a.regle.identifiant for a in alertes)
                    messages.warning(request, f"Repas enregistré ({len(lignes_remplies)} aliment(s)). Nouvelle(s) alerte(s) : {noms_regles}.")
                else:
                    messages.success(request, f"Repas enregistré ({len(lignes_remplies)} aliment(s)). Aucune alerte détectée.")
                return redirect("tableau_bord")
    else:
        repas_form = RepasForm(initial={"date": timezone.localdate()})
        aliment_formset = RepasAlimentFormSet(queryset=RepasAliment.objects.none(), prefix="aliments")

    return render(request, "core/ajouter_repas.html", {
        "repas_form": repas_form,
        "aliment_formset": aliment_formset,
    })


@login_required
def rechercher_aliment(request):
    """Endpoint JSON pour l'autocomplétion d'aliment (remplace le menu déroulant
    simple, qui devenait peu pratique à mesure que la base alimentaire grandit)."""
    from django.http import JsonResponse

    requete = request.GET.get("q", "").strip()
    if len(requete) < 2:
        return JsonResponse({"resultats": []})

    aliments = Aliment.objects.filter(
        models.Q(nom__icontains=requete) | models.Q(nom_local__icontains=requete)
    ).order_by("nom")[:10]

    return JsonResponse({
        "resultats": [
            {"id": str(a.id), "nom": a.nom, "categorie": a.categorie}
            for a in aliments
        ]
    })


@login_required
def historique(request):
    periode = request.GET.get("periode", "semaine")
    aujourdhui = timezone.localdate()

    bornes_periode = {
        "jour": aujourdhui,
        "semaine": aujourdhui - timedelta(days=6),
        "mois": aujourdhui - timedelta(days=29),
        "annee": aujourdhui - timedelta(days=364),
    }
    date_debut = bornes_periode.get(periode, bornes_periode["semaine"])
    if periode not in bornes_periode:
        periode = "semaine"

    repas = request.user.repas.filter(date__gte=date_debut).prefetch_related("aliments_consommes__aliment")[:200]
    alertes = request.user.alertes.filter(date_generation__date__gte=date_debut).select_related("regle")[:200]

    return render(request, "core/historique.html", {
        "repas": repas, "alertes": alertes, "periode": periode,
        "periodes": [("jour", "Aujourd'hui"), ("semaine", "7 jours"), ("mois", "30 jours"), ("annee", "1 an")],
    })


@login_required
def informations_medicales(request):
    """
    Écran unique regroupant allergies, pathologies et traitements déclarés.
    Chaque section a son propre mini-formulaire d'ajout (POST distinct via le
    champ caché 'formulaire', pour rester sur une seule page).
    """
    allergie_form = AllergieForm()
    pathologie_form = PathologieForm()
    traitement_form = TraitementForm()

    if request.method == "POST":
        type_formulaire = request.POST.get("formulaire")

        if type_formulaire == "allergie":
            allergie_form = AllergieForm(request.POST)
            if allergie_form.is_valid():
                allergie = allergie_form.save(commit=False)
                allergie.utilisateur = request.user
                allergie.save()
                messages.success(request, "Allergie ajoutée.")
                return redirect("informations_medicales")

        elif type_formulaire == "pathologie":
            pathologie_form = PathologieForm(request.POST)
            if pathologie_form.is_valid():
                pathologie = pathologie_form.save(commit=False)
                pathologie.utilisateur = request.user
                pathologie.save()
                messages.success(request, "Pathologie ajoutée.")
                return redirect("informations_medicales")

        elif type_formulaire == "traitement":
            traitement_form = TraitementForm(request.POST)
            if traitement_form.is_valid():
                traitement = traitement_form.save(commit=False)
                traitement.utilisateur = request.user
                traitement.save()
                messages.success(request, "Traitement ajouté.")
                return redirect("informations_medicales")

    return render(request, "core/informations_medicales.html", {
        "allergie_form": allergie_form,
        "pathologie_form": pathologie_form,
        "traitement_form": traitement_form,
        "allergies": request.user.allergies.all(),
        "pathologies": request.user.pathologies.all(),
        "traitements": request.user.traitements.all(),
    })


@login_required
def supprimer_allergie(request, pk):
    AllergieUtilisateur.objects.filter(pk=pk, utilisateur=request.user).delete()
    messages.success(request, "Allergie supprimée.")
    return redirect("informations_medicales")


@login_required
def supprimer_pathologie(request, pk):
    PathologieUtilisateur.objects.filter(pk=pk, utilisateur=request.user).delete()
    messages.success(request, "Pathologie supprimée.")
    return redirect("informations_medicales")


@login_required
def supprimer_traitement(request, pk):
    TraitementUtilisateur.objects.filter(pk=pk, utilisateur=request.user).delete()
    messages.success(request, "Traitement supprimé.")
    return redirect("informations_medicales")


@login_required
def modifier_allergie(request, pk):
    allergie = get_object_or_404(AllergieUtilisateur, pk=pk, utilisateur=request.user)
    if request.method == "POST":
        form = AllergieForm(request.POST, instance=allergie)
        if form.is_valid():
            form.save()
            messages.success(request, "Allergie modifiée.")
            return redirect("informations_medicales")
    else:
        form = AllergieForm(instance=allergie)
    return render(request, "core/modifier_element_medical.html", {
        "form": form, "titre": "Modifier l'allergie",
    })


@login_required
def modifier_pathologie(request, pk):
    pathologie = get_object_or_404(PathologieUtilisateur, pk=pk, utilisateur=request.user)
    if request.method == "POST":
        form = PathologieForm(request.POST, instance=pathologie)
        if form.is_valid():
            form.save()
            messages.success(request, "Pathologie modifiée.")
            return redirect("informations_medicales")
    else:
        form = PathologieForm(instance=pathologie)
    return render(request, "core/modifier_element_medical.html", {
        "form": form, "titre": "Modifier la pathologie",
    })


@login_required
def modifier_traitement(request, pk):
    traitement = get_object_or_404(TraitementUtilisateur, pk=pk, utilisateur=request.user)
    if request.method == "POST":
        form = TraitementForm(request.POST, instance=traitement)
        if form.is_valid():
            form.save()
            messages.success(request, "Traitement modifié.")
            return redirect("informations_medicales")
    else:
        form = TraitementForm(instance=traitement)
    return render(request, "core/modifier_element_medical.html", {
        "form": form, "titre": "Modifier le traitement",
    })


@login_required
def supprimer_compte(request):
    """Suppression de compte (Chapitre 3.1). Demande explicite de confirmation
    par mot de passe avant toute suppression irréversible."""
    if request.method == "POST":
        mot_de_passe = request.POST.get("mot_de_passe", "")
        if request.user.check_password(mot_de_passe):
            utilisateur = request.user
            logout(request)
            utilisateur.delete()
            messages.success(request, "Votre compte a été supprimé. Vos données ont été effacées.")
            return redirect("connexion")
        else:
            messages.error(request, "Mot de passe incorrect — le compte n'a pas été supprimé.")

    return render(request, "core/supprimer_compte.html")
