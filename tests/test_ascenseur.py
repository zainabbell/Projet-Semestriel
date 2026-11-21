"""Suite de tests unitaires et d'intégration validant le cahier des charges (Section 16 : T1 à T20 et Section 17).
Exécutable avec pytest.
"""

import os
import tempfile
import pytest
from strategies import LOOK, FCFS
from immeuble import Immeuble
from ascenseur import Ascenseur
from scenarios import (
    ScenarioMatin,
    ScenarioMidi,
    ScenarioNuit,
    generer_suite_appels,
    obtenir_scenario,
)
from simulation import lancer
from comparaison import executer_comparaison
from base_donnees import (
    initialiser_base,
    enregistrer_simulation,
    lire_historique,
    lire_evenements_simulation,
    exporter_csv,
)


def test_t1_aucun_appel():
    """T1 : Aucun appel pendant 10 ticks -> reste à l'étage 0, 'Au repos', 0 appel servi, taux 0 %."""
    stats, evts, asc = lancer(strategie=LOOK(), appels={}, duree=10, nb_etages=10, etage_initial=0)
    assert asc.etage_actuel == 0
    assert asc.direction == "arrêt"
    assert stats["appels_servis"] == 0
    assert stats["taux_occupation"] == 0.0
    assert all(e["evenement"] == "Au repos" for e in evts)


def test_t2_appel_interne_look():
    """T2 : Appel interne au 5e étage (LOOK) -> montée 1 à 5, ouverture, fermeture, repos."""
    # Appel reçu au tick 1
    appels = {1: [(5, "interne")]}
    stats, evts, asc = lancer(strategie=LOOK(), appels=appels, duree=10, nb_etages=10, etage_initial=0)
    evts_cabine = [e["evenement"] for e in evts if e["source"] == ""]
    assert "Montée" in evts_cabine
    assert "Ouverture porte" in evts_cabine
    assert "Fermeture porte" in evts_cabine
    assert stats["appels_servis"] == 1
    assert stats["deplacements"] == 5


def test_t3_appel_externe():
    """T3 : Appel externe au 3e étage -> même comportement, source 'externe' dans le journal."""
    appels = {1: [(3, "externe")]}
    stats, evts, asc = lancer(strategie=LOOK(), appels=appels, duree=8, nb_etages=10, etage_initial=0)
    evts_appels = [e for e in evts if e["evenement"] == "Appel reçu"]
    assert len(evts_appels) == 1
    assert evts_appels[0]["source"] == "externe"
    assert stats["appels_servis"] == 1


def test_t4_look_arret_4_puis_8():
    """T4 : LOOK, départ au 2e, appels 8 puis 4 -> arrêt au 4e puis au 8e."""
    asc = Ascenseur(Immeuble(10), etage_initial=2, strategie=LOOK())
    asc.ajouter_appel(8, "interne", tick=0)
    asc.ajouter_appel(4, "interne", tick=0)

    ordres_arrets = []
    for t in range(1, 15):
        evts = asc.pas(t)
        for e in evts:
            if e["evenement"] == "Ouverture porte":
                ordres_arrets.append(e["etage"])

    assert ordres_arrets == [4, 8]


def test_t5_look_appel_en_bas_pendant_montee():
    """T5 : LOOK, appel en bas pendant une montée -> traité après la fin de la montée."""
    asc = Ascenseur(Immeuble(10), etage_initial=0, strategie=LOOK())
    asc.ajouter_appel(6, "interne", tick=0)
    # Monte vers le 6
    for t in range(1, 4):
        asc.pas(t)
    # À l'étage 3, un appel arrive pour l'étage 1
    asc.ajouter_appel(1, "interne", tick=4)

    ordres_arrets = []
    for t in range(4, 25):
        evts = asc.pas(t)
        for e in evts:
            if e["evenement"] == "Ouverture porte":
                ordres_arrets.append(e["etage"])

    # L'ascenseur doit terminer son ascension au 6 avant de redescendre vers le 1
    assert ordres_arrets == [6, 1]


def test_t6_appel_etage_courant_porte_fermee():
    """T6 : Appel à l'étage courant, porte fermée -> ouverture au tick suivant, attente de 1 tick."""
    asc = Ascenseur(Immeuble(10), etage_initial=3, strategie=LOOK())
    # Tick 1 : appel à l'étage 3
    evts1 = asc.pas(1, [(3, "interne")])
    assert not asc.porte_ouverte
    # Tick 2 : ouverture de la porte
    evts2 = asc.pas(2)
    evts_ouverture = [e for e in evts2 if e["evenement"] == "Ouverture porte"]
    assert len(evts_ouverture) == 1
    assert asc.attentes[-1] == 1  # 2 - 1 = 1 tick


def test_t7_appel_etage_courant_porte_ouverte():
    """T7 : Appel à l'étage courant, porte ouverte -> ignoré et journalisé (RG3)."""
    asc = Ascenseur(Immeuble(10), etage_initial=3, strategie=LOOK())
    asc.porte_ouverte = True
    succes, raison, evt = asc.ajouter_appel(3, "interne", tick=2)
    assert succes is False
    assert raison == "ignoré"
    assert evt["evenement"] == "Appel ignoré"


def test_t8_deux_appels_meme_etage():
    """T8 : Deux appels au même étage -> un seul arrêt."""
    asc = Ascenseur(Immeuble(10), etage_initial=0, strategie=LOOK())
    asc.ajouter_appel(4, "interne", tick=1)
    succes, raison, evt = asc.ajouter_appel(4, "externe", tick=2)
    assert succes is False
    assert raison == "ignoré"
    assert len(asc.liste_appels) == 1

    ouvertures = 0
    for t in range(1, 10):
        for e in asc.pas(t):
            if e["evenement"] == "Ouverture porte":
                ouvertures += 1
    assert ouvertures == 1


def test_t9_etage_invalide():
    """T9 : Étage -1 ou 10 avec 10 étages -> appel refusé (RG1)."""
    asc = Ascenseur(Immeuble(10), etage_initial=0, strategie=LOOK())
    succes1, raison1, evt1 = asc.ajouter_appel(-1, "interne", tick=1)
    succes2, raison2, evt2 = asc.ajouter_appel(10, "interne", tick=1)
    assert succes1 is False and raison1 == "refusé"
    assert evt1["evenement"] == "Appel refusé"
    assert succes2 is False and raison2 == "refusé"
    assert evt2["evenement"] == "Appel refusé"


def test_t10_saisie_abc():
    """T10 : Saisie 'abc' -> message d'erreur, pas de plantage."""
    asc = Ascenseur(Immeuble(10), etage_initial=0, strategie=LOOK())
    succes, raison, evt = asc.ajouter_appel("abc", "interne", tick=1)
    assert succes is False
    assert raison == "refusé"
    assert evt["evenement"] == "Appel refusé"


def test_t11_look_arret_egalite_distance():
    """T11 : LOOK à l'arrêt, appels 2 et 6 depuis l'étage 4 -> va d'abord au 2e (RG5)."""
    asc = Ascenseur(Immeuble(10), etage_initial=4, strategie=LOOK())
    # Distance vers 2: |2-4|=2 ; vers 6: |6-4|=2. Égalité -> étage le plus bas (2).
    asc.ajouter_appel(6, "interne", tick=0)
    asc.ajouter_appel(2, "interne", tick=0)

    # Au tick 1, il doit choisir de descendre vers le 2
    evts = asc.pas(1)
    assert asc.direction == "descend"
    assert asc.etage_actuel == 3


def test_t12_reproductibilite_graine():
    """T12 : Même graine deux fois -> journaux et statistiques identiques."""
    sc = ScenarioMidi()
    appels1 = generer_suite_appels(sc, 10, 50, graine=42)
    appels2 = generer_suite_appels(sc, 10, 50, graine=42)
    assert appels1 == appels2

    stats1, evts1, _ = lancer(LOOK(), appels1, duree=50)
    stats2, evts2, _ = lancer(LOOK(), appels2, duree=50)
    assert stats1 == stats2
    assert len(evts1) == len(evts2)
    for e1, e2 in zip(evts1, evts2):
        assert e1 == e2


def test_t13_fcfs_arret_8_puis_4():
    """T13 : FCFS, départ au 2e, appels 8 puis 4 -> arrêt au 8e puis au 4e (RG6)."""
    asc = Ascenseur(Immeuble(10), etage_initial=2, strategie=FCFS())
    asc.ajouter_appel(8, "interne", tick=0)
    asc.ajouter_appel(4, "interne", tick=0)

    ordres_arrets = []
    for t in range(1, 25):
        evts = asc.pas(t)
        for e in evts:
            if e["evenement"] == "Ouverture porte":
                ordres_arrets.append(e["etage"])

    assert ordres_arrets == [8, 4]


def test_t14_fcfs_traverse_etage_demande():
    """T14 : FCFS traverse un étage demandé -> ne s'y arrête pas, l'étage reste dans la liste."""
    asc = Ascenseur(Immeuble(10), etage_initial=0, strategie=FCFS())
    asc.ajouter_appel(5, "interne", tick=0)
    asc.ajouter_appel(2, "interne", tick=0)

    # Lorsque l'ascenseur arrive à l'étage 2 (vers le tick 2)
    for t in range(1, 3):
        asc.pas(t)

    assert asc.etage_actuel == 2
    assert not asc.porte_ouverte
    assert 2 in asc.liste_appels


def test_t15_equite_comparaison_suite_appels():
    """T15 : Même graine et même scénario, LOOK puis FCFS -> suites d'appels identiques (RG11)."""
    sc = ScenarioMatin()
    appels = generer_suite_appels(sc, 10, 100, graine=777)
    stats_look, _, _ = lancer(LOOK(), appels, duree=100)
    stats_fcfs, _, _ = lancer(FCFS(), appels, duree=100)
    assert stats_look["duree_totale"] == 100
    assert stats_fcfs["duree_totale"] == 100


def test_t16_scenario_matin_repartition():
    """T16 : Scénario matin, 1000 appels générés -> environ 60 % ou plus des appels visent l'étage 0."""
    import random
    sc = ScenarioMatin()
    rng = random.Random(12345)
    etages = [sc.generer_etage(10, rng) for _ in range(1000)]
    proportion_etage_0 = etages.count(0) / len(etages)
    assert 0.55 <= proportion_etage_0 <= 0.65


def test_t17_enregistrement_et_lecture_sqlite():
    """T17 : Enregistrer une simulation puis la relire -> statistiques et nombre d'événements identiques."""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_ascenseur.db")

    try:
        appels = {1: [(3, "interne")], 2: [(5, "externe")]}
        stats, evts, _ = lancer(LOOK(), appels, duree=15)
        sim_data = {
            "date_heure": "2026-11-21 14:00:00",
            "strategie": "LOOK",
            "scenario": "matin",
            "graine": 123,
            "nb_etages": 10,
            "duree": 15,
            **stats,
        }
        sim_id = enregistrer_simulation(sim_data, evts, db_path=db_path)
        historique = lire_historique(db_path=db_path)
        assert len(historique) == 1
        assert historique[0]["id"] == sim_id
        assert historique[0]["deplacements"] == stats["deplacements"]

        evts_lus = lire_evenements_simulation(sim_id, db_path=db_path)
        assert len(evts_lus) == len(evts)

        # Test d'export CSV
        csv_path = os.path.join(temp_dir, "export.csv")
        assert exporter_csv(sim_id, csv_path, db_path=db_path) is True
        assert os.path.exists(csv_path)
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_t18_comparaison_complete_structure():
    """T18 : Comparaison complète -> le tableau contient 3 scénarios x 2 stratégies."""
    res = executer_comparaison(nb_graines=2, duree=50, nb_etages=10)
    synthese = res["synthese"]
    assert set(synthese.keys()) == {"matin", "midi", "nuit"}
    for sc in ["matin", "midi", "nuit"]:
        assert "LOOK" in synthese[sc]
        assert "FCFS" in synthese[sc]
        assert "attente_moyenne" in synthese[sc]["LOOK"]
        assert "deplacements" in synthese[sc]["LOOK"]


def test_t19_reactivite_interface():
    """T19 : Tkinter pendant une simulation rapide -> la fenêtre reste réactive (Pause, Pas)."""
    import tkinter as tk
    from gui import ApplicationAscenseur

    root = tk.Tk()
    root.withdraw()
    try:
        app = ApplicationAscenseur(root)
        # Test du mode Pas à pas
        app._action_pas()
        assert app.tick_actuel == 1
        assert app.ascenseur is not None

        # Test de démarrage et mise en pause
        app._action_demarrer()
        assert app.en_cours is True
        app._action_pause()
        assert app.en_cours is False

        # Test d'avancement manuel d'un tick
        app._action_pas()
        assert app.tick_actuel == 3
    finally:
        root.destroy()


def test_t20_look_vs_fcfs_deplacements():
    """T20 : Comparaison sur graines -> LOOK obtient en moyenne moins ou égal de déplacements que FCFS."""
    res = executer_comparaison(nb_graines=5, duree=150, nb_etages=10, scenarios_noms=["midi"])
    moy_look = res["synthese"]["midi"]["LOOK"]["deplacements"]
    moy_fcfs = res["synthese"]["midi"]["FCFS"]["deplacements"]
    # LOOK optimise la trajectoire, les déplacements doivent être significativement inférieurs
    assert moy_look <= moy_fcfs


def test_section_17_exemple_officiel():
    """Section 17 : Exemple officiel détaillé
    Configuration : 10 étages, départ à l'étage 0, appels aux étages 8 puis 4, reçus au tick 0.
    LOOK :
      Attentes : 5 (étage 4) et 11 (étage 8), moyenne 8.00 s, déplacements = 8
    FCFS :
      Attentes : 9 (étage 8) et 15 (étage 4), moyenne 12.00 s, déplacements = 12
    """
    # 1. Test LOOK
    asc_look = Ascenseur(Immeuble(10), etage_initial=0, strategie=LOOK())
    asc_look.ajouter_appel(8, "interne", tick=0)
    asc_look.ajouter_appel(4, "interne", tick=0)

    for t in range(1, 13):
        asc_look.pas(t)

    assert asc_look.attentes == [5, 11]
    moy_look = sum(asc_look.attentes) / len(asc_look.attentes)
    assert round(moy_look, 2) == 8.00
    assert asc_look.nb_deplacements == 8

    # 2. Test FCFS
    asc_fcfs = Ascenseur(Immeuble(10), etage_initial=0, strategie=FCFS())
    asc_fcfs.ajouter_appel(8, "interne", tick=0)
    asc_fcfs.ajouter_appel(4, "interne", tick=0)

    for t in range(1, 17):
        asc_fcfs.pas(t)

    assert asc_fcfs.attentes == [9, 15]
    moy_fcfs = sum(asc_fcfs.attentes) / len(asc_fcfs.attentes)
    assert round(moy_fcfs, 2) == 12.00
    assert asc_fcfs.nb_deplacements == 12
