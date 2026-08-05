from .citations import citation_aleatoire


def citation_du_jour(request):
    """Rend une citation sur l'alimentation/la santé disponible dans tous les
    templates, sans que chaque vue ait à la passer explicitement."""
    texte, auteur = citation_aleatoire()
    return {"citation_texte": texte, "citation_auteur": auteur}
