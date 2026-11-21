"""Fenêtre d'édition d'une image de maillot (haut, short ou icône) : pipette + remplacement de couleur, logo, annuler."""
import os, time, tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox
from . import images, retouche

AFFICHAGE = 560

# zones des patrons (x0, y0, x1, y1 en fraction de l'image ; x0 == x1 : ligne ; tout petit : repère)
GUIDES = {
    'haut': [
        (0.03, 0.0, 0.35, 0.45, 'MANCHE', '#ffd54a'),
        (0.65, 0.0, 0.97, 0.45, 'MANCHE', '#ffd54a'),
        (0.35, 0.0, 0.65, 0.45, 'col, épaules', '#c8c8c8'),
        (0.0, 0.46, 0.5, 1.0, 'DEVANT', '#5cff8a'),
        (0.5, 0.46, 1.0, 1.0, 'DOS (numéro)', '#ff8a5c'),
        (0.25, 0.47, 0.25, 0.98, 'milieu', '#5cff8a'),
        (0.75, 0.47, 0.75, 0.98, 'milieu', '#ff8a5c'),
        (0.0, 0.5, 0.0, 1.0, 'côté', '#ffffff'),
        (0.5, 0.5, 0.5, 1.0, 'côté', '#ffffff'),
        (0.34, 0.585, 0.375, 0.635, 'écusson', '#5cff8a'),
        (0.13, 0.585, 0.165, 0.635, 'marque', '#5cff8a'),
    ],
    'short': [      # relevé sur le modèle 3D : le short ET les chaussettes sont sur cette image
        (0.0, 0.0, 0.5, 0.54, 'SHORT DEVANT', '#5cff8a'),
        (0.5, 0.0, 1.0, 0.54, 'SHORT DOS', '#ff8a5c'),
        (0.25, 0.02, 0.25, 0.5, 'entre les jambes', '#5cff8a'),
        (0.75, 0.02, 0.75, 0.5, 'entre les jambes', '#ff8a5c'),
        (0.0, 0.56, 0.34, 1.0, 'genoux', '#c8c8c8'),
        (0.36, 0.6, 0.67, 0.99, 'CHAUSSETTE', '#ffd54a'),
        (0.68, 0.6, 0.99, 0.99, 'CHAUSSETTE', '#ffd54a'),
    ],
}


class Editeur(tk.Toplevel):
    def __init__(self, parent, source, sortie, titre, quand_enregistre, genre='haut', en_direct=None):
        super().__init__(parent)
        self.title('Modifier — ' + titre)
        self.transient(parent)
        self.source, self.sortie, self.quand_enregistre = source, sortie, quand_enregistre
        self.w, self.h, self.rows = images.lire_png(source)
        self.original = retouche.copie(self.rows)
        self.historique = []
        self.couleur_source = None
        self.logo = None
        self.mode = tk.StringVar(value='pipette')
        self.tol = tk.DoubleVar(value=60)
        self.taille_logo = tk.DoubleVar(value=max(32, self.w // 6))
        self.guide = tk.BooleanVar(value=True)
        self.couleur_pinceau = (220, 30, 45)
        self.taille_pinceau = tk.DoubleVar(value=24)
        self._dernier = None            # dernier point du trait en cours
        self._envoi = 0.0
        self.genre = genre
        self.en_direct = en_direct        # appelé à chaque modification (aperçu 3D en direct)
        self._ui()
        self._afficher()
        self.update_idletasks()
        self.geometry('+%d+%d' % (parent.winfo_rootx() + 40, parent.winfo_rooty() + 30))
        self.grab_set()
        self.bind('<Destroy>', self._fermeture)

    # ------------------------------------------------------------------------------------------ interface
    def _ui(self):
        f = ttk.Frame(self, padding=10); f.pack(fill='both', expand=True)
        self.cv = tk.Canvas(f, width=AFFICHAGE, height=AFFICHAGE, background='#3c4048', highlightthickness=0, cursor='crosshair')
        self.cv.grid(row=0, column=0, rowspan=20, sticky='n')
        self.cv.bind('<Button-1>', self._clic)
        self.cv.bind('<Motion>', self._survol)
        self.cv.bind('<B1-Motion>', self._glisser)
        self.cv.bind('<ButtonRelease-1>', self._relacher)
        self.cv.bind('<Button-3>', self._prendre_couleur)
        self.cv.bind('<Leave>', lambda e: self.cv.delete('viseur'))
        o = ttk.Frame(f, padding=(14, 0, 0, 0)); o.grid(row=0, column=1, sticky='n')
        ttk.Label(o, text='Outil', font=('Segoe UI', 11, 'bold')).pack(anchor='w')
        ttk.Radiobutton(o, text='Pipette : clique une couleur à changer', variable=self.mode, value='pipette').pack(anchor='w')
        ttk.Radiobutton(o, text='Logo : clique pour le poser', variable=self.mode, value='logo').pack(anchor='w')
        ttk.Radiobutton(o, text='Pinceau : clique et glisse pour peindre', variable=self.mode, value='pinceau').pack(anchor='w')
        ttk.Radiobutton(o, text="Gomme : remet l'image d'origine", variable=self.mode, value='gomme').pack(anchor='w')
        if self.genre in ('haut', 'short'):
            ttk.Checkbutton(o, text='Afficher le guide (devant, dos, manches…)', variable=self.guide,
                            command=self._dessiner_guide).pack(anchor='w', pady=(6, 0))
        ttk.Separator(o).pack(fill='x', pady=8)
        ttk.Label(o, text='Changer une couleur', font=('Segoe UI', 11, 'bold')).pack(anchor='w')
        r = ttk.Frame(o); r.pack(anchor='w', pady=3)
        ttk.Label(r, text='Couleur choisie :').pack(side='left')
        self.pastille = tk.Label(r, width=4, background='#888888', relief='solid', borderwidth=1); self.pastille.pack(side='left', padx=6)
        self.lbl_coul = ttk.Label(r, text='(clique sur l\'image)'); self.lbl_coul.pack(side='left')
        ttk.Label(o, text='Tolérance (couleurs proches incluses)').pack(anchor='w', pady=(6, 0))
        ttk.Scale(o, from_=10, to=150, variable=self.tol, orient='horizontal', length=230).pack(anchor='w')
        ttk.Button(o, text='Remplacer par une nouvelle couleur…', command=self._remplacer).pack(anchor='w', pady=6, fill='x')
        ttk.Separator(o).pack(fill='x', pady=8)
        ttk.Label(o, text='Pinceau / gomme', font=('Segoe UI', 11, 'bold')).pack(anchor='w')
        r = ttk.Frame(o); r.pack(anchor='w', pady=3, fill='x')
        self.pastille_p = tk.Label(r, width=4, background='#dc1e2d', relief='solid', borderwidth=1)
        self.pastille_p.pack(side='left')
        ttk.Button(r, text='Couleur du pinceau…', command=self._choisir_couleur_pinceau).pack(side='left', padx=6)
        ttk.Label(o, text="Clic droit sur l'image : prendre sa couleur", foreground='#666').pack(anchor='w')
        ttk.Label(o, text='Taille (pixels)').pack(anchor='w', pady=(4, 0))
        ttk.Scale(o, from_=2, to=300, variable=self.taille_pinceau, orient='horizontal', length=230).pack(anchor='w')
        ttk.Separator(o).pack(fill='x', pady=8)
        ttk.Label(o, text='Logo / écusson', font=('Segoe UI', 11, 'bold')).pack(anchor='w')
        ttk.Button(o, text='Choisir une image PNG…', command=self._choisir_logo).pack(anchor='w', fill='x', pady=3)
        self.lbl_logo = ttk.Label(o, text='aucun logo', foreground='#666'); self.lbl_logo.pack(anchor='w')
        ttk.Label(o, text='Taille du logo (pixels)').pack(anchor='w', pady=(6, 0))
        ttk.Scale(o, from_=16, to=max(64, self.w // 2), variable=self.taille_logo, orient='horizontal', length=230).pack(anchor='w')
        ttk.Separator(o).pack(fill='x', pady=8)
        ttk.Button(o, text='Annuler la dernière modification', command=self._annuler).pack(anchor='w', fill='x', pady=2)
        ttk.Button(o, text='Revenir à l\'original', command=self._reinitialiser).pack(anchor='w', fill='x', pady=2)
        ttk.Separator(o).pack(fill='x', pady=8)
        b = ttk.Frame(o); b.pack(anchor='w', fill='x')
        ttk.Button(b, text='Enregistrer', command=self._enregistrer).pack(side='left')
        ttk.Button(b, text='Fermer', command=self.destroy).pack(side='left', padx=6)
        self.etat = tk.StringVar(value='%d x %d' % (self.w, self.h))
        ttk.Label(o, textvariable=self.etat, foreground='#444', wraplength=250).pack(anchor='w', pady=(10, 0))

    def _afficher(self):
        pw, ph, pr = retouche.reduire(self.w, self.h, self.rows, AFFICHAGE)
        self.ech = self.w / float(pw)
        self.img = retouche.photo(self, pw, ph, pr)
        self.cv.delete('all')
        self.cv.create_image(0, 0, image=self.img, anchor='nw')
        self.cv.configure(width=pw, height=ph)
        self.pw, self.ph = pw, ph
        self._dessiner_guide()

    def _dessiner_guide(self):
        """zones du patron (relevées sur les maillots du jeu) : approximatives, mais les mêmes pour tous les maillots"""
        self.cv.delete('guide')
        if not self.guide.get() or self.genre not in GUIDES:
            return
        W, H = self.pw, self.ph
        for x0, y0, x1, y1, texte, couleur in GUIDES[self.genre]:
            if x0 == x1:      # ligne verticale (côtés, milieux)
                self.cv.create_line(x0 * W, y0 * H, x0 * W, y1 * H, fill=couleur, dash=(6, 4), width=2, tags='guide')
                if texte:
                    self.cv.create_text(x0 * W + (14 if x0 < 0.5 else -14) if x0 in (0.0, 1.0) else x0 * W, y1 * H - 12,
                                        text=texte, fill=couleur, font=('Segoe UI', 8, 'bold'), tags='guide')
                continue
            if x1 - x0 < 0.03:  # repère (petit carré)
                self.cv.create_rectangle(x0 * W, y0 * H, x1 * W, y1 * H, outline=couleur, width=2, tags='guide')
                self.cv.create_text((x0 + x1) / 2 * W, y1 * H + 9, text=texte, fill=couleur, font=('Segoe UI', 8, 'bold'), tags='guide')
                continue
            self.cv.create_rectangle(x0 * W, y0 * H, x1 * W, y1 * H, outline=couleur, dash=(4, 3), width=2, tags='guide')
            self.cv.create_text((x0 + x1) / 2 * W, y0 * H + 14, text=texte, fill=couleur, font=('Segoe UI', 11, 'bold'), tags='guide')

    def _pos(self, ev):
        x, y = int(ev.x * self.ech), int(ev.y * self.ech)
        return max(0, min(self.w - 1, x)), max(0, min(self.h - 1, y))

    def _survol(self, ev):
        x, y = self._pos(ev)
        self.cv.delete('viseur')
        if self.mode.get() in ('pinceau', 'gomme'):
            t = float(self.taille_pinceau.get()) / self.ech / 2
            self.cv.create_oval(ev.x - t, ev.y - t, ev.x + t, ev.y + t, outline='#ffffff', tags='viseur')
            self.cv.create_oval(ev.x - t - 1, ev.y - t - 1, ev.x + t + 1, ev.y + t + 1, outline='#000000', tags='viseur')
        elif self.mode.get() == 'logo' and self.logo:
            t = float(self.taille_logo.get()) / self.ech / 2
            self.cv.create_rectangle(ev.x - t, ev.y - t, ev.x + t, ev.y + t, outline='#ffcc00', dash=(3, 2), tags='viseur')

    # ------------------------------------------------------------------------------------------- outils
    def _memoriser(self):
        self.historique.append(retouche.copie(self.rows))
        if len(self.historique) > 6:
            self.historique.pop(0)

    def _clic(self, ev):
        x, y = self._pos(ev)
        if self.mode.get() in ('pinceau', 'gomme'):
            self._memoriser()
            self._dernier = (x, y)
            self._peindre((x, y), (x, y), ev)
            return
        if self.mode.get() == 'pipette':
            r, g, b, a = retouche.pixel(self.rows, x, y)
            self.couleur_source = (r, g, b)
            self.pastille.configure(background='#%02x%02x%02x' % (r, g, b))
            self.lbl_coul.configure(text='RVB %d, %d, %d' % (r, g, b))
            self.etat.set('Couleur choisie. Clique « Remplacer par une nouvelle couleur… ».')
        elif self.logo:
            self._memoriser()
            self.configure(cursor='watch'); self.update()
            retouche.poser_logo(self.rows, self.w, self.h, self.logo, x, y, int(float(self.taille_logo.get())))
            self.configure(cursor='')
            self._afficher(); self._signaler()
            self.etat.set('Logo posé en %d, %d (Annuler pour l\'enlever).' % (x, y))
        else:
            self.etat.set('Choisis d\'abord une image de logo.')

    def _peindre(self, a, b, ev):
        rayon = float(self.taille_pinceau.get()) / 2
        gomme = self.mode.get() == 'gomme'
        retouche.trait(self.rows, self.w, self.h, a, b, rayon,
                       None if gomme else self.couleur_pinceau, self.original if gomme else None)
        # retour immédiat à l'écran (l'image complète est redessinée au relâchement)
        t = max(1.0, rayon / self.ech)
        (xa, ya), (xb, yb) = [(p[0] / self.ech, p[1] / self.ech) for p in (a, b)]
        if gomme:
            self.cv.create_line(xa, ya, xb, yb, width=2 * t, capstyle='round', fill='#ffffff', stipple='gray50', tags='trait')
        else:
            self.cv.create_line(xa, ya, xb, yb, width=2 * t, capstyle='round', fill='#%02x%02x%02x' % self.couleur_pinceau, tags='trait')
        self.cv.tag_raise('guide'); self.cv.tag_raise('viseur')
        if time.time() - self._envoi > 0.5:        # aperçu 3D pendant le trait (2 fois par seconde)
            self._envoi = time.time()
            self._signaler()

    def _glisser(self, ev):
        self._survol(ev)
        if self._dernier is None or self.mode.get() not in ('pinceau', 'gomme'):
            return
        p = self._pos(ev)
        if p != self._dernier:
            self._peindre(self._dernier, p, ev)
            self._dernier = p

    def _relacher(self, ev):
        if self._dernier is None:
            return
        self._dernier = None
        self._afficher(); self._signaler()
        self.etat.set('Peint. « Annuler » enlève le dernier trait.')

    def _prendre_couleur(self, ev):
        x, y = self._pos(ev)
        r, g, b, a = retouche.pixel(self.rows, x, y)
        self._couleur_pinceau((r, g, b))
        self.etat.set('Couleur du pinceau : RVB %d, %d, %d' % (r, g, b))

    def _choisir_couleur_pinceau(self):
        c = colorchooser.askcolor(color='#%02x%02x%02x' % self.couleur_pinceau, title='Couleur du pinceau', parent=self)
        if c and c[0]:
            self._couleur_pinceau(tuple(int(v) for v in c[0]))
            if self.mode.get() != 'gomme':
                self.mode.set('pinceau')

    def _couleur_pinceau(self, c):
        self.couleur_pinceau = c
        self.pastille_p.configure(background='#%02x%02x%02x' % c)

    def _remplacer(self):
        if not self.couleur_source:
            messagebox.showinfo('Modifier', 'Choisis d\'abord la couleur à changer avec la pipette (clique sur l\'image).', parent=self)
            return
        c = colorchooser.askcolor(title='Nouvelle couleur', parent=self)
        if not c or not c[0]:
            return
        cible = tuple(int(v) for v in c[0])
        self._memoriser()
        self.configure(cursor='watch'); self.update()
        n = retouche.remplacer_couleur(self.rows, self.couleur_source, cible, int(float(self.tol.get())))
        self.configure(cursor='')
        self._afficher(); self._signaler()
        self.couleur_source = cible
        self.pastille.configure(background='#%02x%02x%02x' % cible)
        self.lbl_coul.configure(text='RVB %d, %d, %d' % cible)
        self.etat.set('%d pixels recolorés. Si ça déborde, Annuler et baisse la tolérance.' % n)

    def _choisir_logo(self):
        p = filedialog.askopenfilename(parent=self, title='Logo (PNG, fond transparent de préférence)', filetypes=[('Images PNG', '*.png')])
        if not p:
            return
        try:
            self.logo = images.lire_png(p)
        except Exception as e:
            messagebox.showerror('Modifier', str(e), parent=self); return
        self.lbl_logo.configure(text=os.path.basename(p))
        self.mode.set('logo')
        self.etat.set('Logo chargé : clique sur l\'image pour le poser.')

    def _annuler(self):
        if self.historique:
            self.rows = self.historique.pop()
            self._afficher(); self._signaler()
            self.etat.set('Modification annulée.')

    def _reinitialiser(self):
        self._memoriser()
        self.rows = retouche.copie(self.original)
        self._afficher(); self._signaler()
        self.etat.set('Image d\'origine remise (Annuler pour revenir).')

    def _signaler(self):
        """envoie l'image en cours à l'aperçu 3D (réduite à 1024 : c'est instantané)"""
        if self.en_direct:
            try:
                w, h, rows = retouche.reduire(self.w, self.h, self.rows, 1024)
                self.en_direct(retouche.png_memoire(w, h, rows))
            except Exception:
                pass

    def _fermeture(self, ev):
        if ev.widget is self and self.en_direct:
            self.en_direct(None)        # l'aperçu 3D revient au fichier enregistré

    def _enregistrer(self):
        self.configure(cursor='watch'); self.update()
        images.ecrire_png(self.sortie, self.w, self.h, self.rows, 6)
        self.configure(cursor='')
        self.etat.set('Enregistré : ' + os.path.basename(self.sortie))
        self.quand_enregistre(self.sortie)
        if self.en_direct:
            self.en_direct(None)        # le fichier enregistré prend le relais
