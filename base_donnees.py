"""Module base_donnees.py
Gère la persistance SQLite (simulations et événements) et l'export CSV (Sections 7 et 12).
Respecte l'exigence ENF8 (requêtes paramétrées avec '?') et RG12 (transaction unique).
"""

import os
import sqlite3
import csv
from typing import Any, Optional

DB_FOLDER = "data"
DB_FILE = os.path.join(DB_FOLDER, "ascenseur.db")


def initialiser_base(db_path: str = DB_FILE) -> None:
    """Crée le dossier data/ et initialise les tables SQLite si elles n'existent pas.

    :param db_path: Chemin du fichier SQLite.
    """
    repertoire = os.path.dirname(db_path)
    if repertoire and not os.path.exists(repertoire):
        os.makedirs(repertoire, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        # Table simulations
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS simulations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date_heure TEXT NOT NULL,
                strategie TEXT NOT NULL,
                scenario TEXT NOT NULL,
                graine INTEGER,
                nb_etages INTEGER NOT NULL,
                duree INTEGER NOT NULL,
                appels_servis INTEGER NOT NULL,
                attente_moyenne REAL NOT NULL,
                attente_max INTEGER NOT NULL,
                deplacements INTEGER NOT NULL,
                taux_occupation REAL NOT NULL
            );
            """
        )

        # Table evenements
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS evenements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                simulation_id INTEGER NOT NULL,
                tick INTEGER NOT NULL,
                etage INTEGER NOT NULL,
                direction TEXT NOT NULL,
                evenement TEXT NOT NULL,
                source TEXT,
                appels TEXT,
                FOREIGN KEY(simulation_id) REFERENCES simulations(id) ON DELETE CASCADE
            );
            """
        )
        conn.commit()


def enregistrer_simulation(
    simulation_data: dict[str, Any],
    evenements: list[dict[str, Any]],
    db_path: str = DB_FILE,
) -> int:
    """Enregistre une simulation et l'ensemble de ses événements en une seule transaction (RG12, ENF8).

    :param simulation_data: Métadonnées et statistiques de la simulation.
    :param evenements: Liste chronologique des événements.
    :param db_path: Chemin du fichier SQLite.
    :return: L'identifiant (ID) généré pour la simulation.
    """
    initialiser_base(db_path)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        # Insertion dans simulations avec requête paramétrée
        cursor.execute(
            """
            INSERT INTO simulations (
                date_heure, strategie, scenario, graine, nb_etages,
                duree, appels_servis, attente_moyenne, attente_max,
                deplacements, taux_occupation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                simulation_data["date_heure"],
                simulation_data["strategie"],
                simulation_data["scenario"],
                simulation_data.get("graine"),
                simulation_data["nb_etages"],
                simulation_data["duree"],
                simulation_data["appels_servis"],
                simulation_data["attente_moyenne"],
                simulation_data["attente_max"],
                simulation_data["deplacements"],
                simulation_data["taux_occupation"],
            ),
        )
        simulation_id = cursor.lastrowid

        # Préparation du lot d'événements
        lot_evenements = []
        for evt in evenements:
            appels_str = ",".join(map(str, evt.get("appels", [])))
            lot_evenements.append(
                (
                    simulation_id,
                    evt["tick"],
                    evt["etage"],
                    evt["direction"],
                    evt["evenement"],
                    evt.get("source", ""),
                    appels_str,
                )
            )

        # Insertion en masse sécurisée
        cursor.executemany(
            """
            INSERT INTO evenements (
                simulation_id, tick, etage, direction, evenement, source, appels
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            lot_evenements,
        )

        conn.commit()
        return simulation_id


def lire_historique(db_path: str = DB_FILE) -> list[dict[str, Any]]:
    """Récupère l'ensemble des simulations enregistrées, triées de la plus récente à la plus ancienne.

    :param db_path: Chemin du fichier SQLite.
    :return: Liste de dictionnaires décrivant chaque simulation.
    """
    initialiser_base(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, date_heure, strategie, scenario, graine, nb_etages,
                   duree, appels_servis, attente_moyenne, attente_max,
                   deplacements, taux_occupation
            FROM simulations
            ORDER BY id DESC;
            """
        )
        lignes = cursor.fetchall()
        return [dict(ligne) for ligne in lignes]


def lire_evenements_simulation(simulation_id: int, db_path: str = DB_FILE) -> list[dict[str, Any]]:
    """Récupère tous les événements d'une simulation donnée.

    :param simulation_id: ID de la simulation.
    :param db_path: Chemin du fichier SQLite.
    :return: Liste de dictionnaires représentant les événements.
    """
    initialiser_base(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, simulation_id, tick, etage, direction, evenement, source, appels
            FROM evenements
            WHERE simulation_id = ?
            ORDER BY id ASC;
            """,
            (simulation_id,),
        )
        return [dict(ligne) for ligne in cursor.fetchall()]


def exporter_csv(simulation_id: int, chemin_csv: str, db_path: str = DB_FILE) -> bool:
    """Exporte le journal des événements d'une simulation au format CSV (point-virgule, UTF-8).

    :param simulation_id: ID de la simulation à exporter.
    :param chemin_csv: Chemin cible du fichier CSV.
    :param db_path: Chemin du fichier SQLite.
    :return: True si l'export a réussi, False sinon.
    """
    evenements = lire_evenements_simulation(simulation_id, db_path)
    if not evenements:
        return False

    colonnes = ["id", "simulation_id", "tick", "etage", "direction", "evenement", "source", "appels"]

    with open(chemin_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=colonnes, delimiter=";")
        writer.writeheader()
        for evt in evenements:
            writer.writerow(evt)

    return True
