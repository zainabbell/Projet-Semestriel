"""Module simulation.py
Gère le moteur de simulation, l'avancement des ticks et l'agrégation des résultats.
"""

from typing import Any, Callable, Optional
from ascenseur import Ascenseur
from immeuble import Immeuble
from strategies import Strategie
from statistiques import calculer_statistiques


def lancer(
    strategie: Strategie,
    appels: dict[int, list[tuple[int, str]]],
    duree: int = 100,
    nb_etages: int = 10,
    etage_initial: int = 0,
    callback_tick: Optional[Callable[[int, Ascenseur, list[dict[str, Any]]], None]] = None,
    mode_comparaison: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]], Ascenseur]:
    """Exécute une simulation complète avec la stratégie et la suite d'appels fournies.

    :param strategie: Instance de Strategie (LOOK ou FCFS).
    :param appels: Dictionnaire {tick: [(etage, source), ...]}.
    :param duree: Durée de base de la simulation en ticks.
    :param nb_etages: Nombre d'étages de l'immeuble.
    :param etage_initial: Étage de départ de l'ascenseur.
    :param callback_tick: Fonction appelée à chaque tick (ex: pour mise à jour UI).
    :param mode_comparaison: Si True, applique RG10 (continue après `duree` jusqu'à vider `liste_appels`).
    :return: (statistiques_dict, liste_evenements, ascenseur)
    """
    immeuble = Immeuble(nb_etages)
    ascenseur = Ascenseur(immeuble=immeuble, etage_initial=etage_initial, strategie=strategie)
    tous_evenements: list[dict[str, Any]] = []

    tick = 1
    limite_securite = duree + 5000  # Empêche toute boucle infinie théorique

    while True:
        # En mode normal, arrêt strict à DUREE_SIMULATION
        if not mode_comparaison and tick > duree:
            break

        # En mode comparaison (RG10) :
        # Au-delà de duree, aucun nouvel appel n'est injecté. On continue jusqu'à ce que liste_appels
        # soit vide et que la porte soit refermée.
        if mode_comparaison and tick > duree:
            if not ascenseur.liste_appels and not ascenseur.porte_ouverte:
                break
            if tick > limite_securite:
                break

        nouveaux_appels = appels.get(tick, []) if tick <= duree else []
        evts = ascenseur.pas(tick, nouveaux_appels)
        tous_evenements.extend(evts)

        if callback_tick:
            callback_tick(tick, ascenseur, evts)

        tick += 1

    ticks_totaux = tick - 1
    stats = calculer_statistiques(
        attentes=ascenseur.attentes,
        ticks_actifs=ascenseur.ticks_actifs,
        ticks_totaux=ticks_totaux,
        nb_servis=ascenseur.nb_servis,
        nb_deplacements=ascenseur.nb_deplacements,
    )
    stats["duree_totale"] = ticks_totaux
    stats["appels_non_servis"] = len(ascenseur.liste_appels)

    return stats, tous_evenements, ascenseur
