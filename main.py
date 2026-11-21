"""Module main.py
Point d'entrée principal du projet Ascenseur Automatique.
Permet de lancer l'interface graphique Tkinter (par défaut) ou le mode console équivalent (EF19).
"""

import sys
import argparse
import datetime
from typing import Optional

from strategies import LOOK, FCFS
from immeuble import Immeuble
from ascenseur import Ascenseur
from scenarios import obtenir_scenario, generer_suite_appels
from simulation import lancer
from statistiques import formater_statistiques
from comparaison import executer_comparaison
from base_donnees import initialiser_base, enregistrer_simulation


def mode_console_interactif() -> None:
    """Mode console interactif permettant de configurer et tester des simulations (EF8, EF19)."""
    print("=" * 65)
    print("      SIMULATION ASCENSEUR AUTOMATIQUE - MODE CONSOLE (EF19)")
    print("=" * 65)

    # 1. Configuration
    try:
        nb_etages_in = input("Nombre d'étages [défaut: 10] : ").strip()
        nb_etages = int(nb_etages_in) if nb_etages_in else 10

        strat_in = input("Stratégie (1 pour LOOK, 2 pour FCFS) [défaut: LOOK] : ").strip()
        strategie = FCFS() if strat_in == "2" else LOOK()

        scen_in = input("Scénario (matin, midi, nuit, personnalisé) [défaut: matin] : ").strip().lower()
        if not scen_in:
            scen_in = "matin"

        duree_in = input("Durée en ticks [défaut: 20] : ").strip()
        duree = int(duree_in) if duree_in else 20

        graine_in = input("Graine aléatoire (optionnelle) : ").strip()
        graine = int(graine_in) if graine_in else None

    except ValueError:
        print("Erreur : saisie invalide, utilisation des valeurs par défaut.")
        nb_etages = 10
        strategie = LOOK()
        scen_in = "matin"
        duree = 20
        graine = None

    scenario = obtenir_scenario(scen_in)
    appels_dict = generer_suite_appels(scenario, nb_etages, duree, graine)

    print(f"\nConfiguration validée : {strategie.nom} | Scénario: {scen_in} | {nb_etages} étages | Durée: {duree} ticks\n")

    # Mode pas à pas ou complet
    mode_pas = input("Voulez-vous avancer pas à pas (o/n) [défaut: n] ? ").strip().lower() == "o"

    immeuble = Immeuble(nb_etages)
    ascenseur = Ascenseur(immeuble, etage_initial=0, strategie=strategie)
    evenements_session = []

    print("-" * 65)
    print(f"{'Tick':<6} | {'Étage':<6} | {'Direction':<10} | {'Événement':<18} | {'Appels restants'}")
    print("-" * 65)

    for tick in range(1, duree + 1):
        nouveaux_appels = appels_dict.get(tick, [])
        evts = ascenseur.pas(tick, nouveaux_appels)
        evenements_session.extend(evts)

        for e in evts:
            appels_str = str(e["appels"])
            print(f"{e['tick']:<6} | {e['etage']:<6} | {e['direction']:<10} | {e['evenement']:<18} | {appels_str}")

        if mode_pas and tick < duree:
            reponse = input(">> Appuyez sur Entrée pour tick suivant, ou saisissez un appel (ex: 4 ext ou 7 int), 'q' pour quitter : ").strip()
            if reponse.lower() == "q":
                break
            elif reponse:
                parts = reponse.split()
                try:
                    etage_demande = int(parts[0])
                    source_demande = "externe" if len(parts) > 1 and "ext" in parts[1].lower() else "interne"
                    succes, raison, evt_man = ascenseur.ajouter_appel(etage_demande, source_demande, tick)
                    evenements_session.append(evt_man)
                    print(f"   [Manuel] {evt_man['evenement']} à l'étage {etage_demande} ({source_demande})")
                except Exception as ex:
                    print(f"   [Erreur saisie] {ex}")

    # Fin et calcul des statistiques
    from statistiques import calculer_statistiques
    stats = calculer_statistiques(
        attentes=ascenseur.attentes,
        ticks_actifs=ascenseur.ticks_actifs,
        ticks_totaux=tick,
        nb_servis=ascenseur.nb_servis,
        nb_deplacements=ascenseur.nb_deplacements,
    )

    print("\n" + "=" * 65)
    print("                    RÉSULTATS DE LA SIMULATION")
    print("=" * 65)
    print(formater_statistiques(stats))
    print(f"Appels en attente non servis : {len(ascenseur.liste_appels)}")

    # Enregistrement dans SQLite
    donnees_sim = {
        "date_heure": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "strategie": strategie.nom,
        "scenario": scen_in,
        "graine": graine,
        "nb_etages": nb_etages,
        "duree": tick,
        **stats,
    }
    sim_id = enregistrer_simulation(donnees_sim, evenements_session)
    print(f"Simulation enregistrée dans data/ascenseur.db avec l'ID #{sim_id}\n")


def mode_comparaison_console(nb_graines: int = 20, duree: int = 300) -> None:
    """Exécute la comparaison LOOK vs FCFS en ligne de commande et affiche les résultats chiffrés."""
    print("=" * 75)
    print(f"  ÉTUDE COMPARATIVE CHIFFRÉE : LOOK vs FCFS ({nb_graines} graines, {duree} ticks)")
    print("=" * 75)

    def progression(actuel, total, msg):
        pourcent = int((actuel / total) * 100)
        print(f"\rProgression : [{pourcent:3d}%] {msg:<50}", end="", flush=True)

    resultats = executer_comparaison(
        nb_graines=nb_graines,
        duree=duree,
        callback_progression=progression,
    )
    print("\n\n" + "-" * 75)
    print(f"{'Scénario':<12} | {'Stratégie':<10} | {'Attente Moy':<12} | {'Déplacements':<14} | {'Servis':<10} | {'Activité'}")
    print("-" * 75)

    synthese = resultats["synthese"]
    for sc in ["matin", "midi", "nuit"]:
        for strat in ["LOOK", "FCFS"]:
            s = synthese[sc][strat]
            print(
                f"{sc.capitalize():<12} | {strat:<10} | {s['attente_moyenne']:>8.2f} s   | {s['deplacements']:>10.1f}     | {s['appels_servis']:>6.1f}   | {s['taux_occupation']:>5.1f} %"
            )
        print("-" * 75)


def main() -> None:
    """Point d'entrée du script."""
    parser = argparse.ArgumentParser(description="Simulation et comparaison d'ascenseur automatique.")
    parser.add_argument("--gui", action="store_true", help="Lancer l'interface graphique Tkinter (par défaut si aucun argument)")
    parser.add_argument("--console", action="store_true", help="Lancer en mode console interactif")
    parser.add_argument("--comparer", action="store_true", help="Lancer l'étude comparative LOOK vs FCFS directement en console")
    parser.add_argument("--graines", type=int, default=20, help="Nombre de graines pour la comparaison (défaut: 20)")
    parser.add_argument("--duree", type=int, default=300, help="Durée en ticks pour la comparaison (défaut: 300)")

    args = parser.parse_args()

    # Initialisation de la base SQLite
    initialiser_base()

    if args.comparer:
        mode_comparaison_console(args.graines, args.duree)
    elif args.console:
        mode_console_interactif()
    else:
        # Interface Tkinter par défaut
        try:
            from gui import lancer_gui
            lancer_gui()
        except Exception as e:
            print(f"Impossible d'ouvrir l'interface Tkinter ({e}). Démarrage en mode console...")
            mode_console_interactif()


if __name__ == "__main__":
    main()
