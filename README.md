# SIENSS — Squelette technique V1 (MVP)

Système Intelligent d'Évaluation Nutritionnelle et de Suivi Santé.
Squelette Django correspondant au périmètre défini au Chapitre 8 (V1/MVP)
du cahier des charges.

## Ce qui est déjà en place

- **Modèles** (`core/models.py`) : Utilisateur, ProfilSante, Allergies/Pathologies/Traitements,
  Aliment, Repas/RepasAliment, RegleNutritionnelle, Alerte, Score — correspondant au Chapitre 5.
- **Admin Django** (`core/admin.py`) : interface de gestion prête à l'emploi (aliments, règles, alertes).
- **Moteur d'analyse** (`core/moteur_analyse.py`) : les **18 règles R01 à R18** sont implémentées
  (voir les limites assumées documentées en en-tête du fichier — seuils et interactions
  médicamenteuses à valider par un(e) professionnel(le) avant production).
- **Commande `charger_regles`** : pré-charge les 18 règles définies (statut "brouillon").
- **Écrans fonctionnels** (`core/views.py`, `core/forms.py`, `core/templates/core/`) :
  inscription, connexion/déconnexion, profil de santé, **informations médicales**
  (allergies/pathologies/traitements — ajout et suppression), tableau de bord (alertes actives,
  IMC, compteurs), **ajout de repas multi-aliments** (formset, analyse automatique), historique.
- Testé de bout en bout via le client de test Django : inscription → profil → déclaration
  d'allergie via l'écran → repas multi-aliments → alertes générées → tableau de bord — et via
  le vrai serveur de développement (`runserver`), pages HTTP 200 confirmées.

- **Base alimentaire de départ** (`core/data/aliments_depart.csv` + commande `importer_aliments`) :
  29 aliments réels, dont une quinzaine d'aliments béninois/ouest-africains (igname, gari, akassa,
  attiéké, banane plantain, haricot niébé/wake, sauces arachide/gombo, poisson braisé/fumé, huile
  de palme rouge...). Testé avec un scénario réel diabète + gari → alertes R09/R10 correctement
  déclenchées.
- **Calcul des scores** (`core/scores.py`) : score alimentaire (diversité, fruits/légumes, fibres,
  sodium, sucres, graisses saturées sur 7 jours glissants) et indice de fiabilité de l'analyse
  (complétude de la saisie, fréquence des repas, qualité des données alimentaires utilisées).
  Se déclenche automatiquement à chaque ajout de repas et s'affiche sur le tableau de bord.
- **Gestion de compte complète** (Chapitre 3.1) : réinitialisation de mot de passe par e-mail
  (console en développement, SMTP configurable en production via variables d'environnement),
  modification des allergies/pathologies/traitements (plus seulement ajout/suppression), et
  suppression de compte avec confirmation par mot de passe (efface aussi les données liées en
  cascade). Testé de bout en bout : réinitialisation complète du mot de passe jusqu'à connexion
  avec le nouveau, suppression refusée avec mauvais mot de passe puis acceptée avec le bon.
- **Tests automatisés** (`core/tests.py`, 29 tests, tous verts) : moteur de règles (R01, R09, R12,
  R14, R17, dé-duplication), scores (favorable/défavorable, absence d'historique), écrans
  (inscription, parcours complet, refus d'un repas vide, redirections d'authentification).
  Lancer avec `python manage.py test core`.

### Comportement important révélé par les tests
La dé-duplication des alertes se fait **par repas, pas globalement** : si un utilisateur mange
deux fois dans la journée un aliment auquel il est allergique, il reçoit une alerte R01 pour
*chaque* repas concerné (comportement volontaire — chaque repas à risque doit être signalé
individuellement), et non une seule alerte au niveau du compte. Voir
`test_alerte_generee_par_repas_distinct_meme_si_meme_regle` dans `core/tests.py`.

## Revue nutritionnelle et corrections apportées

Une revue basée sur les connaissances nutritionnelles et pharmacologiques générales établies
(voir `avis-validation-nutritionnelle-SIENSS.md`) a permis d'identifier et corriger :

- **R08** : l'estimation calorique intègre désormais le facteur d'activité physique du profil
  (sédentaire à intense), corrigeant une sous-estimation systématique pour les profils actifs.
- **R13** : la liste de médicaments a été affinée pour ne cibler que les molécules à interaction
  forte documentée avec le pamplemousse (simvastatine, atorvastatine, lovastatine, félodipine,
  nifédipine, amlodipine) — la pravastatine et la rosuvastatine, peu concernées, ne déclenchent
  plus de fausse alerte. Testé : `test_R13_ne_se_declenche_pas_avec_pravastatine` /
  `test_R13_se_declenche_toujours_avec_simvastatine`.
- **Base alimentaire** : le "Gari" a été scindé en deux entrées distinctes — "Gari sec (semoule)"
  et "Eba (gari réhydraté)" — car les valeurs nutritionnelles diffèrent radicalement selon que
  l'utilisateur consomme le produit sec ou réhydraté. Le sodium du poisson fumé a été révisé à
  la hausse (900→1200mg/100g) pour mieux refléter la fourchette réelle selon le procédé de
  salage/fumage.

⚠️ **Cette revue ne remplace pas une validation clinique par un professionnel de santé inscrit
à l'ordre.** Les règles R13-R16 (interactions médicamenteuses, insuffisance rénale) nécessitent
impérativement une validation par un pharmacien et/ou un néphrologue avant toute mise en
production — voir le document de revue pour le détail des points à faire vérifier en priorité.

### Important à propos des données nutritionnelles béninoises
Beaucoup d'aliments locaux sont marqués `niveau_confiance="faible"` avec la source "Estimation à
valider" — ce sont des valeurs approximatives que j'ai établies à partir de connaissances
nutritionnelles générales, **pas d'une table de composition alimentaire officielle**. Avant toute
mise en production, il est essentiel de les faire vérifier/corriger par un(e) diététicien(ne) ou
de les recouper avec une vraie table de composition (ex. table FAO/INFOODS Afrique de l'Ouest,
si vous y avez accès). Les aliments internationaux (riz, pain, lait...) ont un niveau de confiance
plus élevé, basés sur des tables de composition génériques bien établies.

### Importer un export Open Food Facts (à faire chez vous)
Cet environnement n'a pas accès à openfoodfacts.org (réseau restreint). La commande
`importer_aliments` est générique et lit un CSV avec le mapping de colonnes documenté en en-tête
du fichier `core/management/commands/importer_aliments.py` — adaptez-le à un export OFF téléchargé
depuis https://world.openfoodfacts.org/data. Attention : OFF couvre mal les aliments locaux
béninois/africains, d'où l'intérêt de garder et compléter le fichier `aliments_depart.csv`.

### Ce qui reste à faire côté écrans
- Édition d'une allergie/pathologie/traitement existant (seuls l'ajout et la suppression sont
  disponibles pour l'instant)
- Écran de recherche d'aliment plus ergonomique (actuellement un simple menu déroulant — à
  terme, une recherche avec autocomplétion sera nécessaire maintenant que la base grandit)

## Démarrer en local

```bash
pip install -r requirements.txt --break-system-packages   # ou dans un venv, sans ce flag
cd sienss
python manage.py migrate
python manage.py charger_regles
python manage.py importer_aliments
python manage.py createsuperuser             # pour accéder à /admin/
python manage.py runserver
```

Puis ouvrir :
- http://127.0.0.1:8000/inscription/ pour créer un compte et tester le parcours complet
- http://127.0.0.1:8000/admin/ pour gérer aliments, règles, et déclarer allergies/pathologies/traitements

`ALLOWED_HOSTS` est déjà configuré pour `localhost`/`127.0.0.1` — pas de réglage supplémentaire nécessaire en développement local.

## Tester le moteur d'analyse

```bash
python manage.py shell
```
```python
from core.models import Utilisateur, Aliment, Repas, RepasAliment
from core.moteur_analyse import analyser_repas
# ... créer un utilisateur, un aliment, un repas, puis :
analyser_repas(mon_repas)
```

## Prochaines étapes de développement (dans l'ordre)

1. ~~Compléter le moteur (R01-R18)~~ ✅ fait
2. ~~Premiers écrans (inscription, profil, repas, tableau de bord)~~ ✅ fait
3. ~~Formulaire de repas multi-aliments~~ ✅ fait
4. ~~Écran de déclaration des allergies/pathologies/traitements~~ ✅ fait
5. ~~Base alimentaire de départ (29 aliments dont béninois)~~ ✅ fait — à enrichir en continu
6. ~~Calcul des scores (alimentaire + indice de fiabilité)~~ ✅ fait
7. **Validation scientifique** : faire relire les 18 règles, les seuils des scores, ET les valeurs
   nutritionnelles des aliments béninois (`niveau_confiance="faible"`) par un(e) diététicien(ne)
   avant de passer leur statut en production.
8. ~~Tests automatisés~~ ✅ fait — 29 tests, tous verts (`python manage.py test core`)
9. ~~Réinitialisation de mot de passe et suppression de compte~~ ✅ fait
10. ~~Édition des allergies/pathologies/traitements~~ ✅ fait
11. ~~Filtres de l'historique par période~~ ✅ fait (jour/7 jours/30 jours/1 an)
12. ~~Recherche d'aliment avec autocomplétion~~ ✅ fait (endpoint JSON + JavaScript, remplace le
    menu déroulant simple — testé avec la base de 27 aliments existante)

## Périmètre V1 — complet

Toutes les fonctionnalités prévues au cahier des charges pour la V1 sont maintenant construites
et testées (29 tests automatisés). Il ne reste plus que des étapes hors développement logiciel :
validation professionnelle des règles/données, et déploiement réel.

## Périmètre V1 (MVP) — état d'avancement

Toutes les briques techniques prévues au Chapitre 8 pour la V1 sont maintenant en place et
testées : modèles, moteur de règles complet (18/18), écrans de base, base alimentaire de départ,
scores, tests automatisés. Les étapes suivantes ne sont plus du développement de fonctionnalités
mais de la **mise en conditions réelles** :

- faire valider les règles et les données alimentaires par un(e) diététicien(ne) (étape 7 ci-dessus)
- passer à PostgreSQL (voir section dédiée plus bas)
- déployer sur un hébergement de test et faire essayer l'application par un petit groupe
  d'utilisateurs réels — c'est le critère de passage à la V2 défini au Chapitre 8.6

## Déployer en production

Le projet est prêt pour un déploiement type Railway/Render (recommandé au Chapitre 9) : les
réglages basculent automatiquement entre développement et production selon les variables
d'environnement présentes, sans rien changer au code.

**Ce qui a été réellement testé dans cet environnement de développement :**
- `DEBUG=False` avec les réglages de sécurité HTTPS activés (`python manage.py check --deploy`)
- Parsing d'une URL `DATABASE_URL` PostgreSQL (format Railway/Render)
- Collecte des fichiers statiques (`collectstatic`) avec WhiteNoise
- Démarrage réel du serveur Gunicorn en mode production (réponses HTTP 200 confirmées)

**Ce qui n'a pas pu être testé ici** (PostgreSQL n'a pas pu s'installer dans cet environnement
bac à sable) : la connexion et les migrations sur une vraie base PostgreSQL. À vérifier chez vous
en premier lors du déploiement — c'est l'étape la plus susceptible de révéler un problème.

### Étapes de déploiement (Railway ou Render)

1. Créer un compte et un nouveau projet sur Railway ou Render
2. Connecter votre dépôt Git — le projet est déjà initialisé en local avec un premier commit
   (voir `sienss-repo.bundle` fourni). Pour le récupérer chez vous :
   ```bash
   git clone sienss-repo.bundle sienss
   cd sienss
   git remote add origin https://github.com/<votre-compte>/sienss.git
   git push -u origin main
   ```
   Créez d'abord un dépôt vide sur GitHub (sans README ni .gitignore, pour éviter un conflit),
   puis remplacez l'URL ci-dessus par la vôtre.
3. Ajouter une base de données PostgreSQL depuis l'interface de l'hébergeur — il vous fournira
   automatiquement une variable `DATABASE_URL`
4. Définir les variables d'environnement (voir `.env.example`) : `SECRET_KEY` (générez une vraie
   valeur aléatoire), `DEBUG=False`, `ALLOWED_HOSTS` (votre nom de domaine)
5. L'hébergeur détecte `requirements.txt` et `Procfile` automatiquement et lance :
   `migrate` → `collectstatic` → `gunicorn` (déjà configuré dans le `Procfile`)
6. Une fois déployé, se connecter en SSH/shell distant pour créer un compte administrateur :
   `python manage.py createsuperuser`, puis charger les règles et la base alimentaire :
   `python manage.py charger_regles && python manage.py importer_aliments`

### Générer une vraie SECRET_KEY

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

## Rappel de sécurité

Les tables contiennent des données de santé sensibles (allergies, pathologies, traitements).
La configuration de production (`DEBUG=False` + variables d'environnement, voir section
déploiement ci-dessus) active déjà automatiquement HTTPS obligatoire et les cookies sécurisés.
Il reste à votre charge de :
- générer une vraie `SECRET_KEY` (commande fournie ci-dessus) et ne jamais la committer
- chiffrer les sauvegardes de base de données
- restreindre l'accès à `/admin/` (identifiants forts, authentification à deux facteurs recommandée en V3)
