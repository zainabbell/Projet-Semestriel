"""Module comparaison.py
Automatise l'exécution comparative des stratégies LOOK et FCFS
sur plusieurs graines aléatoires et scénarios de trafic (RG11, EF12, EF13).
"""

from typing import Any, Callable, Optional
from strategies import LOOK, FCFS
from scenarios import obtenir_scenario, generer_suite_appels
from simulation import lancer


def executer_comparaison(
    nb_graines: int = 20,
    duree: int = 300,
    nb_etages: int = 10,
    scenarios_noms: Optional[list[str]] = None,
    callback_progression: Optional[Callable[[int, int, str], None]] = None,
) -> dict[str, Any]:
    """Lance la comparaison complète LOOK vs FCFS selon RG11.

    Pour chaque scénario et pour chaque graine, la suite d'appels est générée
    une seule fois et rejouée rigoureusement à l'identique pour LOOK et FCFS.

    :param nb_graines: Nombre de graines aléatoires (défaut 20).
    :param duree: Durée de la simulation en ticks (défaut 300).
    :param nb_etages: Nombre d'étages de l'immeuble.
    :param scenarios_noms: Liste des noms de scénarios (défaut ['matin', 'midi', 'nuit']).
    :param callback_progression: Fonction appelée (étape_actuelle, total_étapes, message).
    :return: Dictionnaire contenant les moyennes par (scénario, stratégie) et les données brutes.
    """
    if scenarios_noms is None:
        scenarios_noms = ["matin", "midi", "nuit"]

    total_etapes = len(scenarios_noms) * nb_graines * 2
    etape_courante = 0

    # Structure pour accumuler les résultats
    # resultats[scenario][strategie] = list of stat dicts
    resultats_bruts: dict[str, dict[str, list[dict[str, Any]]]] = {
        sc: {"LOOK": [], "FCFS": []} for sc in scenarios_noms
    }

    # Liste de graines reproductibles
    graines = [1000 + i for i in range(nb_graines)]

    for sc_nom in scenarios_noms:
        sc = obtenir_scenario(sc_nom)

        for g in graines:
            # RG11 : Suite d'appels générée une seule fois à l'avance
            appels = generer_suite_appels(
                scenario=sc,
                nb_etages=nb_etages,
                duree=duree,
                graine=g,
            )

            # Simulation LOOK
            stats_look, _, _ = lancer(
                strategie=LOOK(),
                appels=appels,
                duree=duree,
                nb_etages=nb_etages,
                mode_comparaison=True,
            )
            resultats_bruts[sc_nom]["LOOK"].append(stats_look)
            etape_courante += 1
            if callback_progression:
                callback_progression(
                    etape_courante,
                    total_etapes,
                    f"Scénario {sc_nom.capitalize()} | Graine {g} | LOOK terminé",
                )

            # Simulation FCFS (même suite d'appels)
            stats_fcfs, _, _ = lancer(
                strategie=FCFS(),
                appels=appels,
                duree=duree,
                nb_etages=nb_etages,
                mode_comparaison=True,
            )
            resultats_bruts[sc_nom]["FCFS"].append(stats_fcfs)
            etape_courante += 1
            if callback_progression:
                callback_progression(
                    etape_courante,
                    total_etapes,
                    f"Scénario {sc_nom.capitalize()} | Graine {g} | FCFS terminé",
                )

    # Calcul des moyennes
    synthese: dict[str, dict[str, dict[str, float]]] = {}

    for sc_nom in scenarios_noms:
        synthese[sc_nom] = {}
        for strat in ["LOOK", "FCFS"]:
            stats_list = resultats_bruts[sc_nom][strat]
            n = len(stats_list)
            if n > 0:
                moy_attente = sum(s["attente_moyenne"] for s in stats_list) / n
                moy_deplacements = sum(s["deplacements"] for s in stats_list) / n
                moy_servis = sum(s["appels_servis"] for s in stats_list) / n
                moy_occupation = sum(s["taux_occupation"] for s in stats_list) / n
                moy_attente_max = sum(s["attente_max"] for s in stats_list) / n
            else:
                moy_attente = moy_deplacements = moy_servis = moy_occupation = moy_attente_max = 0.0

            synthese[sc_nom][strat] = {
                "attente_moyenne": round(moy_attente, 2),
                "deplacements": round(moy_deplacements, 1),
                "appels_servis": round(moy_servis, 1),
                "taux_occupation": round(moy_occupation, 1),
                "attente_max": round(moy_attente_max, 1),
            }

    return {
        "synthese": synthese,
        "resultats_bruts": resultats_bruts,
        "scenarios": scenarios_noms,
        "nb_graines": nb_graines,
        "duree": duree,
    }
