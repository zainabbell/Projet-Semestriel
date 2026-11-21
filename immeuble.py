"""Module immeuble.py
Définit la classe Immeuble représentant l'infrastructure physique.
Gère le nombre d'étages, les appels externes en attente et la validation des étages.
"""

from typing import Union


class Immeuble:
    """Représente l'immeuble avec ses étages et les boutons d'appel aux paliers."""

    def __init__(self, nb_etages: int = 10) -> None:
        """Initialise l'immeuble.

        :param nb_etages: Nombre d'étages (par défaut 10, étages de 0 à nb_etages - 1).
        :raises ValueError: Si nb_etages n'est pas compris entre 2 et 50.
        """
        if not (2 <= nb_etages <= 50):
            raise ValueError("Le nombre d'étages doit être compris entre 2 et 50.")
        self.nb_etages: int = nb_etages
        self.appels_externes: list[int] = []

    def valider_etage(self, etage: Union[int, str]) -> bool:
        """Vérifie la validité d'un étage selon RG1 (entier tel que 0 <= etage < nb_etages).

        :param etage: Valeur de l'étage testé.
        :return: True si valide, False sinon.
        """
        if not isinstance(etage, int) or isinstance(etage, bool):
            return False
        return 0 <= etage < self.nb_etages

    def enregistrer_appel_externe(self, etage: int) -> bool:
        """Enregistre un appel externe s'il est valide et non encore présent.

        :param etage: Numéro d'étage demandé.
        :return: True si enregistré avec succès, False sinon.
        """
        if self.valider_etage(etage):
            if etage not in self.appels_externes:
                self.appels_externes.append(etage)
            return True
        return False

    def retirer_appel_externe(self, etage: int) -> None:
        """Retire un appel externe lorsque l'étage a été desservi."""
        if etage in self.appels_externes:
            self.appels_externes.remove(etage)
