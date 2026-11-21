"""Module strategies.py
Définit les stratégies de desserte des appels par l'ascenseur (LOOK et FCFS).
Respecte l'exigence ENF1 (aucun print ni appel Tkinter).
"""

from abc import ABC, abstractmethod


class Strategie(ABC):
    """Classe de base abstraite pour les stratégies de service de l'ascenseur."""

    @abstractmethod
    def doit_s_arreter(self, etage_actuel: int, liste_appels: list[int]) -> bool:
        """Détermine si l'ascenseur doit s'arrêter à l'étage actuel.

        :param etage_actuel: Étage où se trouve l'ascenseur.
        :param liste_appels: Liste des étages demandés (en attente).
        :return: True si l'ascenseur doit marquer un arrêt, False sinon.
        """
        pass

    @abstractmethod
    def choisir_direction(
        self, etage_actuel: int, direction: str, liste_appels: list[int]
    ) -> str:
        """Détermine la prochaine direction de déplacement de l'ascenseur.

        :param etage_actuel: Étage où se trouve l'ascenseur.
        :param direction: Direction actuelle ('monte', 'descend', 'arrêt').
        :param liste_appels: Liste des étages demandés (en attente).
        :return: 'monte', 'descend' ou 'arrêt'.
        """
        pass


class LOOK(Strategie):
    """Stratégie LOOK (balayage d'ascenseur).

    Règles RG4 et RG5 :
    - En montée, continue tant qu'un appel existe au-dessus, sinon inverse s'il en existe en dessous.
    - En descente, continue tant qu'un appel existe en dessous, sinon inverse s'il en existe au-dessus.
    - S'arrête à tout étage présent dans liste_appels.
    - À l'arrêt avec des appels : va vers l'appel le plus proche (égalité : étage le plus bas).
    """

    @property
    def nom(self) -> str:
        return "LOOK"

    def doit_s_arreter(self, etage_actuel: int, liste_appels: list[int]) -> bool:
        """LOOK s'arrête à tout étage qui est actuellement demandé."""
        return etage_actuel in liste_appels

    def choisir_direction(
        self, etage_actuel: int, direction: str, liste_appels: list[int]
    ) -> str:
        """Détermine la direction selon l'algorithme LOOK (RG4 et RG5)."""
        if not liste_appels:
            return "arrêt"

        appels_au_dessus = [e for e in liste_appels if e > etage_actuel]
        appels_en_dessous = [e for e in liste_appels if e < etage_actuel]

        # Si l'ascenseur est déjà en train de monter
        if direction == "monte":
            if appels_au_dessus:
                return "monte"
            elif appels_en_dessous:
                return "descend"
            else:
                return "arrêt"

        # Si l'ascenseur est déjà en train de descendre
        elif direction == "descend":
            if appels_en_dessous:
                return "descend"
            elif appels_au_dessus:
                return "monte"
            else:
                return "arrêt"

        # Si l'ascenseur est à l'arrêt (RG5)
        else:
            # Vers l'appel le plus proche (en cas d'égalité : étage le plus bas)
            cible = min(
                liste_appels,
                key=lambda e: (abs(e - etage_actuel), e)
            )
            if cible > etage_actuel:
                return "monte"
            elif cible < etage_actuel:
                return "descend"
            else:
                return "arrêt"


class FCFS(Strategie):
    """Stratégie First-Come First-Served (premier arrivé, premier servi).

    Règle RG6 :
    - La cible est le premier élément de liste_appels (l'appel le plus ancien).
    - La cabine s'y rend directement et ne s'arrête qu'à cette cible,
      même si elle traverse d'autres étages demandés.
    """

    @property
    def nom(self) -> str:
        return "FCFS"

    def doit_s_arreter(self, etage_actuel: int, liste_appels: list[int]) -> bool:
        """FCFS ne s'arrête QUE si l'étage actuel correspond au premier appel de la file."""
        return len(liste_appels) > 0 and etage_actuel == liste_appels[0]

    def choisir_direction(
        self, etage_actuel: int, direction: str, liste_appels: list[int]
    ) -> str:
        """Se dirige uniquement vers la cible la plus ancienne (liste_appels[0])."""
        if not liste_appels:
            return "arrêt"

        cible = liste_appels[0]
        if cible > etage_actuel:
            return "monte"
        elif cible < etage_actuel:
            return "descend"
        else:
            return "arrêt"
