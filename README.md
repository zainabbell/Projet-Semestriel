# Projet 8 : Ascenseur Automatique (Version finale 3.0)

**iTeam University – Programmation Python (Dr. Afef Ghabri)**  
Simulation d'un ascenseur automatique à temps discret avec étude comparative des algorithmes (LOOK vs FCFS).

---

## 🚀 Démarrage Rapide

### 1. Lancer l'interface graphique Tkinter (Mode par défaut)
```bash
python main.py
```
*(ou double-cliquer directement sur `dist/AscenseurAutomatique/AscenseurAutomatique.exe`)*

### 2. Lancer la comparaison statistique LOOK vs FCFS en console
```bash
python main.py --comparer --graines 20 --duree 300
```

### 3. Lancer la simulation interactive en mode console (EF19)
```bash
python main.py --console
```

### 4. Exécuter la suite complète de tests unitaires (T1 à T20 + Section 17)
```bash
pytest tests/test_ascenseur.py -v
```

---

## 📁 Architecture du Projet

- `strategies.py` : Algorithmes d'ordonnancement **LOOK** et **FCFS** (`doit_s_arreter`, `choisir_direction`).
- `immeuble.py` : Modélisation des étages et validation des appels (RG1).
- `ascenseur.py` : Modélisation de la cabine, gestion de porte (RG7, RG8) et boucle d'un tick (Section 10).
- `scenarios.py` : Profils de trafic (Matin, Midi, Nuit, Personnalisé) et pré-génération équitable (RG11).
- `simulation.py` : Moteur d'exécution des ticks et agrégation des mesures.
- `statistiques.py` : Calculs des métriques (attente moyenne, attente max, déplacements, activité).
- `base_donnees.py` : Gestionnaire SQLite (`data/ascenseur.db`) et export CSV (Section 12, ENF8).
- `comparaison.py` : Banc d'essai automatisé sur 20 graines et synthèse des moyennes.
- `gui.py` : Interface graphique Tkinter complète à 3 onglets (Simulation Canvas, Comparaison avec graphique en barres, Historique).
- `main.py` : Point d'entrée unifié CLI et GUI.
- `tests/test_ascenseur.py` : Suite de validation pytest (tests T1 à T20 et reproduction de la section 17).
- `RAPPORT.md` : Rapport académique complet du projet respectant le plan officiel (Section 18).
- `dist/AscenseurAutomatique/` : Exécutable autonome compilé via PyInstaller (ENF6).

