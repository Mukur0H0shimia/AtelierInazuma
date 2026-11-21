"""Atelier Maillots (Inazuma Eleven Victory Road + VRFW) : crée tes propres maillots en quelques clics.

1. « Nouveau maillot » : un nom, un prix, et un maillot du jeu dont on reprend la coupe.
2. « Exporter les images » : le haut, le short (domicile / extérieur) et l'icône du maillot de base, en PNG,
   à modifier dans Paint, GIMP, Photoshop…
3. Choisis tes images (seul le haut domicile est obligatoire), puis « Construire et installer » :
   le mod « Mes maillots » est créé et activé ; les maillots sont vendus à la boutique générale.
Lancer : double-clic sur « Atelier Maillots.exe »."""
try:   # lecture directe des paquets du jeu (variable ATELIER_JEU_DIRECT posée par l'Atelier)
    import os as _os_v, sys as _sys_v
    _sys_v.path.insert(0, _os_v.path.join(_os_v.path.dirname(_os_v.path.dirname(_os_v.path.abspath(__file__))), 'AtelierCouleurs'))
    from moteur import donnees_virtuelles as _dv
    _dv.depuis_env()
except Exception as _ex_v:
    print('lecture directe :', _ex_v)
import os, sys, threading, queue, subprocess, traceback, multiprocessing, webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
from lib import atelier_mod as A, retouche, apercu3d, numeros   # noqa: E402

def lisible(nom):
    """noms du jeu : les codes <MNT:XXX> / <FST:XXX> (noms remplacés par le jeu) deviennent « Xxx »"""
    import re
    return re.sub(r'<[A-Z]+:([A-Za-z0-9_]+?)\d*>', lambda m: m.group(1).capitalize(), nom)


JOURNAL_ERREURS = os.path.join(ICI, 'erreurs.log')


def noter_erreur(texte):
    import time
    try:
        with open(JOURNAL_ERREURS, 'a', encoding='utf-8') as f:
            f.write('\n===== %s\n%s\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), texte))
    except OSError:
        pass


FOND, PANNEAU, CARTE, BORD, TEXTE, DOUX, ACCENT = '#14161c', '#1c1f27', '#232733', '#313646', '#e9ecf3', '#9aa3b5', '#ffc83d'

CHAMPS = (('haut_dom', 'Haut domicile (obligatoire)'), ('short_dom', 'Short + chaussettes domicile'),
          ('haut_ext', 'Haut extérieur'), ('short_ext', 'Short + chaussettes extérieur'), ('icone', 'Icône (256 x 256)'),
          ('embleme', "Emblème d'équipe (512 x 512)"))


class Atelier(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Atelier Maillots — Inazuma Eleven Victory Road')
        self.geometry('1460x780')
        self.minsize(1200, 680)
        self.photos = {}
        self.rgl = A.reglages()
        self.projet = A.charger_projet()
        self.cat, self.cat_par_cle = [], {}
        self.q = queue.Queue()
        self.occupe = False
        self.courant = None
        self._apercu_en_cours = False
        self._apercu_redemande = False
        self.ap3d = None
        self._ui()
        self.after(100, self._pompe)
        self.tache(self._charger_catalogue, 'Lecture des maillots du jeu')

    # ------------------------------------------------------------------------------------------ interface
    def _ui(self):
        st = ttk.Style(self)
        try:
            st.theme_use('clam')
        except tk.TclError:
            pass
        # thème sombre (assorti au studio)
        self.configure(background=PANNEAU)
        st.configure('.', background=PANNEAU, foreground=TEXTE, fieldbackground=CARTE, bordercolor=BORD,
                     lightcolor=BORD, darkcolor=BORD, troughcolor=CARTE, font=('Segoe UI', 10))
        st.configure('TButton', background=CARTE, foreground=TEXTE, padding=(10, 5), borderwidth=1, focuscolor=CARTE)
        st.map('TButton', background=[('active', '#2c3140'), ('disabled', PANNEAU)], foreground=[('disabled', '#5c6475')])
        st.configure('Grand.TButton', background=ACCENT, foreground='#1a1a1a', font=('Segoe UI', 10, 'bold'), padding=8,
                     focuscolor=ACCENT)
        st.map('Grand.TButton', background=[('active', '#ffd56a'), ('disabled', '#5f5330')])
        st.configure('TEntry', fieldbackground=CARTE, foreground=TEXTE, insertcolor=TEXTE)
        st.configure('TSpinbox', fieldbackground=CARTE, foreground=TEXTE, arrowcolor=TEXTE, insertcolor=TEXTE)
        st.configure('Titre.TLabel', font=('Segoe UI', 13, 'bold'), foreground=ACCENT)
        st.configure('Horizontal.TProgressbar', background=ACCENT, troughcolor=CARTE)
        liste = dict(background=CARTE, foreground=TEXTE, selectbackground=ACCENT, selectforeground='#1a1a1a',
                     highlightthickness=0, relief='flat', borderwidth=6)
        haut = ttk.Frame(self, padding=10); haut.pack(fill='both', expand=True)
        # gauche : mes maillots
        g = ttk.Frame(haut); g.pack(side='left', fill='y')
        ttk.Label(g, text='Mes maillots', style='Titre.TLabel').pack(anchor='w')
        self.liste = tk.Listbox(g, width=30, height=20, exportselection=False, font=('Segoe UI', 10), **liste)
        self.liste.pack(fill='y', expand=True, pady=6)
        self.liste.bind('<<ListboxSelect>>', lambda e: self._choisir())
        bg = ttk.Frame(g); bg.pack(fill='x')
        ttk.Button(bg, text='Nouveau maillot', command=self._nouveau).pack(fill='x')
        ttk.Button(bg, text='Supprimer', command=self._supprimer).pack(fill='x', pady=4)
        # droite : le maillot choisi
        d = ttk.Frame(haut, padding=(16, 0, 0, 0)); d.pack(side='left', fill='both', expand=True)
        ttk.Label(d, text='Maillot', style='Titre.TLabel').grid(row=0, column=0, columnspan=3, sticky='w')
        ttk.Label(d, text='Nom (affiché en jeu)').grid(row=1, column=0, sticky='w', pady=4)
        self.v_nom = tk.StringVar(); e = ttk.Entry(d, textvariable=self.v_nom, width=40)
        e.grid(row=1, column=1, sticky='we', pady=4)
        ttk.Label(d, text='Prix (jetons)').grid(row=2, column=0, sticky='w', pady=4)
        self.v_prix = tk.IntVar(value=1)
        ttk.Spinbox(d, from_=0, to=999, textvariable=self.v_prix, width=8).grid(row=2, column=1, sticky='w', pady=4)
        ttk.Label(d, text='Coupe : maillot du jeu').grid(row=3, column=0, sticky='nw', pady=4)
        fb = ttk.Frame(d); fb.grid(row=3, column=1, columnspan=2, sticky='we', pady=4)
        self.v_cherche = tk.StringVar(); self.v_cherche.trace_add('write', lambda *a: self._filtrer())
        ttk.Entry(fb, textvariable=self.v_cherche).pack(fill='x')
        ttk.Label(fb, text='(tape une partie du nom pour chercher)', foreground=DOUX).pack(anchor='w')
        self.bases = tk.Listbox(fb, height=7, exportselection=False, font=('Segoe UI', 10), **liste)
        self.bases.pack(fill='x')
        self.bases.bind('<<ListboxSelect>>', lambda e: self._choisir_base())
        self.v_base = tk.StringVar(value='(aucun)')
        ttk.Label(fb, textvariable=self.v_base, foreground='#7fb2ff').pack(anchor='w', pady=(2, 0))
        ttk.Button(d, text='Exporter les images du maillot de base', command=self._exporter).grid(
            row=4, column=1, sticky='w', pady=(8, 4))
        ttk.Label(d, text='Mes images (PNG)', style='Titre.TLabel').grid(row=5, column=0, columnspan=3, sticky='w', pady=(12, 2))
        self.v_img = {}
        for i, (k, lib) in enumerate(CHAMPS):
            ttk.Label(d, text=lib).grid(row=6 + i, column=0, sticky='w', pady=3)
            v = tk.StringVar(); self.v_img[k] = v
            ttk.Entry(d, textvariable=v).grid(row=6 + i, column=1, sticky='we', pady=3)
            fr = ttk.Frame(d); fr.grid(row=6 + i, column=2, sticky='w')
            ttk.Button(fr, text='Choisir…', command=lambda k=k: self._parcourir(k)).pack(side='left', padx=(6, 0))
            ttk.Button(fr, text='Studio…', command=lambda k=k: self._modifier(k)).pack(side='left', padx=2)
            ttk.Button(fr, text='×', width=3, command=lambda k=k: (self.v_img[k].set(''), self._apercu())).pack(side='left', padx=2)
        ttk.Label(d, foreground=DOUX, justify='left', text=(
            "Sans image : le short et les chaussettes restent ceux du maillot de base, l'extérieur reprend tes images du domicile, "
            "l'icône reprend celle du maillot de base.\nLe gardien porte le même maillot que les joueurs.")).grid(
            row=12, column=0, columnspan=3, sticky='w', pady=(4, 8))
        bb = ttk.Frame(d); bb.grid(row=13, column=0, columnspan=3, sticky='w', pady=6)
        ttk.Button(bb, text='Enregistrer', command=self._enregistrer).pack(side='left')
        ttk.Button(bb, text='Ouvrir le dossier des images', command=self._ouvrir_dossier).pack(side='left', padx=6)
        self.b_construire = ttk.Button(bb, text='Construire et installer le mod', style='Grand.TButton', command=self._construire)
        self.b_construire.pack(side='left', padx=16)
        d.columnconfigure(1, weight=1)
        # aperçu
        ap = ttk.Frame(haut, padding=(16, 0, 0, 0)); ap.pack(side='left', fill='y')
        ttk.Label(ap, text='Aperçu', style='Titre.TLabel').grid(row=0, column=0, columnspan=2, sticky='w')
        self.cv = {}
        for i, (k, lib, taille) in enumerate((('icone', 'Icône (boutique)', 128), ('b10', 'Portrait domicile', 128),
                                              ('b20', 'Portrait extérieur', 128), ('vide', '', 0),
                                              ('h10', 'Haut domicile (image)', 170), ('h20', 'Haut extérieur (image)', 170))):
            if not taille:
                continue
            r, c = (1 + (i // 2) * 2, i % 2)
            ttk.Label(ap, text=lib, foreground=DOUX).grid(row=r, column=c, sticky='w', padx=4)
            cv = tk.Canvas(ap, width=taille, height=taille, background=FOND, highlightthickness=0)
            cv.grid(row=r + 1, column=c, padx=4, pady=(0, 8), sticky='nw')
            self.cv[k] = cv
        ttk.Button(ap, text="Actualiser l'aperçu", command=self._apercu).grid(row=8, column=0, sticky='w', pady=4)
        ttk.Button(ap, text='Ouvrir le studio (3D)', style='Grand.TButton', command=self._ouvrir_3d).grid(
            row=8, column=1, sticky='w', pady=4)
        ttk.Label(ap, foreground=DOUX, wraplength=320, justify='left', text=(
            "Le portrait est celui des cartes de joueurs : le jeu le dessine d'une seule couleur, "
            "la couleur principale de ton haut.")).grid(row=9, column=0, columnspan=2, sticky='w')
        # bas : journal
        bas = ttk.Frame(self, padding=(10, 0, 10, 10)); bas.pack(fill='both')
        self.barre = ttk.Progressbar(bas, mode='indeterminate'); self.barre.pack(fill='x')
        self.etat = tk.StringVar(value='')
        ttk.Label(bas, textvariable=self.etat).pack(anchor='w')
        self.jrn = tk.Text(bas, height=9, font=('Consolas', 9), state='disabled', background=FOND, foreground=DOUX, relief='flat', highlightthickness=0, borderwidth=6)
        self.jrn.pack(fill='both', expand=True)
        self._rafraichir_liste()

    def report_callback_exception(self, typ, val, tb):
        texte = ''.join(traceback.format_exception(typ, val, tb))
        noter_erreur(texte)
        self.log('ERREUR : %s (détails dans erreurs.log)' % val)
        messagebox.showerror('Atelier', "Une erreur est survenue :\n%s\n\nLes détails sont notés dans erreurs.log "
                             "(dossier de l'atelier)." % val)

    # ------------------------------------------------------------------------------------------- tâches
    def log(self, msg, etat_seulement=False):
        self.q.put(('etat' if etat_seulement else 'log', msg))

    def _pompe(self):
        try:
            while True:
                k, v = self.q.get_nowait()
                if k == 'log':
                    self.jrn.configure(state='normal'); self.jrn.insert('end', v + '\n'); self.jrn.see('end')
                    self.jrn.configure(state='disabled'); self.etat.set(v)
                elif k == 'etat':
                    self.etat.set(v)
                elif k == 'apercu':
                    self._montrer_apercu(v)
                elif k == 'apercu_fini':
                    self._apercu_en_cours = False
                    if self._apercu_redemande:
                        self._apercu_redemande = False
                        self._apercu()
                elif k == 'studio_image':
                    cle, chemin = v
                    if cle in self.v_img and self.courant is not None and os.path.dirname(chemin) == A.dossier_travail(self.courant):
                        self.v_img[cle].set(os.path.normpath(chemin))
                        self._enregistrer(True)
                        self._apercu()
                        self.log('studio : %s enregistré' % dict(CHAMPS)[cle])
                elif k == 'studio_numero':
                    if self.courant is not None:
                        A.sauver_projet(self.projet)
                elif k == 'fin':
                    self.occupe = False; self.barre.stop(); self.b_construire.state(['!disabled'])
                    if v:
                        v()
        except queue.Empty:
            pass
        self.after(100, self._pompe)

    def tache(self, fn, titre, apres=None):
        if self.occupe:
            messagebox.showinfo('Atelier', 'Une tâche est déjà en cours, attends la fin.')
            return
        self.occupe = True; self.barre.start(12); self.b_construire.state(['disabled'])
        self.log('— ' + titre)
        def run():
            try:
                fn()
            except Exception as e:
                noter_erreur(traceback.format_exc())
                self.log('ERREUR : %s' % e)
                self.log(traceback.format_exc().strip().splitlines()[-1])
                self.q.put(('fin', lambda: messagebox.showerror('Atelier', str(e))))
                return
            self.q.put(('fin', apres))
        threading.Thread(target=run, daemon=True).start()

    def _charger_catalogue(self):
        self.cat = A.catalogue(self.rgl['donnees'], self.log)
        self.cat_par_cle = {c['cle']: c for c in self.cat}
        self.q.put(('fin', self._filtrer))
        self.log('%d maillots du jeu disponibles comme base' % len(self.cat))

    # ------------------------------------------------------------------------------------------- maillots
    def _rafraichir_liste(self, sel=None):
        self.liste.delete(0, 'end')
        for m in self.projet['maillots']:
            self.liste.insert('end', m['nom'])
        if sel is not None and 0 <= sel < self.liste.size():
            self.liste.selection_set(sel); self._choisir()

    def _choisir(self):
        s = self.liste.curselection()
        if not s:
            return
        m = self.projet['maillots'][s[0]]
        self.courant = m
        self.v_nom.set(m['nom']); self.v_prix.set(m.get('prix', 1))
        b = self.cat_par_cle.get(m.get('base'))
        self.v_base.set('%s  (%s)' % (lisible(b['nom']), b['cle']) if b else '(aucun)')
        for k, _ in CHAMPS:
            self.v_img[k].set(m.get(k) or '')
        self._apercu()

    # ------------------------------------------------------------------------------------------- aperçu
    def _apercu(self):
        if not self.courant or not self.cat_par_cle:
            return
        if self._apercu_en_cours:
            self._apercu_redemande = True
            return
        m = dict(self.courant)
        for k, _ in CHAMPS:
            m[k] = self.v_img[k].get().strip() or None
        self._apercu_en_cours = True
        def run():
            try:
                self.q.put(('apercu', A.apercu(m, self.cat_par_cle, self.rgl['donnees'])))
            except Exception as e:
                noter_erreur(traceback.format_exc())
                self.log('aperçu : %s' % e)
            finally:
                self.q.put(('apercu_fini', None))
        threading.Thread(target=run, daemon=True).start()

    def _montrer_apercu(self, ap):
        for k, cv in self.cv.items():
            cv.delete('all')
            im = ap.get(k)
            if not im:
                cv.create_text(int(cv['width']) // 2, int(cv['height']) // 2, text='—', fill='#aaa')
                continue
            w, h, rows = im
            if k.startswith('b'):
                w, h, rows = retouche.recadrer(w, h, rows)
            taille = int(cv['width'])
            w, h, rows = retouche.reduire(w, h, rows, taille)
            ph = retouche.photo(self, w, h, rows)
            self.photos[k] = ph
            cv.create_image(taille // 2, taille // 2, image=ph)

    def _modifier(self, k):
        """ouvre le Studio (dans le navigateur) sur cette image"""
        self._ouvrir_studio('studio?k=' + k)

    # ------------------------------------------------------------------------------------------- 3D
    def _ouvrir_3d(self):
        self._ouvrir_studio('studio?k=haut_dom')

    def _ouvrir_studio(self, page):
        """aperçu 3D seul (page = '') ou studio (page = 'studio?k=…'), dans le navigateur"""
        if not self.courant or not self.cat_par_cle:
            messagebox.showinfo('Atelier', "Choisis d'abord un maillot (ou crée-en un)."); return
        if not self._enregistrer(True):
            return
        if self.ap3d is None:
            self.ap3d = apercu3d.Apercu3D(self.rgl['donnees'], self.log)
            self.ap3d.quand_enregistre = lambda k, chemin: self.q.put(('studio_image', (k, chemin)))
            self.ap3d.quand_numero = self._numero_du_studio
            self.ap3d.quand_plis = self._plis_du_studio
            self.ap3d.catalogue = self.cat
            self.after(300, self._suivre_3d)
        m = dict(self.courant)
        d = A.dossier_travail(self.courant)
        manque = [k for k in apercu3d.CLES + ('icone',) if not os.path.exists(os.path.join(d, A.FICHIER_BASE[k]))]
        self._suivre_3d(une_fois=True)
        webbrowser.open(self.ap3d.url + page)
        if manque and not self.occupe:
            # images du maillot de base (pour les parties que tu n'as pas encore faites)
            self.tache(lambda: A.exporter_base(m, self.cat_par_cle, self.rgl['donnees'], self.log),
                       "Préparation des images du maillot")
        self.log('studio ouvert dans le navigateur' if page else 'aperçu 3D ouvert dans le navigateur')

    def _plis_du_studio(self, mode):
        if self.courant is not None:
            self.courant['plis'] = mode
        self.q.put(('studio_numero', None))     # même chose : enregistrer le projet

    def _numero_du_studio(self, reglages):
        # appelé par le serveur (autre fil) : on garde les réglages tout de suite, l'enregistrement se fait dans l'interface
        if self.courant is not None:
            self.courant['numero'] = dict(reglages)
        self.q.put(('studio_numero', None))

    def _suivre_3d(self, une_fois=False):
        try:
            if self.ap3d and self.courant:
                m = self.courant
                b = self.cat_par_cle.get(m.get('base'))
                if b:
                    mm = dict(m)
                    for k, _ in CHAMPS:
                        mm[k] = self.v_img[k].get().strip() or None
                    self.ap3d.definir(m['nom'], b['tex10'], apercu3d.sources_maillot(mm, A.dossier_travail(m)),
                                      A.dossier_travail(m), numeros.params(m), b, m.get('plis', 'simples'))
        except Exception:
            noter_erreur(traceback.format_exc())
        if not une_fois:
            self.after(500, self._suivre_3d)

    def _filtrer(self):
        f = self.v_cherche.get().lower().strip()
        self.bases.delete(0, 'end')
        self._bases_vues = [c for c in self.cat if f in lisible(c['nom']).lower() or f in c['cle']]
        for c in self._bases_vues:
            self.bases.insert('end', '%s   [%s]' % (lisible(c['nom']), c['cle']))

    def _choisir_base(self):
        s = self.bases.curselection()
        if not s or not self.courant:
            return
        c = self._bases_vues[s[0]]
        self.courant['base'] = c['cle']
        self.v_base.set('%s  (%s)' % (lisible(c['nom']), c['cle']))
        A.sauver_projet(self.projet)
        self._apercu()

    def _nouveau(self):
        if not self.cat:
            messagebox.showinfo('Atelier', 'La liste des maillots du jeu est encore en lecture, attends quelques secondes.')
            return
        ids = {m['id'] for m in self.projet['maillots']}
        nom = 'Nouveau maillot %d' % (len(ids) + 1)
        m = {'id': A.identifiant(nom, ids), 'nom': nom, 'prix': 1, 'base': self.cat[0]['cle'] if self.cat else ''}
        self.projet['maillots'].append(m)
        A.sauver_projet(self.projet)
        self._rafraichir_liste(len(self.projet['maillots']) - 1)
        self.log('nouveau maillot : choisis un nom et un maillot de base, puis « Exporter les images »')

    def _supprimer(self):
        s = self.liste.curselection()
        if not s:
            return
        m = self.projet['maillots'][s[0]]
        if not messagebox.askyesno('Atelier', 'Supprimer « %s » de la liste ?\n(Tes images ne sont pas effacées. '
                                              'Il disparaîtra du jeu à la prochaine construction.)' % m['nom']):
            return
        del self.projet['maillots'][s[0]]
        A.sauver_projet(self.projet); self.courant = None
        self._rafraichir_liste()

    def _enregistrer(self, silencieux=False):
        m = self.courant
        if not m:
            return False
        nom = self.v_nom.get().strip()
        if not nom:
            messagebox.showwarning('Atelier', 'Donne un nom au maillot.'); return False
        m['nom'] = nom
        try:
            m['prix'] = max(0, int(self.v_prix.get()))
        except (tk.TclError, ValueError):
            m['prix'] = 1
        for k, _ in CHAMPS:
            v = self.v_img[k].get().strip()
            if v and not os.path.exists(v):
                messagebox.showwarning('Atelier', 'Fichier introuvable :\n' + v); return False
            m[k] = v or None
        A.sauver_projet(self.projet)
        i = self.projet['maillots'].index(m)
        self.liste.delete(i); self.liste.insert(i, m['nom']); self.liste.selection_set(i)
        if not silencieux:
            self.log('« %s » enregistré' % m['nom'])
        return True

    def _parcourir(self, k):
        d = A.dossier_travail(self.courant) if self.courant else ICI
        p = filedialog.askopenfilename(title='Choisir une image PNG', initialdir=d, filetypes=[('Images PNG', '*.png')])
        if p:
            self.v_img[k].set(os.path.normpath(p))
            self._enregistrer(True)
            self._apercu()

    def _ouvrir_dossier(self):
        if self.courant:
            subprocess.Popen(['explorer', A.dossier_travail(self.courant)])

    def _exporter(self):
        if not self._enregistrer(True):
            return
        m = dict(self.courant)
        def fait():
            d = A.dossier_travail(self.courant)
            for k, f in (('haut_dom', 'haut_domicile.png'), ('short_dom', 'short_domicile.png'),
                         ('haut_ext', 'haut_exterieur.png'), ('short_ext', 'short_exterieur.png')):
                pass   # on ne remplit pas : l'utilisateur choisit ce qu'il a modifié
            subprocess.Popen(['explorer', d])
            messagebox.showinfo('Atelier', 'Les images du maillot de base sont dans le dossier qui vient de s\'ouvrir.\n\n'
                                'Modifie-les (garde la même taille), enregistre-les en PNG, puis choisis-les dans '
                                '« Mes images ». Seul le haut domicile est obligatoire.')
        self.tache(lambda: A.exporter_base(m, self.cat_par_cle, self.rgl['donnees'], self.log), 'Export des images', fait)

    def _construire(self):
        if self.courant and not self._enregistrer(True):
            return
        if not self.projet['maillots']:
            messagebox.showinfo('Atelier', 'Ajoute d\'abord un maillot.'); return
        manque = [m['nom'] for m in self.projet['maillots'] if not m.get('haut_dom')]
        if manque:
            messagebox.showwarning('Atelier', 'Il manque l\'image du haut domicile pour :\n' + '\n'.join(manque)); return
        jeu = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq nie.exe'], capture_output=True, text=True).stdout
        if 'nie.exe' in jeu:
            if not messagebox.askyesno('Atelier', 'Le jeu est ouvert : le mod sera pris en compte au prochain lancement.\nContinuer ?'):
                return
        projet = {'maillots': [dict(m) for m in self.projet['maillots']]}
        def run():
            with multiprocessing.Pool(max(1, (os.cpu_count() or 2) - 1)) as pool:
                A.construire_mod(projet, self.cat_par_cle, self.rgl, pool, self.log)
        self.tache(run, 'Construction du mod', lambda: messagebox.showinfo(
            'Atelier', 'Mod « Mes maillots » installé et activé.\nRelance le jeu : tes maillots sont à la boutique générale.'))


if __name__ == '__main__':
    multiprocessing.freeze_support()
    Atelier().mainloop()
