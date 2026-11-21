"""Module ascenseur.py
Définit la classe Ascenseur modélisant la cabine, son état et son cycle de vie.
Respecte l'exigence ENF1 (aucun print ni appel Tkinter).
"""

from typing import Optional, Union
from strategies import Strategie, LOOK
from immeuble import Immeuble


class Ascenseur:
    """Classe représentant un ascenseur automatique.

    Gère l'état courant (étage, direction, état de la porte, liste des appels)
    et applique le cycle de simulation par tick.
    """

    def __init__(
        self,
        immeuble: Optional[Immeuble] = None,
        etage_initial: int = 0,
        strategie: Optional[Strategie] = None,
    ) -> None:
        """Initialise l'ascenseur (EF1).

        :param immeuble: Instance d'Immeuble (défaut 10 étages).
        :param etage_initial: Étage de départ (défaut 0).
        :param strategie: Stratégie de déplacement (défaut LOOK).
        """
        self.immeuble = immeuble if immeuble is not None else Immeuble(10)
        if not self.immeuble.valider_etage(etage_initial):
            raise ValueError(f"Étage initial invalide : {etage_initial}")

        self.etage_actuel: int = etage_initial
        self.direction: str = "arrêt"
        self.liste_appels: list[int] = []
        self.porte_ouverte: bool = False
        self.strategie: Strategie = strategie if strategie is not None else LOOK()

        # Dictionnaire associant chaque étage au tick où le premier appel actif a été reçu
        self.heure_appel: dict[int, int] = {}
        # File tampon pour les appels à l'étage courant devant être traités au tick suivant (RG3)
        self._appels_differes: list[int] = []

        # Métriques et statistiques internes
        self.attentes: list[int] = []
        self.ticks_actifs: int = 0
        self.nb_servis: int = 0
        self.nb_trajets: int = 0
        self.nb_arrets: int = 0
        self.nb_deplacements: int = 0

    def ajouter_appel(
        self, etage: Union[int, str], source: str = "interne", tick: int = 0
    ) -> tuple[bool, str, dict]:
        """Traite et enregistre une demande d'appel selon RG1, RG2, RG3, RG9.

        :param etage: Étage demandé.
        :param source: 'interne' ou 'externe'.
        :param tick: Tick auquel l'appel arrive.
        :return: (succès: bool, raison: str, evt_dict: dict)
        """
        # RG1 : Validation de l'étage
        if not self.immeuble.valider_etage(etage):
            evt = {
                "tick": tick,
                "etage": self.etage_actuel,
                "direction": self.direction,
                "evenement": "Appel refusé",
                "source": source,
                "appels": list(self.liste_appels),
            }
            return False, "refusé", evt

        etage_int = int(etage)

        # RG2 : Appel pour un étage déjà dans liste_appels est ignoré
        if etage_int in self.liste_appels or etage_int in self._appels_differes:
            evt = {
                "tick": tick,
                "etage": self.etage_actuel,
                "direction": self.direction,
                "evenement": "Appel ignoré",
                "source": source,
                "appels": list(self.liste_appels),
            }
            return False, "ignoré", evt

        # RG3 : Appel à l'étage courant
        if etage_int == self.etage_actuel:
            if self.porte_ouverte:
                # Porte ouverte -> ignoré et journalisé
                evt = {
                    "tick": tick,
                    "etage": self.etage_actuel,
                    "direction": self.direction,
                    "evenement": "Appel ignoré",
                    "source": source,
                    "appels": list(self.liste_appels),
                }
                return False, "ignoré", evt
            # Porte fermée -> traité au tick suivant (RG3)
            if source == "externe":
                self.immeuble.enregistrer_appel_externe(etage_int)
            self._appels_differes.append(etage_int)
            if etage_int not in self.heure_appel:
                self.heure_appel[etage_int] = tick

            evt = {
                "tick": tick,
                "etage": self.etage_actuel,
                "direction": self.direction,
                "evenement": "Appel reçu",
                "source": source,
                "appels": list(self.liste_appels),
            }
            return True, "accepté", evt

        # RG9 : Enregistrement selon la source
        if source == "externe":
            self.immeuble.enregistrer_appel_externe(etage_int)

        self.liste_appels.append(etage_int)
        if etage_int not in self.heure_appel:
            self.heure_appel[etage_int] = tick

        evt = {
            "tick": tick,
            "etage": self.etage_actuel,
            "direction": self.direction,
            "evenement": "Appel reçu",
            "source": source,
            "appels": list(self.liste_appels),
        }
        return True, "accepté", evt

    def pas(
        self, tick: int, nouveaux_appels: Optional[list[tuple[Union[int, str], str]]] = None
    ) -> list[dict]:
        """Exécute un tick de simulation selon l'algorithme strict de la section 10.

        :param tick: Numéro du tick courant (de 1 à DUREE_SIMULATION).
        :param nouveaux_appels: Liste éventuelle de tuples (étage, source) reçus à ce tick.
        :return: Liste de dictionnaires d'événements survenus pendant le tick.
        """
        evenements_tick: list[dict] = []

        # Activation des appels différés du tick précédent (RG3)
        if self._appels_differes:
            for etage_diff in self._appels_differes:
                if etage_diff not in self.liste_appels:
                    self.liste_appels.append(etage_diff)
            self._appels_differes.clear()

        # 1. Recevoir les nouveaux appels (générés ou saisis) -> RG1, RG2, RG3
        if nouveaux_appels:
            for etage, source in nouveaux_appels:
                _, _, evt = self.ajouter_appel(etage, source, tick)
                evenements_tick.append(evt)

        # 2. Cycle logique de la cabine
        evenement_cabine = ""

        if self.porte_ouverte:
            # RG7 : La porte reste ouverte 1 tick, puis se ferme en 1 tick
            self.porte_ouverte = False
            evenement_cabine = "Fermeture porte"

        elif self.strategie.doit_s_arreter(self.etage_actuel, self.liste_appels):
            # Arrêt et ouverture de la porte
            etage_servi = self.etage_actuel
            self.liste_appels.remove(etage_servi)
            self.immeuble.retirer_appel_externe(etage_servi)

            self.porte_ouverte = True
            evenement_cabine = "Ouverture porte"

            # Calcul de l'attente pour cet appel
            heure_depart = self.heure_appel.pop(etage_servi, tick)
            attente = max(0, tick - heure_depart)
            self.attentes.append(attente)

            self.nb_servis += 1
            self.nb_arrets += 1

        else:
            # Déplacement ou maintien au repos
            ancienne_direction = self.direction
            self.direction = self.strategie.choisir_direction(
                self.etage_actuel, self.direction, self.liste_appels
            )

            if self.direction == "monte":
                if ancienne_direction != "monte":
                    self.nb_trajets += 1
                self.etage_actuel += 1
                self.nb_deplacements += 1
                evenement_cabine = "Montée"

            elif self.direction == "descend":
                if ancienne_direction != "descend":
                    self.nb_trajets += 1
                self.etage_actuel -= 1
                self.nb_deplacements += 1
                evenement_cabine = "Descente"

            else:
                evenement_cabine = "Au repos"

        # 3. Taux d'activité : SI événement différent de « Au repos » : ticks_actifs += 1
        if evenement_cabine != "Au repos":
            self.ticks_actifs += 1

        # 4. Enregistrement de l'événement de cabine
        evt_cabine = {
            "tick": tick,
            "etage": self.etage_actuel,
            "direction": self.direction,
            "evenement": evenement_cabine,
            "source": "",
            "appels": list(self.liste_appels),
        }
        evenements_tick.append(evt_cabine)

        return evenements_tick
