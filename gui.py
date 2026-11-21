"""Module gui.py
Interface graphique Tkinter complète et ergonomique pour la simulation d'ascenseur automatique.
Respecte les exigences EF11 à EF16, ENF4 (validation sans plantage) et la section 13 (3 onglets, Canvas, root.after).
"""

import os
import sys
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Any, Optional

from strategies import LOOK, FCFS
from immeuble import Immeuble
from ascenseur import Ascenseur
from scenarios import obtenir_scenario, generer_suite_appels, Scenario
from statistiques import calculer_statistiques, formater_statistiques
from base_donnees import (
    enregistrer_simulation,
    lire_historique,
    lire_evenements_simulation,
    exporter_csv,
    DB_FILE,
)
from comparaison import executer_comparaison


class ApplicationAscenseur(ttk.Notebook):
    """Fenêtre principale à onglets pour la simulation de l'ascenseur."""

    def __init__(self, master: tk.Tk) -> None:
        super().__init__(master)
        self.master = master
        self.master.title("Simulation & Étude Comparative - Ascenseur Automatique")
        self.master.geometry("1100x780")
        self.master.minsize(950, 680)

        # Style visuel moderne
        self._configurer_styles()

        # Onglets principaux
        self.onglet_simulation = ttk.Frame(self)
        self.onglet_comparaison = ttk.Frame(self)
        self.onglet_historique = ttk.Frame(self)

        self.add(self.onglet_simulation, text="  🏢 Simulation Directe  ")
        self.add(self.onglet_comparaison, text="  📊 Étude Comparative (LOOK vs FCFS)  ")
        self.add(self.onglet_historique, text="  📜 Historique & Base SQLite  ")

        # Initialisation du contenu de chaque onglet
        self._init_onglet_simulation()
        self._init_onglet_comparaison()
        self._init_onglet_historique()

        self.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    def _configurer_styles(self) -> None:
        """Configure les polices et couleurs de l'interface ttk."""
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook.Tab", font=("Helvetica", 10, "bold"), padding=[10, 4])
        style.configure("TLabel", font=("Helvetica", 9))
        style.configure("TButton", font=("Helvetica", 9), padding=4)
        style.configure("Header.TLabel", font=("Helvetica", 11, "bold"))
        style.configure("Stat.TLabel", font=("Helvetica", 9, "bold"), foreground="#1a365d")

    # =========================================================================
    # ONGLET 1 : SIMULATION DIRECTE
    # =========================================================================

    def _init_onglet_simulation(self) -> None:
        """Initialise les composants de l'onglet Simulation."""
        # Variables de contrôle
        self.var_nb_etages = tk.IntVar(value=10)
        self.var_duree = tk.IntVar(value=100)
        self.var_strategie = tk.StringVar(value="LOOK")
        self.var_scenario = tk.StringVar(value="matin")
        self.var_proba_perso = tk.DoubleVar(value=0.15)
        self.var_graine = tk.StringVar(value="")
        self.var_vitesse = tk.IntVar(value=300)  # ms par tick

        self.en_cours = False
        self.tick_actuel = 0
        self.ascenseur: Optional[Ascenseur] = None
        self.appels_pregeneres: dict[int, list[tuple[int, str]]] = {}
        self.evenements_session: list[dict[str, Any]] = []

        # Division en deux panneaux verticaux : Gauche (Contrôles & Journal) et Droite (Canvas Immeuble)
        panneau_gauche = ttk.Frame(self.onglet_simulation, padding=8)
        panneau_gauche.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        panneau_droite = ttk.Frame(self.onglet_simulation, padding=8)
        panneau_droite.pack(side=tk.RIGHT, fill=tk.BOTH)

        # 1. Groupe Paramètres
        lbl_cadre_params = ttk.LabelFrame(panneau_gauche, text=" Paramètres de la simulation ", padding=6)
        lbl_cadre_params.pack(fill=tk.X, pady=(0, 6))

        grid_params = ttk.Frame(lbl_cadre_params)
        grid_params.pack(fill=tk.X)

        # Ligne 1 : Stratégie & Scénario
        ttk.Label(grid_params, text="Stratégie :").grid(row=0, column=0, sticky=tk.W, padx=4, pady=2)
        cb_strat = ttk.Combobox(grid_params, textvariable=self.var_strategie, values=["LOOK", "FCFS"], state="readonly", width=10)
        cb_strat.grid(row=0, column=1, padx=4, pady=2)

        ttk.Label(grid_params, text="Scénario :").grid(row=0, column=2, sticky=tk.W, padx=4, pady=2)
        cb_scen = ttk.Combobox(grid_params, textvariable=self.var_scenario, values=["matin", "midi", "nuit", "personnalisé"], state="readonly", width=12)
        cb_scen.grid(row=0, column=3, padx=4, pady=2)

        # Ligne 2 : Étages & Durée
        ttk.Label(grid_params, text="Nb d'étages (2-50) :").grid(row=1, column=0, sticky=tk.W, padx=4, pady=2)
        ttk.Entry(grid_params, textvariable=self.var_nb_etages, width=12).grid(row=1, column=1, padx=4, pady=2)

        ttk.Label(grid_params, text="Durée (ticks) :").grid(row=1, column=2, sticky=tk.W, padx=4, pady=2)
        ttk.Entry(grid_params, textvariable=self.var_duree, width=14).grid(row=1, column=3, padx=4, pady=2)

        # Ligne 3 : Graine & Proba personnalisée
        ttk.Label(grid_params, text="Graine (facultatif) :").grid(row=2, column=0, sticky=tk.W, padx=4, pady=2)
        ttk.Entry(grid_params, textvariable=self.var_graine, width=12).grid(row=2, column=1, padx=4, pady=2)

        ttk.Label(grid_params, text="Proba (si perso) :").grid(row=2, column=2, sticky=tk.W, padx=4, pady=2)
        ttk.Entry(grid_params, textvariable=self.var_proba_perso, width=14).grid(row=2, column=3, padx=4, pady=2)

        # 2. Groupe Commandes & Vitesse
        cadre_actions = ttk.Frame(panneau_gauche)
        cadre_actions.pack(fill=tk.X, pady=4)

        self.btn_demarrer = ttk.Button(cadre_actions, text="▶ Démarrer", command=self._action_demarrer)
        self.btn_demarrer.pack(side=tk.LEFT, padx=3)

        self.btn_pause = ttk.Button(cadre_actions, text="⏸ Pause", command=self._action_pause, state=tk.DISABLED)
        self.btn_pause.pack(side=tk.LEFT, padx=3)

        self.btn_pas = ttk.Button(cadre_actions, text="⏭ Pas (1 tick)", command=self._action_pas)
        self.btn_pas.pack(side=tk.LEFT, padx=3)

        self.btn_reinit = ttk.Button(cadre_actions, text="🔄 Réinitialiser", command=self._action_reinitialiser)
        self.btn_reinit.pack(side=tk.LEFT, padx=3)

        # Curseur de vitesse
        cadre_vitesse = ttk.Frame(cadre_actions)
        cadre_vitesse.pack(side=tk.RIGHT, padx=6)
        ttk.Label(cadre_vitesse, text="Délai (ms) :").pack(side=tk.LEFT)
        scale_vitesse = ttk.Scale(cadre_vitesse, from_=50, to=1000, variable=self.var_vitesse, orient=tk.HORIZONTAL, length=110)
        scale_vitesse.pack(side=tk.LEFT, padx=4)

        # 3. Groupe Statistiques en direct
        lbl_cadre_stats = ttk.LabelFrame(panneau_gauche, text=" Indicateurs en direct ", padding=6)
        lbl_cadre_stats.pack(fill=tk.X, pady=4)

        self.lbl_tick_info = ttk.Label(lbl_cadre_stats, text="Tick : 0 / 100 | État : À l'arrêt", style="Stat.TLabel")
        self.lbl_tick_info.pack(anchor=tk.W, pady=1)

        self.lbl_stats_details = ttk.Label(
            lbl_cadre_stats,
            text="Appels servis : 0 | Attente moy : 0.00 s | Attente max : 0 s | Déplacements : 0 | Activité : 0.0 %",
        )
        self.lbl_stats_details.pack(anchor=tk.W, pady=1)

        # 4. Groupe Journal des événements
        lbl_cadre_journal = ttk.LabelFrame(panneau_gauche, text=" Journal des événements (Section 12) ", padding=4)
        lbl_cadre_journal.pack(fill=tk.BOTH, expand=True, pady=4)

        colonnes = ("tick", "etage", "direction", "evenement", "source", "appels")
        self.tree_journal = ttk.Treeview(lbl_cadre_journal, columns=colonnes, show="headings", height=9)
        self.tree_journal.heading("tick", text="Tick")
        self.tree_journal.heading("etage", text="Étage")
        self.tree_journal.heading("direction", text="Direction")
        self.tree_journal.heading("evenement", text="Événement")
        self.tree_journal.heading("source", text="Source")
        self.tree_journal.heading("appels", text="File d'attente")

        self.tree_journal.column("tick", width=50, anchor=tk.CENTER)
        self.tree_journal.column("etage", width=55, anchor=tk.CENTER)
        self.tree_journal.column("direction", width=75, anchor=tk.CENTER)
        self.tree_journal.column("evenement", width=120, anchor=tk.W)
        self.tree_journal.column("source", width=70, anchor=tk.CENTER)
        self.tree_journal.column("appels", width=120, anchor=tk.W)

        scroll_journal = ttk.Scrollbar(lbl_cadre_journal, orient=tk.VERTICAL, command=self.tree_journal.yview)
        self.tree_journal.configure(yscrollcommand=scroll_journal.set)
        self.tree_journal.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_journal.pack(side=tk.RIGHT, fill=tk.Y)

        # 5. Panneau de droite : Visualisation Canvas Immeuble & Boutons d'appel
        lbl_cadre_immeuble = ttk.LabelFrame(panneau_droite, text=" Visualisation Immeuble & Appels ", padding=6)
        lbl_cadre_immeuble.pack(fill=tk.BOTH, expand=True)

        # Canvas pour dessiner la gaine d'ascenseur et les étages
        self.canvas_hauteur = 460
        self.canvas_largeur = 230
        self.canvas_immeuble = tk.Canvas(
            lbl_cadre_immeuble,
            width=self.canvas_largeur,
            height=self.canvas_hauteur,
            bg="#f0f4f8",
            highlightthickness=1,
            highlightbackground="#cbd5e1",
        )
        self.canvas_immeuble.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        # Panneau de boutons d'appel (externes et internes) avec scrollbar si beaucoup d'étages
        cadre_appels = ttk.Frame(lbl_cadre_immeuble)
        cadre_appels.pack(side=tk.RIGHT, fill=tk.Y, padx=4)

        ttk.Label(cadre_appels, text="Appels externes / cabine", style="Header.TLabel").pack(pady=2)

        canvas_btn = tk.Canvas(cadre_appels, width=150, height=self.canvas_hauteur - 40, highlightthickness=0)
        scroll_btn = ttk.Scrollbar(cadre_appels, orient=tk.VERTICAL, command=canvas_btn.yview)
        self.frame_boutons_etages = ttk.Frame(canvas_btn)

        self.frame_boutons_etages.bind(
            "<Configure>", lambda e: canvas_btn.configure(scrollregion=canvas_btn.bbox("all"))
        )
        canvas_btn.create_window((0, 0), window=self.frame_boutons_etages, anchor="nw")
        canvas_btn.configure(yscrollcommand=scroll_btn.set)

        canvas_btn.pack(side=tk.LEFT, fill=tk.BOTH)
        scroll_btn.pack(side=tk.RIGHT, fill=tk.Y)

        # Construction initiale de l'ascenseur
        self._action_reinitialiser()

    def _valider_entrees(self) -> tuple[bool, str]:
        """Vérifie la validité des champs de saisie (ENF4 : aucune saisie ne provoque de plantage)."""
        try:
            nb = int(self.var_nb_etages.get())
            if not (2 <= nb <= 50):
                return False, "Le nombre d'étages doit être compris entre 2 et 50."
        except Exception:
            return False, "Le nombre d'étages doit être un entier valide."

        try:
            duree = int(self.var_duree.get())
            if duree < 1:
                return False, "La durée de simulation doit être un entier supérieur ou égal à 1."
        except Exception:
            return False, "La durée doit être un entier valide."

        try:
            p = float(self.var_proba_perso.get())
            if not (0.0 <= p <= 1.0):
                return False, "La probabilité d'appel doit être comprise entre 0.0 et 1.0."
        except Exception:
            return False, "La probabilité d'appel doit être un nombre réel (ex: 0.15)."

        graine_str = self.var_graine.get().strip()
        if graine_str:
            try:
                int(graine_str)
            except Exception:
                return False, "La graine doit être un entier facultatif."

        return True, ""

    def _action_reinitialiser(self) -> None:
        """Réinitialise complètement l'état de la simulation."""
        self.en_cours = False
        self.btn_demarrer.config(state=tk.NORMAL)
        self.btn_pause.config(state=tk.DISABLED)
        self.btn_pas.config(state=tk.NORMAL)

        valide, msg = self._valider_entrees()
        if not valide:
            messagebox.showerror("Erreur de configuration", msg)
            return

        nb_etages = self.var_nb_etages.get()
        strat_nom = self.var_strategie.get()
        strat = LOOK() if strat_nom == "LOOK" else FCFS()

        self.immeuble = Immeuble(nb_etages)
        self.ascenseur = Ascenseur(self.immeuble, etage_initial=0, strategie=strat)
        self.tick_actuel = 0
        self.evenements_session = []

        # Génération ou préparation de la suite d'appels
        sc_nom = self.var_scenario.get()
        scenario = obtenir_scenario(sc_nom, self.var_proba_perso.get())
        duree = self.var_duree.get()
        graine_str = self.var_graine.get().strip()
        graine = int(graine_str) if graine_str else None

        self.appels_pregeneres = generer_suite_appels(scenario, nb_etages, duree, graine)

        # Nettoyage du journal
        for row in self.tree_journal.get_children():
            self.tree_journal.delete(row)

        self._mettre_a_jour_boutons_appels()
        self._rafraichir_canvas()
        self._mettre_a_jour_stats()

    def _mettre_a_jour_boutons_appels(self) -> None:
        """Génère les boutons d'appel (palier externe et cabine interne) pour chaque étage."""
        for widget in self.frame_boutons_etages.winfo_children():
            widget.destroy()

        nb_etages = self.var_nb_etages.get()
        # Affichage du plus haut étage au plus bas (comme un immeuble)
        for etage in range(nb_etages - 1, -1, -1):
            cadre_e = ttk.Frame(self.frame_boutons_etages, padding=1)
            cadre_e.pack(fill=tk.X, pady=1)

            lbl = ttk.Label(cadre_e, text=f"Étage {etage:2d}:", width=8)
            lbl.pack(side=tk.LEFT)

            btn_ext = ttk.Button(
                cadre_e,
                text="🔔 Palier",
                width=7,
                command=lambda e=etage: self._appel_manuel(e, "externe"),
            )
            btn_ext.pack(side=tk.LEFT, padx=1)

            btn_int = ttk.Button(
                cadre_e,
                text="🚪 Cabine",
                width=7,
                command=lambda e=etage: self._appel_manuel(e, "interne"),
            )
            btn_int.pack(side=tk.LEFT, padx=1)

    def _appel_manuel(self, etage: int, source: str) -> None:
        """Gère la saisie manuelle d'un appel par l'utilisateur (CU3, EF8)."""
        if self.ascenseur is None:
            return
        succes, raison, evt = self.ascenseur.ajouter_appel(etage, source, self.tick_actuel)
        self.evenements_session.append(evt)
        self._ajouter_au_journal(evt)
        self._rafraichir_canvas()
        self._mettre_a_jour_stats()

    def _action_demarrer(self) -> None:
        """Démarre ou reprend la simulation automatique."""
        if not self.en_cours:
            self.en_cours = True
            self.btn_demarrer.config(state=tk.DISABLED)
            self.btn_pause.config(state=tk.NORMAL)
            self.btn_pas.config(state=tk.DISABLED)
            self._boucle_simulation()

    def _action_pause(self) -> None:
        """Met en pause la simulation."""
        self.en_cours = False
        self.btn_demarrer.config(state=tk.NORMAL)
        self.btn_pause.config(state=tk.DISABLED)
        self.btn_pas.config(state=tk.NORMAL)

    def _action_pas(self) -> None:
        """Exécute un tick unique en mode pas à pas."""
        if self.ascenseur is None:
            self._action_reinitialiser()
        self._executer_un_tick()

    def _boucle_simulation(self) -> None:
        """Boucle d'exécution continue non bloquante avec root.after()."""
        if not self.en_cours:
            return

        fini = self._executer_un_tick()
        if fini:
            self._action_pause()
            self._enregistrer_fin_simulation()
        else:
            delai = max(20, self.var_vitesse.get())
            self.master.after(delai, self._boucle_simulation)

    def _executer_un_tick(self) -> bool:
        """Exécute les opérations du tick courant.

        :return: True si la simulation est terminée, False sinon.
        """
        if self.ascenseur is None:
            return True

        duree_max = self.var_duree.get()
        if self.tick_actuel >= duree_max:
            return True

        self.tick_actuel += 1
        nouveaux_appels = self.appels_pregeneres.get(self.tick_actuel, [])

        evts = self.ascenseur.pas(self.tick_actuel, nouveaux_appels)
        for e in evts:
            self.evenements_session.append(e)
            self._ajouter_au_journal(e)

        self._rafraichir_canvas()
        self._mettre_a_jour_stats()

        if self.tick_actuel >= duree_max:
            return True
        return False

    def _ajouter_au_journal(self, evt: dict[str, Any]) -> None:
        """Ajoute un événement au tableau visuel du journal."""
        appels_txt = ", ".join(map(str, evt.get("appels", [])))
        self.tree_journal.insert(
            "",
            0,  # En haut pour voir immédiatement le dernier événement
            values=(
                evt["tick"],
                evt["etage"],
                evt["direction"],
                evt["evenement"],
                evt.get("source", ""),
                appels_txt,
            ),
        )

    def _mettre_a_jour_stats(self) -> None:
        """Met à jour l'affichage des métriques en direct."""
        if self.ascenseur is None:
            return

        duree = self.var_duree.get()
        dir_symbole = "■ (Au repos)"
        if self.ascenseur.direction == "monte":
            dir_symbole = "▲ (Montée)"
        elif self.ascenseur.direction == "descend":
            dir_symbole = "▼ (Descente)"

        porte_txt = "Ouverte" if self.ascenseur.porte_ouverte else "Fermée"
        self.lbl_tick_info.config(
            text=f"Tick : {self.tick_actuel} / {duree} | Étage actuel : {self.ascenseur.etage_actuel} | Direction : {dir_symbole} | Porte : {porte_txt}"
        )

        stats = calculer_statistiques(
            attentes=self.ascenseur.attentes,
            ticks_actifs=self.ascenseur.ticks_actifs,
            ticks_totaux=max(1, self.tick_actuel),
            nb_servis=self.ascenseur.nb_servis,
            nb_deplacements=self.ascenseur.nb_deplacements,
        )
        self.lbl_stats_details.config(text=formater_statistiques(stats))

    def _rafraichir_canvas(self) -> None:
        """Dessine graphiquement l'immeuble, la gaine, la cabine et les indicateurs sur le Canvas."""
        self.canvas_immeuble.delete("all")
        if self.ascenseur is None:
            return

        nb_etages = self.ascenseur.immeuble.nb_etages
        h_totale = self.canvas_hauteur - 20
        h_etage = h_totale / max(1, nb_etages)

        gaine_x1 = 60
        gaine_x2 = 180

        # Dessin de chaque étage
        for etage in range(nb_etages):
            y_bas = self.canvas_hauteur - 10 - (etage * h_etage)
            y_haut = y_bas - h_etage

            # Ligne de sol
            self.canvas_immeuble.create_line(gaine_x1 - 30, y_bas, gaine_x2 + 30, y_bas, fill="#94a3b8", width=1)

            # Numéro de l'étage
            self.canvas_immeuble.create_text(
                gaine_x1 - 15,
                (y_haut + y_bas) / 2,
                text=str(etage),
                font=("Helvetica", 9, "bold"),
                fill="#334155",
            )

            # Voyant d'appel si cet étage est demandé
            if etage in self.ascenseur.liste_appels:
                self.canvas_immeuble.create_oval(
                    gaine_x2 + 10,
                    (y_haut + y_bas) / 2 - 5,
                    gaine_x2 + 20,
                    (y_haut + y_bas) / 2 + 5,
                    fill="#ef4444",
                    outline="#b91c1c",
                )

        # Dessin des rails de guidage
        self.canvas_immeuble.create_line(gaine_x1, 10, gaine_x1, self.canvas_hauteur - 10, fill="#64748b", width=2)
        self.canvas_immeuble.create_line(gaine_x2, 10, gaine_x2, self.canvas_hauteur - 10, fill="#64748b", width=2)

        # Dessin de la cabine mobile
        cabine_etage = self.ascenseur.etage_actuel
        y_cabine_bas = self.canvas_hauteur - 10 - (cabine_etage * h_etage)
        y_cabine_haut = y_cabine_bas - h_etage + 2

        couleur_cabine = "#3b82f6"  # Bleu
        self.canvas_immeuble.create_rectangle(
            gaine_x1 + 4,
            y_cabine_haut + 2,
            gaine_x2 - 4,
            y_cabine_bas - 2,
            fill=couleur_cabine,
            outline="#1d4ed8",
            width=2,
        )

        # Dessin de la porte (verte si ouverte, grise si fermée)
        if self.ascenseur.porte_ouverte:
            # Porte ouverte : deux volets coulissés sur les côtés
            self.canvas_immeuble.create_rectangle(
                gaine_x1 + 6, y_cabine_haut + 4, gaine_x1 + 20, y_cabine_bas - 4, fill="#10b981", outline="#047857"
            )
            self.canvas_immeuble.create_rectangle(
                gaine_x2 - 20, y_cabine_haut + 4, gaine_x2 - 6, y_cabine_bas - 4, fill="#10b981", outline="#047857"
            )
            self.canvas_immeuble.create_text(
                (gaine_x1 + gaine_x2) / 2,
                (y_cabine_haut + y_cabine_bas) / 2,
                text="OUVERT",
                font=("Helvetica", 7, "bold"),
                fill="#ffffff",
            )
        else:
            # Porte fermée : volet central
            self.canvas_immeuble.create_rectangle(
                gaine_x1 + 25, y_cabine_haut + 4, gaine_x2 - 25, y_cabine_bas - 4, fill="#1e293b", outline="#0f172a"
            )

        # Flèche de direction sur la cabine
        fleche = "■"
        if self.ascenseur.direction == "monte":
            fleche = "▲"
        elif self.ascenseur.direction == "descend":
            fleche = "▼"
        self.canvas_immeuble.create_text(
            (gaine_x1 + gaine_x2) / 2,
            y_cabine_haut - 6,
            text=fleche,
            font=("Helvetica", 10, "bold"),
            fill="#dc2626" if fleche != "■" else "#64748b",
        )

    def _enregistrer_fin_simulation(self) -> None:
        """Enregistre la simulation terminée dans la base SQLite et affiche le résumé (EF16, RG12)."""
        if self.ascenseur is None:
            return

        duree = self.var_duree.get()
        stats = calculer_statistiques(
            attentes=self.ascenseur.attentes,
            ticks_actifs=self.ascenseur.ticks_actifs,
            ticks_totaux=self.tick_actuel,
            nb_servis=self.ascenseur.nb_servis,
            nb_deplacements=self.ascenseur.nb_deplacements,
        )

        graine_str = self.var_graine.get().strip()
        graine = int(graine_str) if graine_str else None

        donnees_sim = {
            "date_heure": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "strategie": self.ascenseur.strategie.nom,
            "scenario": self.var_scenario.get(),
            "graine": graine,
            "nb_etages": self.ascenseur.immeuble.nb_etages,
            "duree": self.tick_actuel,
            **stats,
        }

        try:
            sim_id = enregistrer_simulation(donnees_sim, self.evenements_session)
            # Rafraîchir l'historique
            self._actualiser_liste_historique()

            # Résumé de fin de simulation (EF16)
            appels_restants = len(self.ascenseur.liste_appels)
            resume = (
                f"Simulation terminée (ID #{sim_id}) !\n\n"
                f"• Stratégie : {donnees_sim['strategie']}\n"
                f"• Scénario : {donnees_sim['scenario']}\n"
                f"• Appels servis : {stats['appels_servis']}\n"
                f"• Appels non servis : {appels_restants}\n"
                f"• Attente moyenne : {stats['attente_moyenne']:.2f} s\n"
                f"• Attente maximale : {stats['attente_max']} s\n"
                f"• Déplacements : {stats['deplacements']} étages\n"
                f"• Taux d'activité : {stats['taux_occupation']:.1f} %\n\n"
                "La simulation a été enregistrée avec succès dans la base SQLite."
            )
            messagebox.showinfo("Résumé de fin de simulation", resume)
        except Exception as e:
            messagebox.showwarning("Enregistrement", f"Erreur lors de l'enregistrement SQLite : {e}")

    # =========================================================================
    # ONGLET 2 : ÉTUDE COMPARATIVE (LOOK vs FCFS)
    # =========================================================================

    def _init_onglet_comparaison(self) -> None:
        """Initialise l'onglet d'étude comparative (EF12, EF13, EF14)."""
        cadre_haut = ttk.LabelFrame(self.onglet_comparaison, text=" Configuration du banc d'essai comparatif ", padding=8)
        cadre_haut.pack(fill=tk.X, padx=8, pady=6)

        self.var_comp_graines = tk.IntVar(value=20)
        self.var_comp_duree = tk.IntVar(value=300)

        grid_c = ttk.Frame(cadre_haut)
        grid_c.pack(fill=tk.X)

        ttk.Label(grid_c, text="Nombre de graines (défaut 20) :").grid(row=0, column=0, padx=4, pady=2, sticky=tk.W)
        ttk.Entry(grid_c, textvariable=self.var_comp_graines, width=10).grid(row=0, column=1, padx=4, pady=2)

        ttk.Label(grid_c, text="Durée par simulation (défaut 300) :").grid(row=0, column=2, padx=4, pady=2, sticky=tk.W)
        ttk.Entry(grid_c, textvariable=self.var_comp_duree, width=10).grid(row=0, column=3, padx=4, pady=2)

        self.btn_lancer_comp = ttk.Button(grid_c, text="🚀 Lancer la comparaison (RG11)", command=self._action_lancer_comparaison)
        self.btn_lancer_comp.grid(row=0, column=4, padx=12, pady=2)

        self.progress_bar = ttk.Progressbar(cadre_haut, orient=tk.HORIZONTAL, mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=(6, 2))

        self.lbl_progress = ttk.Label(cadre_haut, text="Prêt à lancer l'analyse comparative.")
        self.lbl_progress.pack(anchor=tk.W)

        # Tableau comparatif (EF13)
        cadre_tableau = ttk.LabelFrame(self.onglet_comparaison, text=" Tableau comparatif des moyennes ", padding=6)
        cadre_tableau.pack(fill=tk.X, padx=8, pady=4)

        colonnes = ("scenario", "strategie", "attente_moy", "attente_max", "deplacements", "servis", "taux")
        self.tree_comp = ttk.Treeview(cadre_tableau, columns=colonnes, show="headings", height=7)
        self.tree_comp.heading("scenario", text="Scénario")
        self.tree_comp.heading("strategie", text="Stratégie")
        self.tree_comp.heading("attente_moy", text="Attente Moyenne (s)")
        self.tree_comp.heading("attente_max", text="Attente Max (s)")
        self.tree_comp.heading("deplacements", text="Déplacements Moyens")
        self.tree_comp.heading("servis", text="Appels Servis")
        self.tree_comp.heading("taux", text="Taux d'activité (%)")

        for col in colonnes:
            self.tree_comp.column(col, anchor=tk.CENTER)

        self.tree_comp.pack(fill=tk.X)

        # Graphique en barres (EF14) dessiné sur Canvas
        cadre_graphique = ttk.LabelFrame(self.onglet_comparaison, text=" Graphique en barres : Attente moyenne par stratégie et par scénario (EF14) ", padding=6)
        cadre_graphique.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        self.canvas_graphique = tk.Canvas(cadre_graphique, bg="#ffffff", highlightthickness=1, highlightbackground="#cbd5e1")
        self.canvas_graphique.pack(fill=tk.BOTH, expand=True)

    def _action_lancer_comparaison(self) -> None:
        """Exécute la comparaison LOOK vs FCFS par étapes non bloquantes avec root.after()."""
        try:
            nb_graines = int(self.var_comp_graines.get())
            duree = int(self.var_comp_duree.get())
            if nb_graines < 1 or duree < 1:
                raise ValueError
        except Exception:
            messagebox.showerror("Erreur", "Veuillez entrer des entiers positifs valides.")
            return

        self.btn_lancer_comp.config(state=tk.DISABLED)
        scenarios_noms = ["matin", "midi", "nuit"]
        total_etapes = len(scenarios_noms) * nb_graines * 2
        self.progress_bar["maximum"] = total_etapes
        self.progress_bar["value"] = 0

        graines = [1000 + i for i in range(nb_graines)]
        taches: list[dict[str, Any]] = []

        # Construction de la pile de simulations à exécuter
        for sc_nom in scenarios_noms:
            sc = obtenir_scenario(sc_nom)
            for g in graines:
                # Pré-génération conforme RG11
                appels = generer_suite_appels(sc, 10, duree, g)
                taches.append({"sc": sc_nom, "strat": "LOOK", "appels": appels, "duree": duree, "graine": g})
                taches.append({"sc": sc_nom, "strat": "FCFS", "appels": appels, "duree": duree, "graine": g})

        resultats_bruts: dict[str, dict[str, list[dict[str, Any]]]] = {
            sc: {"LOOK": [], "FCFS": []} for sc in scenarios_noms
        }

        def executer_etape(idx: int) -> None:
            if idx >= len(taches):
                self._finaliser_comparaison(resultats_bruts, scenarios_noms)
                return

            tache = taches[idx]
            strat_obj = LOOK() if tache["strat"] == "LOOK" else FCFS()
            stats, _, _ = lancer(
                strategie=strat_obj,
                appels=tache["appels"],
                duree=tache["duree"],
                nb_etages=10,
                mode_comparaison=True,
            )
            resultats_bruts[tache["sc"]][tache["strat"]].append(stats)

            self.progress_bar["value"] = idx + 1
            pourcent = int(((idx + 1) / total_etapes) * 100)
            self.lbl_progress.config(
                text=f"Progression : {pourcent}% | {tache['sc'].capitalize()} - {tache['strat']} (Graine {tache['graine']})"
            )

            # Prochaine étape cédée au gestionnaire d'événements Tkinter
            self.master.after(2, lambda: executer_etape(idx + 1))

        executer_etape(0)

    def _finaliser_comparaison(
        self, resultats_bruts: dict[str, dict[str, list[dict[str, Any]]]], scenarios_noms: list[str]
    ) -> None:
        """Calcule les moyennes, remplit le tableau et trace le graphique en barres."""
        self.btn_lancer_comp.config(state=tk.NORMAL)
        self.lbl_progress.config(text="Comparaison terminée avec succès ! Résultats synthétisés ci-dessous.")

        # Vider l'ancien tableau
        for row in self.tree_comp.get_children():
            self.tree_comp.delete(row)

        synthese: dict[str, dict[str, dict[str, float]]] = {}
        for sc in scenarios_noms:
            synthese[sc] = {}
            for strat in ["LOOK", "FCFS"]:
                stats_list = resultats_bruts[sc][strat]
                n = len(stats_list)
                moy_attente = sum(s["attente_moyenne"] for s in stats_list) / n
                moy_depl = sum(s["deplacements"] for s in stats_list) / n
                moy_serv = sum(s["appels_servis"] for s in stats_list) / n
                moy_occ = sum(s["taux_occupation"] for s in stats_list) / n
                moy_max = sum(s["attente_max"] for s in stats_list) / n

                synthese[sc][strat] = {
                    "attente_moyenne": round(moy_attente, 2),
                    "deplacements": round(moy_depl, 1),
                    "appels_servis": round(moy_serv, 1),
                    "taux_occupation": round(moy_occ, 1),
                    "attente_max": round(moy_max, 1),
                }

                self.tree_comp.insert(
                    "",
                    tk.END,
                    values=(
                        sc.capitalize(),
                        strat,
                        f"{moy_attente:.2f}",
                        f"{moy_max:.1f}",
                        f"{moy_depl:.1f}",
                        f"{moy_serv:.1f}",
                        f"{moy_occ:.1f}",
                    ),
                )

        self._dessiner_graphique_comparatif(synthese, scenarios_noms)

    def _dessiner_graphique_comparatif(
        self, synthese: dict[str, dict[str, dict[str, float]]], scenarios_noms: list[str]
    ) -> None:
        """Trace un graphique en barres net et soigné sur le Canvas pour l'attente moyenne (EF14)."""
        self.canvas_graphique.delete("all")
        w = self.canvas_graphique.winfo_width()
        h = self.canvas_graphique.winfo_height()
        if w < 100 or h < 100:
            w, h = 700, 260

        marge_gauche = 70
        marge_droite = 30
        marge_haut = 40
        marge_bas = 45

        # Recherche de la valeur maximale pour l'échelle Y
        val_max = 1.0
        for sc in scenarios_noms:
            for strat in ["LOOK", "FCFS"]:
                val_max = max(val_max, synthese[sc][strat]["attente_moyenne"])
        val_max = val_max * 1.25  # Marge supérieure

        # Axes
        self.canvas_graphique.create_line(marge_gauche, h - marge_bas, w - marge_droite, h - marge_bas, width=2, fill="#475569")
        self.canvas_graphique.create_line(marge_gauche, marge_haut, marge_gauche, h - marge_bas, width=2, fill="#475569")

        # Graduations axe Y
        nb_grad = 5
        for i in range(nb_grad + 1):
            val = (val_max / nb_grad) * i
            y = (h - marge_bas) - (i / nb_grad) * (h - marge_haut - marge_bas)
            self.canvas_graphique.create_line(marge_gauche - 5, y, marge_gauche, y, fill="#475569")
            self.canvas_graphique.create_line(marge_gauche, y, w - marge_droite, y, fill="#e2e8f0", dash=(2, 2))
            self.canvas_graphique.create_text(marge_gauche - 10, y, text=f"{val:.1f}s", anchor=tk.E, font=("Helvetica", 8))

        # Titre et légende
        self.canvas_graphique.create_text(
            w / 2, 18, text="Temps d'attente moyen par stratégie et par scénario (secondes)", font=("Helvetica", 10, "bold"), fill="#1e293b"
        )

        # Légende
        leg_x = w - 180
        self.canvas_graphique.create_rectangle(leg_x, 10, leg_x + 15, 22, fill="#2563eb", outline="#1d4ed8")
        self.canvas_graphique.create_text(leg_x + 22, 16, text="LOOK", anchor=tk.W, font=("Helvetica", 8, "bold"))
        self.canvas_graphique.create_rectangle(leg_x + 70, 10, leg_x + 85, 22, fill="#ea580c", outline="#c2410c")
        self.canvas_graphique.create_text(leg_x + 92, 16, text="FCFS", anchor=tk.W, font=("Helvetica", 8, "bold"))

        # Barres par groupe
        largeur_dispo = (w - marge_gauche - marge_droite)
        nb_groupes = len(scenarios_noms)
        largeur_groupe = largeur_dispo / nb_groupes
        largeur_barre = min(40, largeur_groupe * 0.35)

        for idx, sc in enumerate(scenarios_noms):
            centre_groupe = marge_gauche + (idx + 0.5) * largeur_groupe

            # Barre LOOK
            val_look = synthese[sc]["LOOK"]["attente_moyenne"]
            h_barre_look = (val_look / val_max) * (h - marge_haut - marge_bas)
            x_look1 = centre_groupe - largeur_barre - 2
            x_look2 = centre_groupe - 2
            y_look = (h - marge_bas) - h_barre_look

            self.canvas_graphique.create_rectangle(x_look1, y_look, x_look2, h - marge_bas, fill="#2563eb", outline="#1d4ed8")
            self.canvas_graphique.create_text((x_look1 + x_look2) / 2, y_look - 8, text=f"{val_look:.1f}", font=("Helvetica", 8, "bold"), fill="#1d4ed8")

            # Barre FCFS
            val_fcfs = synthese[sc]["FCFS"]["attente_moyenne"]
            h_barre_fcfs = (val_fcfs / val_max) * (h - marge_haut - marge_bas)
            x_fcfs1 = centre_groupe + 2
            x_fcfs2 = centre_groupe + largeur_barre + 2
            y_fcfs = (h - marge_bas) - h_barre_fcfs

            self.canvas_graphique.create_rectangle(x_fcfs1, y_fcfs, x_fcfs2, h - marge_bas, fill="#ea580c", outline="#c2410c")
            self.canvas_graphique.create_text((x_fcfs1 + x_fcfs2) / 2, y_fcfs - 8, text=f"{val_fcfs:.1f}", font=("Helvetica", 8, "bold"), fill="#c2410c")

            # Libellé scénario
            self.canvas_graphique.create_text(centre_groupe, h - marge_bas + 18, text=sc.capitalize(), font=("Helvetica", 9, "bold"), fill="#1e293b")

    # =========================================================================
    # ONGLET 3 : HISTORIQUE & BASE DE DONNÉES SQLITE
    # =========================================================================

    def _init_onglet_historique(self) -> None:
        """Initialise l'onglet d'historique SQLite et export CSV (EF15, EF17)."""
        cadre_haut = ttk.Frame(self.onglet_historique, padding=6)
        cadre_haut.pack(fill=tk.X)

        ttk.Button(cadre_haut, text="🔄 Actualiser l'historique", command=self._actualiser_liste_historique).pack(side=tk.LEFT, padx=4)
        ttk.Button(cadre_haut, text="📥 Exporter le journal sélectionné en CSV (EF17)", command=self._action_exporter_csv).pack(side=tk.LEFT, padx=4)

        # Panneau partagé : Table des simulations (haut) et Détail des événements (bas)
        panneau_division = ttk.PanedWindow(self.onglet_historique, orient=tk.VERTICAL)
        panneau_division.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        # Table du haut : simulations
        cadre_sims = ttk.LabelFrame(panneau_division, text=" Simulations enregistrées dans data/ascenseur.db ", padding=4)
        panneau_division.add(cadre_sims, weight=1)

        cols_sims = ("id", "date_heure", "strategie", "scenario", "graine", "nb_etages", "duree", "servis", "att_moy", "att_max", "depl", "taux")
        self.tree_historique = ttk.Treeview(cadre_sims, columns=cols_sims, show="headings", height=7)
        self.tree_historique.heading("id", text="ID")
        self.tree_historique.heading("date_heure", text="Date / Heure")
        self.tree_historique.heading("strategie", text="Stratégie")
        self.tree_historique.heading("scenario", text="Scénario")
        self.tree_historique.heading("graine", text="Graine")
        self.tree_historique.heading("nb_etages", text="Étages")
        self.tree_historique.heading("duree", text="Durée")
        self.tree_historique.heading("servis", text="Servis")
        self.tree_historique.heading("att_moy", text="Attente Moy")
        self.tree_historique.heading("att_max", text="Attente Max")
        self.tree_historique.heading("depl", text="Déplacements")
        self.tree_historique.heading("taux", text="Taux (%)")

        self.tree_historique.column("id", width=40, anchor=tk.CENTER)
        self.tree_historique.column("date_heure", width=130, anchor=tk.CENTER)
        self.tree_historique.column("strategie", width=70, anchor=tk.CENTER)
        self.tree_historique.column("scenario", width=80, anchor=tk.CENTER)
        self.tree_historique.column("graine", width=60, anchor=tk.CENTER)
        self.tree_historique.column("nb_etages", width=55, anchor=tk.CENTER)
        self.tree_historique.column("duree", width=55, anchor=tk.CENTER)
        self.tree_historique.column("servis", width=55, anchor=tk.CENTER)
        self.tree_historique.column("att_moy", width=75, anchor=tk.CENTER)
        self.tree_historique.column("att_max", width=75, anchor=tk.CENTER)
        self.tree_historique.column("depl", width=85, anchor=tk.CENTER)
        self.tree_historique.column("taux", width=65, anchor=tk.CENTER)

        scroll_sims = ttk.Scrollbar(cadre_sims, orient=tk.VERTICAL, command=self.tree_historique.yview)
        self.tree_historique.configure(yscrollcommand=scroll_sims.set)
        self.tree_historique.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_sims.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree_historique.bind("<<TreeviewSelect>>", self._on_selection_simulation)

        # Table du bas : détail des événements
        cadre_evts = ttk.LabelFrame(panneau_division, text=" Détail du journal de la simulation sélectionnée ", padding=4)
        panneau_division.add(cadre_evts, weight=1)

        cols_evts = ("tick", "etage", "direction", "evenement", "source", "appels")
        self.tree_hist_evts = ttk.Treeview(cadre_evts, columns=cols_evts, show="headings", height=8)
        self.tree_hist_evts.heading("tick", text="Tick")
        self.tree_hist_evts.heading("etage", text="Étage")
        self.tree_hist_evts.heading("direction", text="Direction")
        self.tree_hist_evts.heading("evenement", text="Événement")
        self.tree_hist_evts.heading("source", text="Source")
        self.tree_hist_evts.heading("appels", text="File d'attente")

        self.tree_hist_evts.column("tick", width=60, anchor=tk.CENTER)
        self.tree_hist_evts.column("etage", width=60, anchor=tk.CENTER)
        self.tree_hist_evts.column("direction", width=80, anchor=tk.CENTER)
        self.tree_hist_evts.column("evenement", width=140, anchor=tk.W)
        self.tree_hist_evts.column("source", width=80, anchor=tk.CENTER)
        self.tree_hist_evts.column("appels", width=180, anchor=tk.W)

        scroll_evts = ttk.Scrollbar(cadre_evts, orient=tk.VERTICAL, command=self.tree_hist_evts.yview)
        self.tree_hist_evts.configure(yscrollcommand=scroll_evts.set)
        self.tree_hist_evts.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_evts.pack(side=tk.RIGHT, fill=tk.Y)

        self._actualiser_liste_historique()

    def _actualiser_liste_historique(self) -> None:
        """Recharge les simulations depuis SQLite et met à jour l'affichage."""
        for row in self.tree_historique.get_children():
            self.tree_historique.delete(row)

        sims = lire_historique()
        for s in sims:
            self.tree_historique.insert(
                "",
                tk.END,
                values=(
                    s["id"],
                    s["date_heure"],
                    s["strategie"],
                    s["scenario"],
                    s["graine"] if s["graine"] is not None else "-",
                    s["nb_etages"],
                    s["duree"],
                    s["appels_servis"],
                    f"{s['attente_moyenne']:.2f}",
                    s["attente_max"],
                    s["deplacements"],
                    f"{s['taux_occupation']:.1f}",
                ),
            )

    def _on_selection_simulation(self, event: Any) -> None:
        """Charge et affiche les événements de la simulation sélectionnée."""
        selection = self.tree_historique.selection()
        if not selection:
            return

        item = self.tree_historique.item(selection[0])
        sim_id = int(item["values"][0])

        for row in self.tree_hist_evts.get_children():
            self.tree_hist_evts.delete(row)

        evenements = lire_evenements_simulation(sim_id)
        for e in evenements:
            self.tree_hist_evts.insert(
                "",
                tk.END,
                values=(
                    e["tick"],
                    e["etage"],
                    e["direction"],
                    e["evenement"],
                    e.get("source", ""),
                    e.get("appels", ""),
                ),
            )

    def _action_exporter_csv(self) -> None:
        """Permet à l'utilisateur de sauvegarder le journal sélectionné au format CSV."""
        selection = self.tree_historique.selection()
        if not selection:
            messagebox.showinfo("Export CSV", "Veuillez d'abord sélectionner une simulation dans le tableau ci-dessus.")
            return

        item = self.tree_historique.item(selection[0])
        sim_id = int(item["values"][0])

        nom_fichier_suggere = f"journal_simulation_{sim_id}.csv"
        chemin = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("Fichiers CSV", "*.csv"), ("Tous les fichiers", "*.*")],
            initialfile=nom_fichier_suggere,
            title="Exporter le journal en CSV",
        )
        if chemin:
            succes = exporter_csv(sim_id, chemin)
            if succes:
                messagebox.showinfo("Export CSV Réussi", f"Le journal a été exporté avec succès vers :\n{chemin}")
            else:
                messagebox.showerror("Export CSV Échoué", "Impossible d'exporter les événements de cette simulation.")


def lancer_gui() -> None:
    """Point d'entrée pour démarrer l'interface graphique Tkinter."""
    root = tk.Tk()
    app = ApplicationAscenseur(root)
    root.mainloop()


if __name__ == "__main__":
    lancer_gui()
