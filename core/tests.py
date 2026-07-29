"""
Tests automatisés — formalisent les scénarios déjà validés manuellement au fil
du développement (voir historique du projet). Objectif : détecter toute
régression future sur le moteur de règles, les scores, ou les écrans.

Lancer avec : python manage.py test core
"""
from datetime import date, time, timedelta

from django.test import TestCase
from django.urls import reverse

from .models import (
    Aliment,
    AllergieUtilisateur,
    Alerte,
    PathologieUtilisateur,
    ProfilSante,
    RegleNutritionnelle,
    Repas,
    RepasAliment,
    TraitementUtilisateur,
    Utilisateur,
)
from .moteur_analyse import analyser_repas
from .scores import calculer_indice_fiabilite, calculer_score_alimentaire


def _charger_regles_de_test():
    """Recrée en base les règles nécessaires aux tests (indépendamment de la
    commande charger_regles, pour ne pas dépendre de sa liste complète)."""
    regles = [
        ("R01", "Allergène détecté", "risque_eleve", "Allergène présent."),
        ("R02", "Intolérance lactose", "vigilance", "Contient du lactose."),
        ("R03", "Gluten + maladie cœliaque", "risque_eleve", "Contient du gluten."),
        ("R04", "Excès de sodium", "vigilance", "Sodium élevé."),
        ("R05", "Excès de sucres", "vigilance", "Sucres élevés."),
        ("R06", "Excès de graisses saturées", "vigilance", "Graisses saturées élevées."),
        ("R07", "Fibres insuffisantes", "info", "Fibres insuffisantes."),
        ("R08", "Apport calorique insuffisant", "risque_eleve", "Apport insuffisant."),
        ("R09", "IG élevé + diabète", "vigilance", "Index glycémique élevé."),
        ("R10", "Répartition glucides déséquilibrée", "vigilance", "Glucides mal répartis."),
        ("R11", "Sodium + hypertension", "risque_eleve", "Sodium trop élevé pour hypertension."),
        ("R12", "Réglisse + hypertension", "vigilance", "Réglisse déconseillée."),
        ("R13", "Pamplemousse + traitement", "risque_eleve", "Interaction pamplemousse."),
        ("R14", "Vitamine K + anticoagulant", "risque_eleve", "Interaction vitamine K."),
        ("R15", "Laitages + antibiotiques", "vigilance", "Interaction laitages/antibiotiques."),
        ("R16", "Potassium + insuffisance rénale", "risque_eleve", "Potassium élevé."),
        ("R17", "Répétition excessive d'un aliment", "vigilance", "Aliment trop répété."),
        ("R18", "Sauts de repas répétés", "info", "Repas manquants."),
    ]
    for identifiant, nom, niveau, message in regles:
        RegleNutritionnelle.objects.get_or_create(
            identifiant=identifiant,
            defaults=dict(nom=nom, description=nom, niveau_alerte=niveau, message=message,
                          statut="validee"),
        )


class MoteurAnalyseTests(TestCase):
    """Formalise les scénarios manuels validés pendant le développement."""

    @classmethod
    def setUpTestData(cls):
        _charger_regles_de_test()
        cls.sauce_arachide = Aliment.objects.create(
            nom="Sauce arachide (test)", allergenes="arachide", calories=250, sodium_mg=400
        )
        cls.gari = Aliment.objects.create(
            nom="Gari (test)", index_glycemique=80, calories=357, glucides=86
        )
        cls.reglisse = Aliment.objects.create(nom="Bonbon réglisse (test)", calories=340)
        cls.choux = Aliment.objects.create(nom="Choux verts (test)", vitamine_k_mcg=120, calories=45)
        cls.riz = Aliment.objects.create(nom="Riz blanc (test)", calories=130)

    def _creer_utilisateur(self, username, **kwargs):
        return Utilisateur.objects.create_user(username=username, password="motdepasse", **kwargs)

    def test_R01_allergene_declenche_alerte_risque_eleve(self):
        """Scénario validé : utilisatrice allergique à l'arachide + sauce arachide -> R01."""
        u = self._creer_utilisateur("marie")
        AllergieUtilisateur.objects.create(utilisateur=u, allergene="arachide")

        repas = Repas.objects.create(utilisateur=u, date=date.today(), heure=time(12, 30), type_repas="dejeuner")
        RepasAliment.objects.create(repas=repas, aliment=self.sauce_arachide, quantite_g=150)

        alertes = analyser_repas(repas)
        identifiants = [a.regle.identifiant for a in alertes]
        self.assertIn("R01", identifiants)

        alerte_r01 = Alerte.objects.get(utilisateur=u, regle__identifiant="R01")
        self.assertEqual(alerte_r01.regle.niveau_alerte, "risque_eleve")

    def test_R01_ne_se_declenche_pas_sans_allergie_declaree(self):
        """Un utilisateur sans allergie déclarée ne doit recevoir aucune alerte R01."""
        u = self._creer_utilisateur("paul")
        repas = Repas.objects.create(utilisateur=u, date=date.today(), heure=time(12, 30), type_repas="dejeuner")
        RepasAliment.objects.create(repas=repas, aliment=self.sauce_arachide, quantite_g=150)

        alertes = analyser_repas(repas)
        self.assertNotIn("R01", [a.regle.identifiant for a in alertes])

    def test_R09_ig_eleve_repete_declenche_alerte_diabete(self):
        """Scénario validé : diabétique consommant un aliment à IG élevé 4x/semaine -> R09."""
        u = self._creer_utilisateur("fatou")
        PathologieUtilisateur.objects.create(utilisateur=u, pathologie="diabete")

        for i in range(4):
            r = Repas.objects.create(
                utilisateur=u, date=date.today() - timedelta(days=i), heure=time(8, 0), type_repas="petit_dejeuner"
            )
            RepasAliment.objects.create(repas=r, aliment=self.gari, quantite_g=150)

        alertes = analyser_repas(r)
        self.assertIn("R09", [a.regle.identifiant for a in alertes])

    def test_R09_ne_se_declenche_pas_si_moins_de_4_occurrences(self):
        """Sous le seuil de fréquence (4x/semaine), R09 ne doit pas se déclencher."""
        u = self._creer_utilisateur("issa")
        PathologieUtilisateur.objects.create(utilisateur=u, pathologie="diabete")

        r = Repas.objects.create(utilisateur=u, date=date.today(), heure=time(8, 0), type_repas="petit_dejeuner")
        RepasAliment.objects.create(repas=r, aliment=self.gari, quantite_g=150)

        alertes = analyser_repas(r)
        self.assertNotIn("R09", [a.regle.identifiant for a in alertes])

    def test_R12_reglisse_hypertension(self):
        """Scénario validé : hypertendu + réglisse -> R12."""
        u = self._creer_utilisateur("alice")
        PathologieUtilisateur.objects.create(utilisateur=u, pathologie="hypertension")

        r = Repas.objects.create(utilisateur=u, date=date.today(), heure=time(16, 0), type_repas="collation")
        RepasAliment.objects.create(repas=r, aliment=self.reglisse, quantite_g=30)

        alertes = analyser_repas(r)
        self.assertIn("R12", [a.regle.identifiant for a in alertes])

    def test_R14_vitamine_k_anticoagulant(self):
        """Scénario validé : anticoagulant + aliment riche en vitamine K -> R14."""
        u = self._creer_utilisateur("jean")
        TraitementUtilisateur.objects.create(utilisateur=u, medicament="Warfarine")

        r = Repas.objects.create(utilisateur=u, date=date.today(), heure=time(12, 0), type_repas="dejeuner")
        RepasAliment.objects.create(repas=r, aliment=self.choux, quantite_g=150)

        alertes = analyser_repas(r)
        self.assertIn("R14", [a.regle.identifiant for a in alertes])

    def test_R17_repetition_excessive_aliment(self):
        """Scénario validé : même aliment > 50% des calories sur 5 jours -> R17."""
        u = self._creer_utilisateur("fatou2")
        for i in range(5):
            r = Repas.objects.create(
                utilisateur=u, date=date.today() - timedelta(days=i), heure=time(12, 0), type_repas="dejeuner"
            )
            RepasAliment.objects.create(repas=r, aliment=self.riz, quantite_g=300)

        alertes = analyser_repas(r)
        self.assertIn("R17", [a.regle.identifiant for a in alertes])

    def test_pas_de_doublon_si_meme_repas_analyse_deux_fois(self):
        """Ré-analyser le même repas ne doit pas dupliquer l'alerte (idempotence)."""
        u = self._creer_utilisateur("no_doublon")
        AllergieUtilisateur.objects.create(utilisateur=u, allergene="arachide")

        r = Repas.objects.create(utilisateur=u, date=date.today(), heure=time(12, 0), type_repas="dejeuner")
        RepasAliment.objects.create(repas=r, aliment=self.sauce_arachide, quantite_g=100)
        analyser_repas(r)
        analyser_repas(r)  # seconde analyse du même repas (ex: si l'utilisateur modifie une quantité)

        self.assertEqual(
            Alerte.objects.filter(utilisateur=u, regle__identifiant="R01", statut="active").count(), 1
        )

    def test_alerte_generee_par_repas_distinct_meme_si_meme_regle(self):
        """La dé-duplication est par repas, pas globale : deux repas différents contenant
        le même allergène doivent chacun déclencher leur propre alerte R01 (chaque repas
        à risque doit être signalé individuellement)."""
        u = self._creer_utilisateur("deux_repas_risque")
        AllergieUtilisateur.objects.create(utilisateur=u, allergene="arachide")

        r1 = Repas.objects.create(utilisateur=u, date=date.today(), heure=time(12, 0), type_repas="dejeuner")
        RepasAliment.objects.create(repas=r1, aliment=self.sauce_arachide, quantite_g=100)
        analyser_repas(r1)

        r2 = Repas.objects.create(utilisateur=u, date=date.today(), heure=time(19, 0), type_repas="diner")
        RepasAliment.objects.create(repas=r2, aliment=self.sauce_arachide, quantite_g=100)
        analyser_repas(r2)

        self.assertEqual(
            Alerte.objects.filter(utilisateur=u, regle__identifiant="R01", statut="active").count(), 2
        )


    def test_R13_ne_se_declenche_pas_avec_pravastatine(self):
        """Correction issue de la revue nutritionnelle : la pravastatine n'a pas
        d'interaction significative avec le pamplemousse, contrairement à la
        simvastatine — ne doit plus générer de faux positif."""
        u = self._creer_utilisateur("pravastatine_user")
        TraitementUtilisateur.objects.create(utilisateur=u, medicament="Pravastatine")
        pamplemousse = Aliment.objects.create(nom="Pamplemousse (test R13)", calories=32)

        r = Repas.objects.create(utilisateur=u, date=date.today(), heure=time(8, 0), type_repas="petit_dejeuner")
        RepasAliment.objects.create(repas=r, aliment=pamplemousse, quantite_g=150)

        alertes = analyser_repas(r)
        self.assertNotIn("R13", [a.regle.identifiant for a in alertes])

    def test_R13_se_declenche_toujours_avec_simvastatine(self):
        """La simvastatine reste bien couverte après l'affinage de la liste (R13)."""
        u = self._creer_utilisateur("simvastatine_user")
        TraitementUtilisateur.objects.create(utilisateur=u, medicament="Simvastatine")
        pamplemousse = Aliment.objects.create(nom="Pamplemousse (test R13 bis)", calories=32)

        r = Repas.objects.create(utilisateur=u, date=date.today(), heure=time(8, 0), type_repas="petit_dejeuner")
        RepasAliment.objects.create(repas=r, aliment=pamplemousse, quantite_g=150)

        alertes = analyser_repas(r)
        self.assertIn("R13", [a.regle.identifiant for a in alertes])


class BesoinsCaloriquesTests(TestCase):
    """Formalise la correction du facteur d'activité dans l'estimation de R08
    (revue nutritionnelle : l'estimation sous-estimait les profils actifs)."""

    def test_facteur_activite_augmente_les_besoins_estimes(self):
        from core.moteur_analyse import _besoins_caloriques_estimes

        u = Utilisateur.objects.create_user(
            username="activite_test", password="motdepasse",
            date_naissance=date(1990, 1, 1), sexe="H",
        )

        besoins_par_niveau = {}
        for niveau in ["sedentaire", "leger", "modere", "intense"]:
            ProfilSante.objects.update_or_create(
                utilisateur=u,
                defaults=dict(taille_cm=175, poids_actuel_kg=70, niveau_activite_physique=niveau),
            )
            u_frais = Utilisateur.objects.get(pk=u.pk)  # relation profil_sante rechargée à neuf
            besoins_par_niveau[niveau] = _besoins_caloriques_estimes(u_frais)

        # Les besoins doivent croître strictement avec le niveau d'activité
        valeurs = list(besoins_par_niveau.values())
        self.assertEqual(valeurs, sorted(valeurs))
        self.assertGreater(besoins_par_niveau["intense"], besoins_par_niveau["sedentaire"])

    @classmethod
    def setUpTestData(cls):
        cls.tomate = Aliment.objects.create(
            nom="Tomate (test)", categorie="Légume", calories=18, fibres=1.2, sodium_mg=5, sucres=2.6
        )
        cls.reglisse = Aliment.objects.create(
            nom="Réglisse (test)", categorie="Confiserie", calories=340, sucres=55, sodium_mg=90
        )

    def _creer_utilisateur(self, username):
        return Utilisateur.objects.create_user(username=username, password="motdepasse")

    def test_score_alimentaire_favorable_pour_alimentation_variee(self):
        u = self._creer_utilisateur("bonne_alim")
        for i in range(5):
            r = Repas.objects.create(
                utilisateur=u, date=date.today() - timedelta(days=i), heure=time(12, 0), type_repas="dejeuner"
            )
            RepasAliment.objects.create(repas=r, aliment=self.tomate, quantite_g=100)

        score = calculer_score_alimentaire(u)
        self.assertIsNotNone(score)
        self.assertGreater(score.valeur, 50)

    def test_score_alimentaire_defavorable_pour_aliment_sucre_unique(self):
        u = self._creer_utilisateur("mauvaise_alim")
        r = Repas.objects.create(utilisateur=u, date=date.today(), heure=time(16, 0), type_repas="collation")
        RepasAliment.objects.create(repas=r, aliment=self.reglisse, quantite_g=200)

        score = calculer_score_alimentaire(u)
        self.assertIsNotNone(score)
        self.assertLess(score.valeur, 60)

    def test_indice_fiabilite_bas_si_saisie_incomplete(self):
        u = self._creer_utilisateur("saisie_rare")
        r = Repas.objects.create(utilisateur=u, date=date.today(), heure=time(12, 0), type_repas="dejeuner")
        RepasAliment.objects.create(repas=r, aliment=self.tomate, quantite_g=100)

        score = calculer_indice_fiabilite(u)
        self.assertIsNotNone(score)
        self.assertLess(score.valeur, 50)

    def test_indice_fiabilite_eleve_si_saisie_reguliere(self):
        u = self._creer_utilisateur("saisie_reguliere")
        for i in range(7):
            for heure, type_repas in [(time(8, 0), "petit_dejeuner"), (time(12, 30), "dejeuner"), (time(19, 0), "diner")]:
                r = Repas.objects.create(
                    utilisateur=u, date=date.today() - timedelta(days=i), heure=heure, type_repas=type_repas
                )
                RepasAliment.objects.create(repas=r, aliment=self.tomate, quantite_g=100)

        score = calculer_indice_fiabilite(u)
        self.assertIsNotNone(score)
        self.assertGreaterEqual(score.valeur, 70)

    def test_aucun_score_sans_historique(self):
        u = self._creer_utilisateur("sans_historique")
        self.assertIsNone(calculer_score_alimentaire(u))
        self.assertIsNone(calculer_indice_fiabilite(u))


class EcransTests(TestCase):
    """Vérifie le parcours utilisateur complet via les vraies routes HTTP."""

    @classmethod
    def setUpTestData(cls):
        _charger_regles_de_test()
        cls.sauce_arachide = Aliment.objects.create(
            nom="Sauce arachide écran (test)", allergenes="arachide", calories=250, sodium_mg=400
        )

    def test_inscription_cree_compte_et_profil_sante(self):
        resp = self.client.post(reverse("inscription"), {
            "username": "nouvel_utilisateur",
            "email": "nu@test.com",
            "password1": "MotDePasse#2026",
            "password2": "MotDePasse#2026",
            "consentement_donnees_sante": "on",
        })
        self.assertEqual(resp.status_code, 302)
        u = Utilisateur.objects.get(username="nouvel_utilisateur")
        self.assertTrue(ProfilSante.objects.filter(utilisateur=u).exists())

    def test_parcours_complet_allergie_puis_repas_declenche_alerte(self):
        self.client.post(reverse("inscription"), {
            "username": "parcours_complet",
            "email": "pc@test.com",
            "password1": "MotDePasse#2026",
            "password2": "MotDePasse#2026",
            "consentement_donnees_sante": "on",
        })

        # Déclarer l'allergie via l'écran dédié (pas via /admin/)
        self.client.post(reverse("informations_medicales"), {
            "formulaire": "allergie", "allergene": "arachide", "gravite": "",
        })

        # Ajouter un repas multi-aliments contenant l'allergène
        data = {
            "date": str(date.today()), "heure": "12:30", "type_repas": "dejeuner", "commentaire": "",
            "aliments-TOTAL_FORMS": "8", "aliments-INITIAL_FORMS": "0",
            "aliments-MIN_NUM_FORMS": "0", "aliments-MAX_NUM_FORMS": "1000",
            "aliments-0-aliment": str(self.sauce_arachide.id), "aliments-0-quantite_g": "100",
        }
        for i in range(1, 8):
            data[f"aliments-{i}-aliment"] = ""
            data[f"aliments-{i}-quantite_g"] = ""
        resp = self.client.post(reverse("ajouter_repas"), data, follow=True)

        u = Utilisateur.objects.get(username="parcours_complet")
        self.assertTrue(Alerte.objects.filter(utilisateur=u, regle__identifiant="R01").exists())

        # Le tableau de bord doit afficher l'alerte et un score
        resp = self.client.get(reverse("tableau_bord"))
        self.assertEqual(resp.status_code, 200)
        self.assertGreater(len(resp.context["alertes_actives"]), 0)

    def test_ajout_repas_sans_aucun_aliment_est_refuse(self):
        self.client.post(reverse("inscription"), {
            "username": "repas_vide",
            "email": "rv@test.com",
            "password1": "MotDePasse#2026",
            "password2": "MotDePasse#2026",
            "consentement_donnees_sante": "on",
        })
        data = {
            "date": str(date.today()), "heure": "13:00", "type_repas": "collation", "commentaire": "",
            "aliments-TOTAL_FORMS": "8", "aliments-INITIAL_FORMS": "0",
            "aliments-MIN_NUM_FORMS": "0", "aliments-MAX_NUM_FORMS": "1000",
        }
        for i in range(8):
            data[f"aliments-{i}-aliment"] = ""
            data[f"aliments-{i}-quantite_g"] = ""

        resp = self.client.post(reverse("ajouter_repas"), data)
        self.assertEqual(resp.status_code, 200)  # pas de redirection = pas d'enregistrement
        self.assertEqual(Repas.objects.filter(type_repas="collation").count(), 0)

    def test_page_connexion_accessible_sans_authentification(self):
        resp = self.client.get(reverse("connexion"))
        self.assertEqual(resp.status_code, 200)

    def test_tableau_de_bord_redirige_si_non_connecte(self):
        resp = self.client.get(reverse("tableau_bord"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("connexion"), resp.url)


class GestionCompteTests(TestCase):
    """Réinitialisation de mot de passe, modification des informations médicales,
    suppression de compte (Chapitre 3.1)."""

    def test_reinitialisation_mot_de_passe_parcours_complet(self):
        import re
        from django.core import mail

        u = Utilisateur.objects.create_user(
            username="oublie_mdp", email="oublie@test.com", password="AncienMdp#2026"
        )

        resp = self.client.post(reverse("mot_de_passe_reinitialiser"), {"email": "oublie@test.com"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)

        lien = re.search(r"(/mot-de-passe/reinitialiser/confirmer/\S+)", mail.outbox[0].body).group(1)
        resp = self.client.get(lien, follow=True)
        url_finale = resp.redirect_chain[-1][0] if resp.redirect_chain else lien

        resp = self.client.post(url_finale, {
            "new_password1": "NouveauMdp#2026!", "new_password2": "NouveauMdp#2026!",
        })
        self.assertEqual(resp.status_code, 302)

        u.refresh_from_db()
        self.assertFalse(u.check_password("AncienMdp#2026"))
        self.assertTrue(u.check_password("NouveauMdp#2026!"))

    def test_modification_allergie(self):
        u = Utilisateur.objects.create_user(username="modif_allergie", password="motdepasse")
        allergie = AllergieUtilisateur.objects.create(utilisateur=u, allergene="arachide")
        self.client.login(username="modif_allergie", password="motdepasse")

        self.client.post(reverse("modifier_allergie", args=[allergie.id]), {
            "allergene": "arachide", "gravite": "sévère",
        })
        allergie.refresh_from_db()
        self.assertEqual(allergie.gravite, "sévère")

    def test_suppression_compte_refusee_avec_mauvais_mot_de_passe(self):
        u = Utilisateur.objects.create_user(username="suppr_ko", password="BonMdp#2026")
        self.client.login(username="suppr_ko", password="BonMdp#2026")

        self.client.post(reverse("supprimer_compte"), {"mot_de_passe": "MauvaisMotDePasse"})
        self.assertTrue(Utilisateur.objects.filter(username="suppr_ko").exists())

    def test_suppression_compte_reussit_avec_bon_mot_de_passe_et_efface_les_donnees_liees(self):
        u = Utilisateur.objects.create_user(username="suppr_ok", password="BonMdp#2026")
        AllergieUtilisateur.objects.create(utilisateur=u, allergene="arachide")
        self.client.login(username="suppr_ok", password="BonMdp#2026")

        self.client.post(reverse("supprimer_compte"), {"mot_de_passe": "BonMdp#2026"})
        self.assertFalse(Utilisateur.objects.filter(username="suppr_ok").exists())
        self.assertFalse(AllergieUtilisateur.objects.filter(allergene="arachide", utilisateur_id=u.id).exists())


class HistoriqueEtRechercheTests(TestCase):
    """Filtres de période sur l'historique (Chapitre 7.6) et recherche d'aliment
    par autocomplétion (remplace le menu déroulant simple)."""

    def test_filtre_historique_par_periode(self):
        u = Utilisateur.objects.create_user(username="filtre_histo", password="motdepasse")
        Repas.objects.create(utilisateur=u, date=date.today() - timedelta(days=40), heure=time(12, 0), type_repas="dejeuner")
        Repas.objects.create(utilisateur=u, date=date.today() - timedelta(days=1), heure=time(12, 0), type_repas="dejeuner")
        Repas.objects.create(utilisateur=u, date=date.today(), heure=time(12, 0), type_repas="dejeuner")

        self.client.login(username="filtre_histo", password="motdepasse")

        resp = self.client.get(reverse("historique"), {"periode": "jour"})
        self.assertEqual(resp.context["repas"].count(), 1)

        resp = self.client.get(reverse("historique"), {"periode": "semaine"})
        self.assertEqual(resp.context["repas"].count(), 2)

        resp = self.client.get(reverse("historique"), {"periode": "annee"})
        self.assertEqual(resp.context["repas"].count(), 3)

    def test_recherche_aliment_trouve_par_nom_partiel(self):
        u = Utilisateur.objects.create_user(username="recherche_user", password="motdepasse")
        Aliment.objects.create(nom="Igname bouillie (test recherche)", calories=118)
        self.client.login(username="recherche_user", password="motdepasse")

        resp = self.client.get(reverse("rechercher_aliment"), {"q": "igna"})
        noms = [r["nom"] for r in resp.json()["resultats"]]
        self.assertIn("Igname bouillie (test recherche)", noms)

    def test_recherche_aliment_ignore_requete_trop_courte(self):
        u = Utilisateur.objects.create_user(username="recherche_courte", password="motdepasse")
        self.client.login(username="recherche_courte", password="motdepasse")

        resp = self.client.get(reverse("rechercher_aliment"), {"q": "a"})
        self.assertEqual(resp.json()["resultats"], [])
