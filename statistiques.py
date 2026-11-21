"""Module statistiques.py
Définit les fonctions de calcul et de formatage des métriques d'évaluation (Section 11).
"""

from typing import Any


def calculer_statistiques(
    attentes: list[int],
    ticks_actifs: int,
    ticks_totaux: int,
    nb_servis: int,
    nb_deplacements: int,
) -> dict[str, Any]:
    """Calcule les indicateurs statistiques d'une simulation selon la section 11.

    :param attentes: Liste des temps d'attente observés pour chaque appel servi.
    :param ticks_actifs: Nombre de ticks où la cabine n'était pas 'Au repos'.
    :param ticks_totaux: Nombre total de ticks simulés.
    :param nb_servis: Nombre total d'appels servis (ouvertures de porte).
    :param nb_deplacements: Nombre d'étages parcourus.
    :return: Dictionnaire contenant les statistiques calculées.
    """
    if nb_servis > 0 and len(attentes) > 0:
        attente_moyenne = sum(attentes) / len(attentes)
        attente_max = max(attentes)
    else:
        attente_moyenne = 0.0
        attente_max = 0

    if ticks_totaux > 0:
        taux_occupation = (ticks_actifs / ticks_totaux) * 100.0
    else:
        taux_occupation = 0.0

    return {
        "appels_servis": nb_servis,
        "attente_moyenne": round(attente_moyenne, 2),
        "attente_max": attente_max,
        "deplacements": nb_deplacements,
        "taux_occupation": round(taux_occupation, 1),
    }


def formater_statistiques(stats: dict[str, Any]) -> str:
    """Retourne une chaîne lisible formatant les statistiques pour l'affichage console ou graphique."""
    return (
        f"Appels servis : {stats.get('appels_servis', 0)} | "
        f"Attente moy : {stats.get('attente_moyenne', 0.0):.2f} s | "
        f"Attente max : {stats.get('attente_max', 0)} s | "
        f"Déplacements : {stats.get('deplacements', 0)} étages | "
        f"Taux d'activité : {stats.get('taux_occupation', 0.0):.1f} %"
    )
