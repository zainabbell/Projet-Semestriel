"""Module voir_base.py
Outil en ligne de commande pour inspecter, afficher et interroger la base SQLite (data/ascenseur.db).
"""

import sys
import sqlite3
from base_donnees import DB_FILE, initialiser_base, lire_historique, lire_evenements_simulation


def afficher_simulations() -> None:
    """Affiche toutes les simulations enregistrées dans data/ascenseur.db."""
    initialiser_base(DB_FILE)
    sims = lire_historique(DB_FILE)

    print("\n" + "=" * 90)
    print(f"             BASE SQLITE : {DB_FILE} ({len(sims)} simulation(s) enregistrée(s))")
    print("=" * 90)

    if not sims:
        print("Aucune simulation n'est encore enregistrée dans la base.")
        print("Lancez une simulation via l'interface graphique (py main.py) ou en console pour alimenter la base.\n")
        return

    en_tete = f"{'ID':<4} | {'Date / Heure':<19} | {'Stratégie':<9} | {'Scénario':<9} | {'Graine':<7} | {'Étages':<6} | {'Durée':<6} | {'Servis':<6} | {'Att. Moy':<9} | {'Dépl':<5} | {'Activité':<8}"
    print(en_tete)
    print("-" * 90)

    for s in sims:
        graine_str = str(s["graine"]) if s["graine"] is not None else "-"
        print(
            f"{s['id']:<4} | "
            f"{s['date_heure']:<19} | "
            f"{s['strategie']:<9} | "
            f"{s['scenario']:<9} | "
            f"{graine_str:<7} | "
            f"{s['nb_etages']:<6} | "
            f"{s['duree']:<6} | "
            f"{s['appels_servis']:<6} | "
            f"{s['attente_moyenne']:>6.2f} s  | "
            f"{s['deplacements']:<5} | "
            f"{s['taux_occupation']:>5.1f} %"
        )
    print("-" * 90 + "\n")


def afficher_evenements(simulation_id: int, limite: int = 25) -> None:
    """Affiche les événements d'une simulation spécifique."""
    evts = lire_evenements_simulation(simulation_id, DB_FILE)
    if not evts:
        print(f"\nAucun événement trouvé pour la simulation ID #{simulation_id}.\n")
        return

    print("\n" + "=" * 80)
    print(f"   ÉVÉNEMENTS DE LA SIMULATION #{simulation_id} (Total: {len(evts)} événements)")
    print("=" * 80)
    print(f"{'Tick':<6} | {'Étage':<6} | {'Direction':<10} | {'Événement':<18} | {'Source':<9} | {'File d\'attente'}")
    print("-" * 80)

    a_afficher = evts[:limite] if limite > 0 else evts
    for e in a_afficher:
        appels_str = e.get("appels", "")
        print(
            f"{e['tick']:<6} | "
            f"{e['etage']:<6} | "
            f"{e['direction']:<10} | "
            f"{e['evenement']:<18} | "
            f"{e.get('source', ''):<9} | "
            f"{appels_str}"
        )

    if limite > 0 and len(evts) > limite:
        print(f"... et {len(evts) - limite} autres événements non affichés (utilisez --tout pour voir l'intégralité).")
    print("-" * 80 + "\n")


def menu_interactif() -> None:
    """Menu interactif pour explorer SQLite en ligne de commande."""
    while True:
        afficher_simulations()
        print("Options disponibles :")
        print("  1. Voir les événements d'une simulation")
        print("  2. Exécuter une requête SQL personnalisée (SELECT)")
        print("  3. Quitter")
        choix = input("\nVotre choix [1/2/3] : ").strip()

        if choix == "1":
            sim_id_in = input("Entrez l'ID de la simulation : ").strip()
            try:
                sim_id = int(sim_id_in)
                afficher_evenements(sim_id, limite=30)
            except ValueError:
                print("ID invalide.")
            input("Appuyez sur Entrée pour continuer...")

        elif choix == "2":
            requete = input("Entrez votre requête SQL (ex: SELECT * FROM simulations WHERE strategie='LOOK') :\n> ").strip()
            if requete:
                try:
                    with sqlite3.connect(DB_FILE) as conn:
                        conn.row_factory = sqlite3.Row
                        cur = conn.cursor()
                        cur.execute(requete)
                        lignes = cur.fetchall()
                        if lignes:
                            cols = lignes[0].keys()
                            print("\nRésultats :")
                            print(" | ".join(cols))
                            print("-" * 60)
                            for l in lignes:
                                print(" | ".join(str(l[c]) for c in cols))
                        else:
                            print("Aucun résultat retourné.")
                except Exception as ex:
                    print(f"Erreur SQL : {ex}")
            input("\nAppuyez sur Entrée pour continuer...")

        elif choix == "3" or choix.lower() in ("q", "quit", "exit"):
            print("Au revoir !")
            break


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        afficher_evenements(int(sys.argv[1]), limite=0 if "--tout" in sys.argv else 25)
    elif "--menu" in sys.argv or len(sys.argv) == 1:
        afficher_simulations()
        if sys.stdin.isatty():
            menu_interactif()
    else:
        afficher_simulations()
