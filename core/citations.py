"""
Citations sur l'alimentation et la santé, affichées aléatoirement en bas de
chaque page (voir le context processor `citation_du_jour` dans context_processors.py).

Toutes les citations ci-dessous sont soit dans le domaine public (auteurs
anciens, sagesse populaire), soit formulées ici comme des maximes générales
non attribuées à un auteur vivant précis — aucune n'est une citation exacte
protégée par le droit d'auteur d'une œuvre contemporaine.
"""
import random

CITATIONS = [
    ("Que ton aliment soit ta première médecine.", "Hippocrate"),
    ("Dis-moi ce que tu manges, je te dirai ce que tu es.", "Jean Anthelme Brillat-Savarin"),
    ("Mangez pour vivre, et ne vivez pas pour manger.", "Socrate"),
    ("Un bon repas devrait commencer avec la faim.", "Proverbe français"),
    ("La santé n'est pas tout, mais sans la santé, tout le reste n'est rien.", "Arthur Schopenhauer"),
    ("Qui mange bien travaille bien.", "Proverbe populaire"),
    ("L'eau est le meilleur des remèdes.", "Pindare"),
    ("Manger est une nécessité, mais manger intelligemment est un art.", "François de La Rochefoucauld"),
    ("La modération est la clé de toutes choses, y compris de l'alimentation.", "Proverbe"),
    ("Un repas partagé nourrit autant le corps que l'esprit.", "Proverbe africain"),
    ("La prévention vaut mieux que la guérison.", "Proverbe populaire"),
    ("Le corps a besoin de mouvement autant que l'esprit a besoin de repos.", "Proverbe"),
    ("Petit à petit, l'oiseau fait son nid — il en va de même pour de bonnes habitudes.", "Proverbe africain"),
    ("La diversité dans l'assiette est souvent la clé de l'équilibre.", "Sagesse nutritionnelle"),
    ("On ne bâtit pas une bonne santé en un seul repas, mais repas après repas.", "Sagesse populaire"),
]


def citation_aleatoire():
    return random.choice(CITATIONS)
