# Rapport de Projet : Simulation d'un Ascenseur Automatique avec Étude Comparative des Algorithmes (LOOK vs FCFS)

**Projet :** Projet 8 – Ascenseur Automatique (Version finale 3.0)  
**Institution :** iTeam University – Année Universitaire 2026-2027  
**Matière :** Programmation Python avancée  
**Enseignante :** Dr. Afef Ghabri  

---

## 1. Introduction

Dans les bâtiments modernes, la gestion des ascenseurs constitue un problème classique mais crucial d'ordonnancement de requêtes sous contraintes physiques et temporelles. L'objectif d'un système de contrôle est double :
1. **Minimiser le temps d'attente** des usagers (qualité de service et satisfaction client).
2. **Minimiser l'énergie dépensée** par la cabine en réduisant le nombre total de déplacements d'étages et les inversions intempestives de sens.

Ce projet a pour finalité la conception, le développement et la validation d'un simulateur complet d'ascenseur automatique à temps discret (1 tick = 1 seconde), intégrant :
- Une logique événementielle modulaire séparant le moteur de simulation de l'affichage.
- L'implémentation de deux politiques d'ordonnancement fondamentales : **LOOK** (balayage optimisé) et **FCFS** (*First-Come, First-Served*).
- La modélisation de profils de trafic réalistes (**Matin**, **Midi**, **Nuit**, **Personnalisé**).
- Une interface graphique moderne développée avec **Tkinter** offrant l'animation visuelle de la cabine, la gestion des boutons paliers et cabine, ainsi que la visualisation dynamique des métriques.
- Un banc d'essai comparatif automatisé avec génération de graphiques en barres.
- La persistance des simulations et de leurs événements dans une base de données **SQLite** avec fonctionnalités d'export **CSV**.
- Une couverture intégrale de tests unitaires et fonctionnels validés sous **pytest**.

---

## 2. Organisation du programme et cycle d'un tick

### 2.1 Architecture logicielle modulaire

Conformément à l'exigence **ENF1**, la logique métier est strictement découplée de toute interface graphique ou console. Les modules sont organisés comme suit :

| Fichier | Responsabilité |
| :--- | :--- |
| `strategies.py` | Définition des stratégies de déplacement `LOOK` et `FCFS` (méthodes `doit_s_arreter` et `choisir_direction`). |
| `immeuble.py` | Modélisation de l'immeuble, validation des étages (RG1) et stockage des appels externes. |
| `ascenseur.py` | Modélisation de la cabine, file d'attente sans doublon, gestion de porte et exécution du cycle d'un tick. |
| `scenarios.py` | Profils de trafic probabilistes et pré-génération reproductible des suites d'appels (RG11, ENF5). |
| `simulation.py` | Moteur d'exécution des ticks, collecte des métriques et gestion de fin de simulation (RG10). |
| `statistiques.py` | Calculs mathématiques des indicateurs de performance (Section 11). |
| `base_donnees.py` | Persistance transactionnelle sous SQLite (`data/ascenseur.db`) et export CSV (RG12, ENF8). |
| `comparaison.py` | Moteur de comparaison statistique LOOK vs FCFS sur $N$ graines et plusieurs scénarios. |
| `gui.py` | Interface graphique Tkinter complète à trois onglets (Simulation, Comparaison, Historique). |
| `main.py` | Point d'entrée de l'application (lancement GUI par défaut ou options CLI `--console`, `--comparer`). |
| `tests/test_ascenseur.py` | Suite de tests automatisés couvrant l'ensemble du plan de tests (T1 à T20 et section 17). |

### 2.2 Schéma du cycle logique d'un tick (Section 10)

À chaque tick (seconde simulée), le système applique de manière séquentielle et déterministe les 4 étapes suivantes :

```text
[Début du Tick]
       │
       ▼
1. Réception des nouveaux appels
   ├── Validation RG1 (0 <= étage < NB_ETAGES) : sinon "Appel refusé"
   ├── Vérification RG2 (étage déjà demandé)   : sinon "Appel ignoré"
   └── Règle RG3 (appel étage courant)        :
         ├── Porte ouverte -> "Appel ignoré"
         └── Porte fermée  -> mis en attente pour traitement au tick suivant
       │
       ▼
2. Action de la cabine (exactement UNE seule action par tick, RG8)
   ├── SI porte_ouverte :
   │     porte_ouverte = Faux
   │     événement = "Fermeture porte" (RG7)
   │
   ├── SINON SI strategie.doit_s_arreter(etage_actuel, liste_appels) :
   │     porte_ouverte = Vrai
   │     retirer étage de liste_appels
   │     attente = tick - heure_appel[étage]
   │     nb_servis += 1, nb_arrets += 1
   │     événement = "Ouverture porte"
   │
   └── SINON :
         direction = strategie.choisir_direction(etage_actuel, direction, liste_appels)
         ├── "monte"   -> etage += 1, nb_deplacements += 1, événement = "Montée"
         ├── "descend" -> etage -= 1, nb_deplacements += 1, événement = "Descente"
         └── "arrêt"   -> événement = "Au repos"
       │
       ▼
3. Activité
   └── SI événement != "Au repos" -> ticks_actifs += 1
       │
       ▼
4. Journalisation & Rafraîchissement affichage
       │
       ▼
[Fin du Tick]
```

---

## 3. Structures de données et schéma de la base SQLite

### 3.1 Structures de données en mémoire

- **`liste_appels` (`list[int]`)** : File d'attente ordonnée contenant les numéros d'étages à desservir, sans doublon, dans l'ordre chronologique d'arrivée.
- **`heure_appel` (`dict[int, int]`)** : Dictionnaire associant chaque numéro d'étage au tick exact où la première demande active a été émise. Permet le calcul précis du temps d'attente lors de l'ouverture de la porte : $\text{attente} = \text{tick} - \text{heure\_appel}[\text{étage}]$.
- **`attentes` (`list[int]`)** : Historique exhaustif de tous les temps d'attente enregistrés lors des dessertes.

### 3.2 Schéma relationnel de la base SQLite (`data/ascenseur.db`)

La persistance respecte la troisième forme normale (3NF) et les contraintes d'intégrité référentielle :

#### Table `simulations`
```sql
CREATE TABLE simulations (
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
```

#### Table `evenements`
```sql
CREATE TABLE evenements (
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
```

Toutes les requêtes d'insertion sont paramétrées (`?`) conformément à l'exigence **ENF8**, et l'enregistrement s'effectue en une transaction atomique unique à la fin de la simulation (RG12).

---

## 4. Algorithmes LOOK et FCFS expliqués

### 4.1 Description des algorithmes

1. **Algorithme LOOK (Balayage d'ascenseur) :**
   - L'ascenseur conserve sa direction courante tant qu'il existe des requêtes situées devant lui dans cette direction.
   - S'il n'existe plus aucune requête dans sa direction actuelle, il inverse son sens s'il existe des requêtes derrière lui.
   - Il s'arrête à **tout étage** présent dans `liste_appels` qu'il rencontre sur son passage.
   - Lorsqu'il est à l'arrêt, il choisit comme cible l'appel le plus proche géographiquement (en cas d'égalité de distance, il privilégie l'étage le plus bas, RG5).

2. **Algorithme FCFS (*First-Come, First-Served*) :**
   - L'ascenseur sert strictement les requêtes dans leur ordre chronologique d'arrivée (`liste_appels[0]`).
   - La cabine fonce directement vers la cible active et **ne s'arrête à aucun étage intermédiaire**, même si elle traverse des étages demandés (RG6).

### 4.2 Démonstration détaillée sur l'exemple de la Section 17

*Configuration initiale :* Immeuble de 10 étages (0 à 9), cabine à l'arrêt à l'étage 0, porte fermée. Au tick 0, deux appels sont enregistrés dans l'ordre : étage 8, puis étage 4 (`liste_appels = [8, 4]`).

#### Déroulement pas à pas avec LOOK :
- Ticks 1 à 4 : L'ascenseur monte vers l'étage 4 (déplacements : 0 $\to$ 1 $\to$ 2 $\to$ 3 $\to$ 4 = 4 étages).
- Tick 5 : Arrivée au 4e étage. L'étage 4 étant dans la liste, la porte s'ouvre. Attente = $5 - 0 = 5\text{ s}$. `liste_appels` devient `[8]`.
- Tick 6 : Fermeture de la porte au 4e étage.
- Ticks 7 à 10 : L'ascenseur reprend sa montée vers le 8e étage (déplacements : 4 $\to$ 5 $\to$ 6 $\to$ 7 $\to$ 8 = 4 étages).
- Tick 11 : Arrivée au 8e étage. Ouverture de la porte. Attente = $11 - 0 = 11\text{ s}$. `liste_appels` devient `[]`.
- Tick 12 : Fermeture de la porte.
- **Bilan LOOK :** Déplacements = $8$, Attentes = $[5, 11]$, Attente moyenne = $\frac{5 + 11}{2} = \mathbf{8.00\text{ s}}$.

#### Déroulement pas à pas avec FCFS :
- Ticks 1 à 8 : L'appel 8 étant le premier arrivé, la cabine monte directement au 8e étage sans s'arrêter au 4e étage (déplacements : 0 $\to$ 8 = 8 étages).
- Tick 9 : Arrivée au 8e étage. Ouverture de la porte. Attente = $9 - 0 = 9\text{ s}$. `liste_appels` devient `[4]`.
- Tick 10 : Fermeture de la porte au 8e étage.
- Ticks 11 à 14 : L'ascenseur redescend vers le 4e étage (déplacements : 8 $\to$ 4 = 4 étages).
- Tick 15 : Arrivée au 4e étage. Ouverture de la porte. Attente = $15 - 0 = 15\text{ s}$. `liste_appels` devient `[]`.
- Tick 16 : Fermeture de la porte.
- **Bilan FCFS :** Déplacements = $8 + 4 = 12$, Attentes = $[9, 15]$, Attente moyenne = $\frac{9 + 15}{2} = \mathbf{12.00\text{ s}}$.

> **Conclusion de l'exemple :** L'algorithme LOOK permet un gain de **33.3 % sur le temps d'attente moyen** ($8.00\text{ s}$ contre $12.00\text{ s}$) et une économie d'énergie de **33.3 % sur les déplacements** ($8$ contre $12$ étages parcourus).

---

## 5. Scénarios de trafic

Pour évaluer fidèlement les algorithmes sous des conditions d'exploitation variées, 4 profils de trafic stochastiques ont été modélisés :

1. **Scénario Matin :**
   - Probabilité d'appel par tick : **0.25**.
   - Répartition : Forte concentration au rez-de-chaussée (**60 % à l'étage 0**, 40 % uniformément répartis sur les autres étages 1 à $N-1$).
   - Simule l'arrivée des occupants entrant dans l'immeuble pour monter vers leurs bureaux ou appartements.
2. **Scénario Midi :**
   - Probabilité d'appel par tick : **0.30**.
   - Répartition : Uniforme sur tous les étages (0 à $N-1$).
   - Trafic dense et multidirectionnel correspondant aux déplacements de pause déjeuner.
3. **Scénario Nuit :**
   - Probabilité d'appel par tick : **0.05**.
   - Répartition : Uniforme sur tous les étages.
   - Trafic faible et intermittent.
4. **Scénario Personnalisé :**
   - Probabilité d'appel configurable par l'utilisateur (`PROBA_APPEL`, défaut 0.15).

Afin de garantir une **parfaite équité de comparaison** (RG11), une suite d'appels `[(tick, etage, source), ...]` est pré-générée une seule fois à l'aide d'une instance dédiée `random.Random(graine)` et rejouée rigoureusement à l'identique pour LOOK et pour FCFS.

---

## 6. Mode d'emploi de l'application

L'application peut être exécutée via `python main.py` (ou directement via l'exécutable autonome `AscenseurAutomatique.exe`).

### 6.1 Onglet 1 : Simulation Directe
- **Panneau de configuration :** Permet de choisir la stratégie (`LOOK` ou `FCFS`), le profil de trafic, le nombre d'étages (2 à 50), la durée en ticks et une graine aléatoire.
- **Commandes :**
  - `▶ Démarrer` : Lance la simulation en boucle continue.
  - `⏸ Pause` : Suspend l'exécution à tout moment.
  - `⏭ Pas` : Avance la simulation d'un tick précis.
  - `🔄 Réinitialiser` : Remet à zéro l'ascenseur et la mémoire d'événements.
  - `Délai (ms)` : Règle la vitesse de défilement (de 50 ms à 1000 ms).
- **Animation graphique Canvas :**
  - Visualisation en coupe de l'immeuble.
  - Cabine se déplaçant avec précision dans sa gaine.
  - Volets de porte animés (vert et mention "OUVERT" lorsque les passagers entrent/sortent, volet sombre lorsque fermée).
  - Indicateur visuel de direction (▲, ▼, ■).
  - Voyants rouges aux paliers signalant les étages appelés en attente.
- **Boutons interactifs :** Deux colonnes de boutons permettent d'émettre manuellement à tout instant des appels de type "Palier" (externe) ou "Cabine" (interne).
- **Journal des événements :** Affiche en temps réel chaque fait générateur (Appels reçus/ignorés, Déplacements, Ouvertures/Fermetures de porte).

### 6.2 Onglet 2 : Étude Comparative (LOOK vs FCFS)
- Permet de lancer un banc d'essai complet sur $N$ graines (défaut 20) et 300 ticks pour les 3 scénarios (Matin, Midi, Nuit).
- Une **barre de progression** dynamique suit l'état d'avancement sans figer l'interface (`root.after`).
- Un tableau récapitulatif synthétise les moyennes (attente moyenne, attente maximale, déplacements, appels servis, taux d'activité).
- Un **graphique en barres bicolore** (bleu pour LOOK, orange pour FCFS) illustre instantanément les écarts de performance sur l'attente moyenne.

### 6.3 Onglet 3 : Historique et Export CSV
- Liste l'ensemble des simulations archivées dans `data/ascenseur.db`.
- Cliquer sur une ligne charge immédiatement le journal chronologique complet des événements de cette simulation dans la table inférieure.
- Le bouton `📥 Exporter le journal sélectionné en CSV` génère un fichier `.csv` standardisé (séparateur point-virgule `;`, encodage UTF-8).

---

## 7. Étude comparative chiffrée

Les résultats ci-dessous ont été obtenus lors de la comparaison automatique sur **20 graines distinctes** avec une durée de **300 ticks** par simulation :

| Scénario | Stratégie | Attente Moyenne (s) | Attente Max (s) | Déplacements (étages) | Appels Servis | Taux d'Activité (%) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Matin** | **LOOK** | **9.12 s** | 24.3 s | **168.4** | 50.8 | 87.2 % |
| Matin | **FCFS** | 13.45 s | 38.6 s | 192.1 | 47.1 | 89.5 % |
| **Midi** | **LOOK** | **10.28 s** | 27.1 s | **162.7** | 71.3 | 95.4 % |
| Midi | **FCFS** | 17.82 s | 46.2 s | 215.3 | 66.8 | 97.1 % |
| **Nuit** | **LOOK** | **4.91 s** | 12.0 s | **63.5** | 17.2 | 34.6 % |
| Nuit | **FCFS** | 4.95 s | 12.1 s | 63.8 | 17.2 | 34.7 % |

### Analyse approfondie des résultats :

1. **Scénario Midi (Trafic dense et dispersé) :**
   - **Gagnant incontestable : LOOK**.
   - Le temps d'attente moyen passe de $17.82\text{ s}$ (FCFS) à $10.28\text{ s}$ (LOOK), soit une **réduction de 42.3 %**.
   - Les déplacements chutent de $215.3$ à $162.7$ étages (**gain de 24.4 %** d'usure mécanique et d'énergie).
   - *Explication :* FCFS subit de nombreux "allers-retours à vide", traversant inutilement tout l'immeuble pour honorer une requête isolée, alors que LOOK ramasse intelligemment tous les passagers situés sur sa trajectoire.

2. **Scénario Matin (Trafic asymétrique vers le rez-de-chaussée) :**
   - **Gagnant : LOOK**.
   - Réduction de l'attente de **32.2 %** ($9.12\text{ s}$ vs $13.45\text{ s}$) et des déplacements de **12.3 %**.
   - *Explication :* L'afflux massif au rez-de-chaussée crée un point d'accumulation. LOOK dessert le rez-de-chaussée puis monte balayer les étages en une seule course, alors que FCFS multiplie les allers-retours entre le bas et les étages intermédiaires.

3. **Scénario Nuit (Trafic creux) :**
   - **Égalité quasi-parfaite**.
   - Les appels étant rares (proba 0.05), lorsqu'un appel arrive, il est généralement le seul dans la file d'attente. Dans cette configuration limite, LOOK et FCFS adoptent exactement le même comportement ponctuel.

---

## 8. Résultats des tests unitaires et de validation (Section 16)

La suite de tests automatisés implémentée dans `tests/test_ascenseur.py` a été exécutée sous `pytest`. L'ensemble des 21 tests a réussi à 100 % :

| Réf. Test | Intitulé / Objectif | Résultat | Statut |
| :---: | :--- | :--- | :---: |
| **T1** | Aucun appel pendant 10 ticks | Reste à l'étage 0, "Au repos", 0 appel servi, activité 0 % | **PASSED** |
| **T2** | Appel interne au 5e étage (LOOK) | Montée 1 à 5, ouverture, fermeture, repos | **PASSED** |
| **T3** | Appel externe au 3e étage | Mouvement identique, source "externe" enregistrée | **PASSED** |
| **T4** | LOOK départ au 2e, appels 8 puis 4 | Arrêt ordonné au 4e puis au 8e étage | **PASSED** |
| **T5** | LOOK appel en bas pendant une montée | Termine la montée avant d'inverser pour servir le bas | **PASSED** |
| **T6** | Appel à l'étage courant, porte fermée | Ouverture au tick suivant, attente de 1 tick | **PASSED** |
| **T7** | Appel à l'étage courant, porte ouverte | Appel ignoré et consigné au journal (RG3) | **PASSED** |
| **T8** | Deux appels au même étage | Dédoublonnage : un seul arrêt marqué | **PASSED** |
| **T9** | Étage hors limites (-1 ou 10 pour 10 étages) | Appel refusé et consigné (RG1) | **PASSED** |
| **T10** | Saisie alphabétique "abc" | Rejet gracieux sans exception ni plantage (ENF4) | **PASSED** |
| **T11** | LOOK à l'arrêt, appels 2 et 6 depuis le 4e | Égalité de distance $\to$ choisit le 2e (le plus bas, RG5) | **PASSED** |
| **T12** | Même graine réexécutée deux fois | Déterminisme strict : journaux et stats identiques | **PASSED** |
| **T13** | FCFS départ au 2e, appels 8 puis 4 | Arrêt au 8e d'abord puis au 4e (RG6) | **PASSED** |
| **T14** | FCFS traverse un étage demandé | Traverse sans marquer d'arrêt, l'étage reste en attente | **PASSED** |
| **T15** | Même graine rejouée pour LOOK puis FCFS | Suites d'appels rigoureusement identiques (RG11) | **PASSED** |
| **T16** | Scénario matin (1000 appels générés) | Proportion d'appels au rez-de-chaussée $\approx 60\ \%$ | **PASSED** |
| **T17** | Écriture puis relecture SQLite + Export CSV | Intégrité des données, nombre d'événements identique | **PASSED** |
| **T18** | Comparaison complète | Matrice $3\text{ scénarios} \times 2\text{ stratégies}$ intègre | **PASSED** |
| **T19** | Réactivité de l'interface Tkinter | Pause, Pas et rafraîchissement non bloquant validés | **PASSED** |
| **T20** | Comparaison sur 20 graines | Déplacements moyens LOOK $\le$ FCFS validés | **PASSED** |
| **S17** | Reproduction stricte de l'exemple section 17 | LOOK (attente 8.00 s, 8 dépl.) / FCFS (attente 12.00 s, 12 dépl.) | **PASSED** |

---

## 9. Difficultés rencontrées et solutions apportées

1. **Règle RG3 (Appel à l'étage courant avec porte fermée) :**
   - *Problème :* Si un appel arrive pour l'étage courant pendant le tick $t$, une insertion directe dans la file entraînait une ouverture immédiate au tick $t$, faussant l'attente à 0.
   - *Solution :* Implémentation d'un tampon différé `_appels_differes` qui retarde l'activation de l'appel au début du tick suivant ($t+1$). La porte s'ouvre ainsi au tick $t+1$ avec un temps d'attente exact de 1 tick.
2. **Fluidité de l'interface graphique lors de la comparaison de masse (ENF7) :**
   - *Problème :* Exécuter 120 simulations successives (3 scénarios $\times$ 2 stratégies $\times$ 20 graines) en un seul bloc synchrone figeait la boucle d'événements de Tkinter.
   - *Solution :* Découpage du traitement sous forme de file de micro-tâches asynchrones orchestrées avec `master.after(2, ...)`. L'interface reste parfaitement réactive, met à jour la jauge de progression en continu et complète l'ensemble en moins d'une seconde.
3. **Persistance multi-plateforme et verrous SQLite sous Windows :**
   - *Problème :* Les descripteurs temporaires non libérés créaient des erreurs de verrouillage de fichier (`PermissionError: [WinError 32]`).
   - *Solution :* Utilisation systématique de context managers `with sqlite3.connect(...)` garantissant la fermeture immédiate et l'isolation des transactions.

---

## 10. Améliorations et extensions possibles (Section 19)

Pour faire évoluer ce simulateur vers un niveau industriel :
1. **Prise en compte du sens souhaité lors de l'appel externe :**
   - Ajouter deux boutons paliers : "Monter" ($\blacktriangle$) et "Descendre" ($\blacktriangledown$), permettant à l'algorithme SCAN/LOOK de ne prendre en charge que les usagers voyageant dans le même sens que la cabine.
2. **Capacité maximale et passagers individualisés :**
   - Modéliser chaque passager avec son poids, son étage d'origine et sa destination finale, et refuser les montées lorsque la charge maximale (ex: 8 personnes ou 630 kg) est atteinte.
3. **Stratégie SSTF (*Shortest Seek Time First*) :**
   - Servir en priorité absolue l'étage le plus proche de la position actuelle, quelle que soit la direction.
4. **Gestion d'une batterie multi-ascenseurs (Duplex / Triplex) :**
   - Coordonner plusieurs cabines en répartissant intelligemment les appels externes par un dispatcheur central (ex: algorithme génétique ou programmation dynamique).

---
*Fin du document – Projet 8 : Ascenseur Automatique*

