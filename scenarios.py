"""Module scenarios.py
Définit les profils de trafic (Matin, Midi, Nuit, Personnalisé) et la génération
reproductible des séquences d'appels (RG11, EF7, ENF5).
"""

import random
from typing import Optional


class Scenario:
    """Classe de base pour un profil de trafic."""

    def __init__(self, nom: str, probabilite: float) -> None:
        """Initialise le scénario.

        :param nom: Nom du scénario.
        :param probabilite: Probabilité d'avoir un appel à chaque tick (0 <= p <= 1).
        """
        self.nom = nom
        self.probabilite = probabilite

    def generer_etage(self, nb_etages: int, rng: random.Random) -> int:
        """Tire un numéro d'étage selon la répartition spécifique du scénario."""
        raise NotImplementedError

    def generer_source(self, rng: random.Random) -> str:
        """Tire à égalité la source de l'appel ('interne' ou 'externe')."""
        return "interne" if rng.random() < 0.5 else "externe"


class ScenarioMatin(Scenario):
    """Scénario Matin :
    Probabilité 0.25 par tick.
    60% au rez-de-chaussée (étage 0), 40% uniforme sur les autres étages.
    """

    def __init__(self) -> None:
        super().__init__("matin", 0.25)

    def generer_etage(self, nb_etages: int, rng: random.Random) -> int:
        if nb_etages <= 1:
            return 0
        if rng.random() < 0.60:
            return 0
        else:
            return rng.randint(1, nb_etages - 1)


class ScenarioMidi(Scenario):
    """Scénario Midi :
    Probabilité 0.30 par tick.
    Répartition uniforme sur tous les étages.
    """

    def __init__(self) -> None:
        super().__init__("midi", 0.30)

    def generer_etage(self, nb_etages: int, rng: random.Random) -> int:
        return rng.randint(0, nb_etages - 1)


class ScenarioNuit(Scenario):
    """Scénario Nuit :
    Probabilité 0.05 par tick.
    Répartition uniforme sur tous les étages.
    """

    def __init__(self) -> None:
        super().__init__("nuit", 0.05)

    def generer_etage(self, nb_etages: int, rng: random.Random) -> int:
        return rng.randint(0, nb_etages - 1)


class ScenarioPersonnalise(Scenario):
    """Scénario Personnalisé :
    Probabilité configurable (défaut 0.15).
    Répartition uniforme sur tous les étages.
    """

    def __init__(self, probabilite: float = 0.15) -> None:
        proba = max(0.0, min(1.0, float(probabilite)))
        super().__init__("personnalisé", proba)

    def generer_etage(self, nb_etages: int, rng: random.Random) -> int:
        return rng.randint(0, nb_etages - 1)


def obtenir_scenario(nom: str, proba_perso: float = 0.15) -> Scenario:
    """Retourne l'instance de scénario correspondant au nom demandé."""
    nom_normalise = nom.strip().lower()
    if nom_normalise == "matin":
        return ScenarioMatin()
    elif nom_normalise == "midi":
        return ScenarioMidi()
    elif nom_normalise == "nuit":
        return ScenarioNuit()
    else:
        return ScenarioPersonnalise(proba_perso)


def generer_suite_appels(
    scenario: Scenario,
    nb_etages: int,
    duree: int,
    graine: Optional[int] = None,
) -> dict[int, list[tuple[int, str]]]:
    """Génère à l'avance la suite d'appels pour toute la durée de la simulation.

    Conforme à RG11 (Équité de comparaison) et ENF5 (Reproductibilité) :
    La suite est générée une seule fois à partir d'un générateur isolé `random.Random(graine)`.

    :param scenario: Instance de Scenario.
    :param nb_etages: Nombre d'étages de l'immeuble.
    :param duree: Durée de la simulation en ticks.
    :param graine: Graine aléatoire (facultative).
    :return: Dictionnaire mappant {tick: [(etage, source), ...]}.
    """
    rng = random.Random(graine)
    appels_par_tick: dict[int, list[tuple[int, str]]] = {t: [] for t in range(1, duree + 1)}

    for tick in range(1, duree + 1):
        if rng.random() < scenario.probabilite:
            etage = scenario.generer_etage(nb_etages, rng)
            source = scenario.generer_source(rng)
            appels_par_tick[tick].append((etage, source))

    return appels_par_tick
