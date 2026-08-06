"""
URL configuration for sienss project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from core import views as core_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', core_views.accueil, name='accueil'),
    path('inscription/', core_views.inscription, name='inscription'),
    path('connexion/', core_views.ConnexionView.as_view(), name='connexion'),
    path('deconnexion/', auth_views.LogoutView.as_view(next_page='connexion'), name='deconnexion'),

    # Réinitialisation de mot de passe (Chapitre 3.1)
    path('mot-de-passe/reinitialiser/', auth_views.PasswordResetView.as_view(
        template_name='core/mot_de_passe_reinitialiser.html',
        email_template_name='core/emails/mot_de_passe_email.txt',
        subject_template_name='core/emails/mot_de_passe_sujet.txt',
        success_url='/mot-de-passe/reinitialiser/envoye/',
    ), name='mot_de_passe_reinitialiser'),
    path('mot-de-passe/reinitialiser/envoye/', auth_views.PasswordResetDoneView.as_view(
        template_name='core/mot_de_passe_envoye.html',
    ), name='password_reset_done'),
    path('mot-de-passe/reinitialiser/confirmer/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='core/mot_de_passe_confirmer.html',
        success_url='/mot-de-passe/reinitialiser/termine/',
    ), name='password_reset_confirm'),
    path('mot-de-passe/reinitialiser/termine/', auth_views.PasswordResetCompleteView.as_view(
        template_name='core/mot_de_passe_termine.html',
    ), name='password_reset_complete'),

    path('profil/', core_views.profil_sante, name='profil_sante'),
    path('profil/informations-medicales/', core_views.informations_medicales, name='informations_medicales'),
    path('profil/allergies/<uuid:pk>/supprimer/', core_views.supprimer_allergie, name='supprimer_allergie'),
    path('profil/allergies/<uuid:pk>/modifier/', core_views.modifier_allergie, name='modifier_allergie'),
    path('profil/pathologies/<uuid:pk>/supprimer/', core_views.supprimer_pathologie, name='supprimer_pathologie'),
    path('profil/pathologies/<uuid:pk>/modifier/', core_views.modifier_pathologie, name='modifier_pathologie'),
    path('profil/traitements/<uuid:pk>/supprimer/', core_views.supprimer_traitement, name='supprimer_traitement'),
    path('profil/traitements/<uuid:pk>/modifier/', core_views.modifier_traitement, name='modifier_traitement'),
    path('profil/supprimer-compte/', core_views.supprimer_compte, name='supprimer_compte'),

    path('tableau-de-bord/', core_views.tableau_bord, name='tableau_bord'),
    path('repas/ajouter/', core_views.ajouter_repas, name='ajouter_repas'),
    path('aliments/rechercher/', core_views.rechercher_aliment, name='rechercher_aliment'),
    path('historique/', core_views.historique, name='historique'),
    path('conseils/', core_views.conseils, name='conseils'),
    path('professionnels/', core_views.annuaire_professionnels, name='annuaire_professionnels'),
    path('professionnels/devenir/', core_views.devenir_professionnel, name='devenir_professionnel'),
    path('professionnels/<uuid:professionnel_id>/rendez-vous/', core_views.demander_rendezvous, name='demander_rendezvous'),
    path('rendez-vous/', core_views.mes_rendezvous, name='mes_rendezvous'),
    path('rendez-vous/<uuid:pk>/confirmer/', core_views.confirmer_rendezvous, name='confirmer_rendezvous'),
    path('rendez-vous/<uuid:pk>/annuler/', core_views.annuler_rendezvous, name='annuler_rendezvous'),
    path('rendez-vous/<uuid:pk>/salle/', core_views.salle_teleconsultation, name='salle_teleconsultation'),

    # Validation des professionnels par un administrateur
    path('administration/professionnels/', core_views.validation_professionnels, name='validation_professionnels'),
    path('administration/professionnels/<uuid:pk>/valider/', core_views.valider_professionnel, name='valider_professionnel'),
    path('administration/professionnels/<uuid:pk>/rejeter/', core_views.rejeter_professionnel, name='rejeter_professionnel'),
]
