// Atelier Inazuma.exe : une vraie fenêtre Windows (WinForms + WebView2, le moteur d'affichage des apps de Windows),
// sans navigateur. Démarre le serveur de l'atelier (serveur.py avec pythonw : pas de fenêtre noire), affiche l'atelier
// dans la fenêtre, et arrête le serveur quand on ferme la fenêtre.
// Bibliothèques WebView2 (Microsoft, redistribuables) dans lanceur\webview2. Compilé par lanceur\compiler.bat.
// Ancienne version (fenêtre Edge en mode app) : Lanceur_edge.cs.bak.
using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Net.Sockets;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Text.RegularExpressions;
using System.Threading;
using System.Windows.Forms;

[assembly: AssemblyTitle("Atelier Inazuma")]
[assembly: AssemblyProduct("Atelier Inazuma")]
[assembly: AssemblyVersion("2.0.0.0")]

static class Lanceur
{
    public const string TITRE = "Atelier Inazuma";
    public static string Dossier, Libs;

    [STAThread]
    static void Main()
    {
        Dossier = AppDomain.CurrentDomain.BaseDirectory;
        Libs = Path.Combine(Dossier, "lanceur", "webview2");
        // les bibliothèques WebView2 sont dans lanceur\webview2 (pas à côté de l'exe)
        AppDomain.CurrentDomain.AssemblyResolve += (s, e) =>
        {
            string p = Path.Combine(Libs, new AssemblyName(e.Name).Name + ".dll");
            return File.Exists(p) ? Assembly.UnsafeLoadFrom(p) : null;   // Unsafe : fichiers venus d'internet (zip téléchargé)
        };
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        if (!File.Exists(Path.Combine(Dossier, "serveur.py")))
        {
            Erreur("serveur.py est introuvable à côté de ce programme :\n" + Dossier +
                   "\n\nGarde « Atelier Inazuma.exe » dans le dossier AtelierCouleurs (utilise un raccourci pour le bureau).");
            return;
        }
        ReprendreAncienneVersion();
        Debloquer();
        RaccourciBureau();
        Lancer();
    }

    [System.Runtime.InteropServices.DllImport("kernel32.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode)]
    static extern bool DeleteFile(string nom);

    // zip téléchargé : Windows marque chaque fichier « venu d'internet » (flux Zone.Identifier) et redemande à chaque
    // lancement s'il faut l'exécuter. Une fois l'Atelier lancé, on retire cette marque de SES fichiers (une seule fois) :
    // le dossier téléchargé entier s'il a son python\, sinon seulement AtelierCouleurs.
    static void Debloquer()
    {
        try
        {
            string marque = Path.Combine(Dossier, "cache", "debloque.txt");
            if (File.Exists(marque)) return;
            string parent = Path.GetFullPath(Path.Combine(Dossier, ".."));
            string racine = Directory.Exists(Path.Combine(parent, "python")) ? parent : Dossier;
            foreach (string f in Directory.EnumerateFiles(racine, "*", SearchOption.AllDirectories))
                DeleteFile(f + ":Zone.Identifier");
            Directory.CreateDirectory(Path.GetDirectoryName(marque));
            File.WriteAllText(marque, racine);
        }
        catch (Exception) { }
    }

    // numéro de version (version.txt à côté de l'exe) : dans le titre de la fenêtre et en haut du journal
    public static string VersionDe(string dossier)
    {
        try { return File.ReadAllText(Path.Combine(dossier, "version.txt")).Trim(); } catch (Exception) { return ""; }
    }

    public static string TitreComplet()
    {
        string v = VersionDe(Dossier);
        return v.Length > 0 ? TITRE + " " + v : TITRE;
    }

    static Version NumeroDe(string dossier)
    {
        try { return new Version(VersionDe(dossier)); } catch (Exception) { return new Version(0, 0); }
    }

    static bool EstPaquet(string dossierAtelier)      // dossier téléchargé (zip) : il a son python\ à côté
    {
        try { return Directory.Exists(Path.Combine(Path.GetFullPath(Path.Combine(dossierAtelier, "..")), "python")); }
        catch (Exception) { return false; }
    }

    // ---------------------------------------------------------------- reprise des données d'une version précédente
    // Une nouvelle version décompressée dans un AUTRE dossier repartait de zéro : long 1er démarrage refait, créations
    // restées dans l'ancien dossier. Au 1er lancement d'un téléchargement, on retrouve la version précédente (raccourci
    // du bureau, dossiers voisins) et on reprend ses données (une seule fois ; détail dans cache\reprise.txt).
    static readonly string[] DOSSIERS_REPRIS = { @"AtelierCouleurs\cache", @"AtelierCouleurs\projets", @"AtelierCouleurs\sortie",
        @"AtelierCouleurs\maillots", @"AtelierMaillots\travail", @"AtelierMaillots\cache_textures", "Sauvegardes Atelier" };
    static readonly string[] FICHIERS_REPRIS = { @"AtelierCouleurs\config.json", @"AtelierCouleurs\prereglages.json",
        @"AtelierMaillots\reglages.json", @"AtelierMaillots\catalogue.json", @"AtelierMaillots\mes_maillots.json" };

    static bool EstRacinePaquet(string r)
    {
        return r != null && File.Exists(Path.Combine(r, "AtelierCouleurs", "Atelier Inazuma.exe")) && Directory.Exists(Path.Combine(r, "python"));
    }

    static bool AUnContenu(string d)
    {
        try { return Directory.Exists(d) && Directory.EnumerateFileSystemEntries(d).GetEnumerator().MoveNext(); } catch (Exception) { return false; }
    }

    static System.Collections.Generic.List<string> TrouverAnciennes(string racine)
    {
        var cand = new System.Collections.Generic.List<string>();
        try                                                       // 1. la cible du raccourci du bureau
        {
            string lnk = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), "Atelier Inazuma.lnk");
            if (File.Exists(lnk))
            {
                Type t = Type.GetTypeFromProgID("WScript.Shell");
                object sh = Activator.CreateInstance(t);
                object l = t.InvokeMember("CreateShortcut", BindingFlags.InvokeMethod, null, sh, new object[] { lnk });
                string cible = (string)l.GetType().InvokeMember("TargetPath", BindingFlags.GetProperty, null, l, null);
                cand.Add(Path.GetFullPath(Path.Combine(Path.GetDirectoryName(cible), "..")));
            }
        }
        catch (Exception) { }
        // 2. les dossiers voisins (et un niveau dedans), depuis le dossier parent ET le grand-parent : Windows décompresse
        //    « AtelierInazuma (1).zip » dans Téléchargements\AtelierInazuma (1)\AtelierInazuma, l'ancienne étant dans
        //    Téléchargements\AtelierInazuma\AtelierInazuma
        string bas = Path.GetDirectoryName(racine);
        for (int niveau = 0; niveau < 2 && bas != null; niveau++, bas = Path.GetDirectoryName(bas))
        {
            try
            {
                foreach (string d in Directory.GetDirectories(bas))
                {
                    cand.Add(d);
                    try { foreach (string s in Directory.GetDirectories(d)) cand.Add(s); } catch (Exception) { }
                }
            }
            catch (Exception) { }
        }
        // toutes les versions précédentes trouvées, la préférée d'abord (version la plus haute, puis la plus récemment
        // utilisée) : chaque élément est repris de la PREMIÈRE qui l'a (créations d'un dossier, cache d'un autre…)
        var res = new System.Collections.Generic.List<Tuple<string, Version, DateTime>>();
        var vus = new System.Collections.Generic.HashSet<string>(StringComparer.OrdinalIgnoreCase);
        Version vIci = NumeroDe(Dossier);
        foreach (string c0 in cand)
        {
            string c = Path.GetFullPath(c0).TrimEnd('\\');
            if (!vus.Add(c) || !EstRacinePaquet(c) || string.Equals(c, racine.TrimEnd('\\'), StringComparison.OrdinalIgnoreCase)) continue;
            string ac = Path.Combine(c, "AtelierCouleurs");
            if (!AUnContenu(Path.Combine(ac, "cache")) && !AUnContenu(Path.Combine(ac, "projets")) && !AUnContenu(Path.Combine(ac, "sortie"))) continue;
            Version v = NumeroDe(ac);
            if (v > vIci) continue;                                  // jamais les données d'une version plus récente
            DateTime t = DateTime.MinValue;
            try { t = Directory.GetLastWriteTime(Path.Combine(ac, "cache")); } catch (Exception) { }
            res.Add(Tuple.Create(c, v, t));
        }
        res.Sort((x, y) => x.Item2 != y.Item2 ? y.Item2.CompareTo(x.Item2) : y.Item3.CompareTo(x.Item3));
        return res.ConvertAll(x => x.Item1);
    }

    static void CopierDossier(string src, string dst)
    {
        Directory.CreateDirectory(dst);
        foreach (string f in Directory.GetFiles(src))
            try { File.Copy(f, Path.Combine(dst, Path.GetFileName(f)), true); } catch (Exception) { }
        foreach (string d in Directory.GetDirectories(src))
            CopierDossier(d, Path.Combine(dst, Path.GetFileName(d)));
    }

    static void ReprendreAncienneVersion()
    {
        try
        {
            string racine = Path.GetFullPath(Path.Combine(Dossier, ".."));
            string marque = Path.Combine(Dossier, "cache", "reprise.txt");
            if (!EstRacinePaquet(racine) || File.Exists(marque)) return;
            var anciennes = TrouverAnciennes(racine);
            var rapport = new System.Text.StringBuilder();
            if (anciennes.Count > 0)
            {
                foreach (string a in anciennes)
                    rapport.AppendLine("version précédente : " + a + " (" + VersionDe(Path.Combine(a, "AtelierCouleurs")) + ")");
                foreach (string rel in DOSSIERS_REPRIS)
                {
                    string ancienne = anciennes.Find(a => AUnContenu(Path.Combine(a, rel)));
                    if (ancienne == null) continue;
                    string src = Path.Combine(ancienne, rel), dst = Path.Combine(racine, rel);
                    // le cache neuf n'est gardé que s'il est complet (index des textures fini) ; les créations ne sont
                    // jamais écrasées : si la nouvelle version en a déjà, on ne touche à rien
                    if (AUnContenu(dst) && !(rel.EndsWith("cache") && !File.Exists(Path.Combine(dst, "index_tx_chr.json")))) continue;
                    try
                    {
                        if (Directory.Exists(dst)) Directory.Delete(dst, true);
                        try { Directory.Move(src, dst); rapport.AppendLine("déplacé : " + rel + " (de " + ancienne + ")"); }
                        catch (Exception) { CopierDossier(src, dst); rapport.AppendLine("copié : " + rel + " (de " + ancienne + ")"); }
                    }
                    catch (Exception ex) { rapport.AppendLine("pas repris : " + rel + " (" + ex.Message + ")"); }
                }
                foreach (string rel in FICHIERS_REPRIS)
                {
                    string ancienne = anciennes.Find(a => File.Exists(Path.Combine(a, rel)));
                    if (ancienne == null) continue;
                    string src = Path.Combine(ancienne, rel), dst = Path.Combine(racine, rel);
                    try
                    {
                        string txt = File.ReadAllText(src);
                        // chemins de l'ancien dossier (ex. sauvegardes_dir) -> le nouveau ; dans le JSON, « \ » est écrit « \\ »
                        txt = Regex.Replace(txt, Regex.Escape(ancienne.TrimEnd('\\').Replace("\\", "\\\\")),
                                            racine.TrimEnd('\\').Replace("\\", "\\\\").Replace("$", "$$"), RegexOptions.IgnoreCase);
                        File.WriteAllText(dst, txt);
                        rapport.AppendLine("repris : " + rel);
                    }
                    catch (Exception ex) { rapport.AppendLine("pas repris : " + rel + " (" + ex.Message + ")"); }
                }
            }
            else rapport.AppendLine("aucune version précédente trouvée");
            // le cache repris porte les marques de l'ANCIEN dossier : celui-ci doit encore être débloqué (zip téléchargé)
            try { File.Delete(Path.Combine(Dossier, "cache", "debloque.txt")); } catch (Exception) { }
            Directory.CreateDirectory(Path.GetDirectoryName(marque));
            File.WriteAllText(marque, rapport.ToString());
        }
        catch (Exception) { }
    }

    // raccourci « Atelier Inazuma » sur le bureau : créé au 1er lancement (s'il est supprimé, il ne revient pas). S'il mène
    // à une version téléchargée PLUS ANCIENNE (ou disparue), il est remis sur celle-ci : sinon, après avoir décompressé une
    // nouvelle version ailleurs, le raccourci ouvrait toujours l'ancienne.
    static void RaccourciBureau()
    {
        try
        {
            string marque = Path.Combine(Dossier, "cache", "raccourci_bureau.txt");
            string lnk = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), "Atelier Inazuma.lnk");
            Type t = Type.GetTypeFromProgID("WScript.Shell");
            object sh = Activator.CreateInstance(t);
            bool ecrire = false;
            if (!File.Exists(lnk))
                ecrire = !File.Exists(marque);
            else if (EstPaquet(Dossier))
            {
                object l = t.InvokeMember("CreateShortcut", BindingFlags.InvokeMethod, null, sh, new object[] { lnk });
                string cible = (string)l.GetType().InvokeMember("TargetPath", BindingFlags.GetProperty, null, l, null);
                string ici = Path.GetFullPath(Application.ExecutablePath);
                if (!string.Equals(Path.GetFullPath(cible), ici, StringComparison.OrdinalIgnoreCase)
                    && Path.GetFileName(cible).Equals("Atelier Inazuma.exe", StringComparison.OrdinalIgnoreCase))
                {
                    string dCible = Path.GetDirectoryName(cible);
                    ecrire = !File.Exists(cible) || (EstPaquet(dCible) && NumeroDe(dCible) < NumeroDe(Dossier));
                }
            }
            if (ecrire)
            {
                object s = t.InvokeMember("CreateShortcut", BindingFlags.InvokeMethod, null, sh, new object[] { lnk });
                Type st = s.GetType();
                st.InvokeMember("TargetPath", BindingFlags.SetProperty, null, s, new object[] { Application.ExecutablePath });
                st.InvokeMember("WorkingDirectory", BindingFlags.SetProperty, null, s, new object[] { Dossier });
                st.InvokeMember("IconLocation", BindingFlags.SetProperty, null, s, new object[] { Application.ExecutablePath + ",0" });
                st.InvokeMember("Description", BindingFlags.SetProperty, null, s, new object[] { TitreComplet() });
                st.InvokeMember("Save", BindingFlags.InvokeMethod, null, s, null);
            }
            if (!File.Exists(marque))
            {
                Directory.CreateDirectory(Path.GetDirectoryName(marque));
                File.WriteAllText(marque, lnk);
            }
        }
        catch (Exception) { }
    }

    [MethodImpl(MethodImplOptions.NoInlining)]          // charge WebView2 seulement après AssemblyResolve
    static void Lancer()
    {
        Application.Run(new Fenetre());
    }

    public static void Erreur(string texte)
    {
        MessageBox.Show(texte, TITRE, MessageBoxButtons.OK, MessageBoxIcon.Error);
    }

    public static long TailleFichier(string f)
    {
        try { return File.Exists(f) ? new FileInfo(f).Length : 0; } catch (Exception) { return 0; }
    }

    // ce que le serveur a écrit dans son journal pendant CE lancement (les dernières lignes) : la raison d'un échec
    public static string FinJournal(string f, long depuis)
    {
        try
        {
            using (var fs = new FileStream(f, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete))
            {
                if (depuis > 0 && depuis <= fs.Length) fs.Seek(depuis, SeekOrigin.Begin);
                string t = new StreamReader(fs, System.Text.Encoding.UTF8).ReadToEnd().Trim();
                string[] l = t.Split('\n');
                int n = Math.Min(l.Length, 12);
                string fin = string.Join("\n", l, l.Length - n, n).Trim();
                return fin.Length > 1500 ? "…" + fin.Substring(fin.Length - 1500) : fin;
            }
        }
        catch (Exception) { return ""; }
    }

    static bool JeuValide(string d)
    {
        return d != null && File.Exists(Path.Combine(d, "nie.exe")) && File.Exists(Path.Combine(d, "data", "cpk_list.cfg.bin"));
    }

    // le jeu n'a pas été trouvé tout seul : on demande son dossier (celui qui contient nie.exe) ; null = abandon
    public static string ChoisirJeu()
    {
        MessageBox.Show("Le jeu Inazuma Eleven : Victory Road n'a pas été trouvé automatiquement.\n" +
                        "Choisis son dossier : celui qui contient nie.exe (et le dossier data).\n\n" +
                        "Inazuma Eleven: Victory Road was not found automatically.\n" +
                        "Pick its folder: the one that contains nie.exe (and the data folder).",
                        TITRE, MessageBoxButtons.OK, MessageBoxIcon.Information);
        while (true)
        {
            using (var dlg = new FolderBrowserDialog())
            {
                dlg.Description = "Dossier du jeu (avec nie.exe) / Game folder (with nie.exe)";
                dlg.ShowNewFolderButton = false;
                if (dlg.ShowDialog() != DialogResult.OK) return null;
                string d = dlg.SelectedPath;
                if (JeuValide(d)) return d;
                try
                {
                    foreach (string s in Directory.GetDirectories(d))       // dossier parent choisi : on regarde dedans
                        if (JeuValide(s)) return s;
                }
                catch (Exception) { }
                if (MessageBox.Show("Ce dossier ne contient pas le jeu (nie.exe + data\\cpk_list.cfg.bin).\n" +
                                    "This folder doesn't contain the game (nie.exe + data\\cpk_list.cfg.bin).\n\n" + d,
                                    TITRE, MessageBoxButtons.RetryCancel, MessageBoxIcon.Warning) != DialogResult.Retry)
                    return null;
            }
        }
    }

    public static string TrouverPythonw()
    {
        string fourni = Path.GetFullPath(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "python", "pythonw.exe"));
        if (File.Exists(fourni)) { Environment.SetEnvironmentVariable("PYTHONNOUSERSITE", "1"); return fourni; }   // Python fourni
        string local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        string[] fixes = {
            @"C:\Python314\pythonw.exe",
            Path.Combine(local, @"Programs\Python\Python314\pythonw.exe"),
            Path.Combine(local, @"Programs\Python\Python313\pythonw.exe"),
            Path.Combine(local, @"Programs\Python\Python312\pythonw.exe"),
        };
        foreach (string f in fixes)
            if (File.Exists(f)) return f;
        foreach (string d in (Environment.GetEnvironmentVariable("PATH") ?? "").Split(';'))
        {
            try
            {
                string f = Path.Combine(d.Trim(), "pythonw.exe");
                if (File.Exists(f) && !f.ToLower().Contains("venv")) return f;
            }
            catch (ArgumentException) { }
        }
        return null;
    }

    public static bool PortOuvert(int port)
    {
        try
        {
            using (var c = new TcpClient())
            {
                var r = c.BeginConnect("127.0.0.1", port, null, null);
                bool ok = r.AsyncWaitHandle.WaitOne(300);
                if (ok) c.EndConnect(r);
                return ok && c.Connected;
            }
        }
        catch (Exception) { return false; }
    }

    public static int LirePort()
    {
        try
        {
            var m = Regex.Match(File.ReadAllText(Path.Combine(Dossier, "config.json")), "\"port\"\\s*:\\s*(\\d+)");
            if (m.Success) return int.Parse(m.Groups[1].Value);
        }
        catch (Exception) { }
        return 8765;
    }
}

class Fenetre : Form
{
    Microsoft.Web.WebView2.WinForms.WebView2 vue;
    Label attente;
    Process serveur;
    int port;

    public Fenetre()
    {
        Text = Lanceur.TitreComplet();
        try { Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath); } catch (Exception) { }
        ClientSize = new Size(1500, 900);
        MinimumSize = new Size(1000, 640);
        StartPosition = FormStartPosition.CenterScreen;
        BackColor = Color.FromArgb(15, 17, 23);
        attente = new Label();
        attente.Text = "Démarrage de l'Atelier Inazuma…\n\n1er lancement : quelques minutes (une seule fois)\nFirst run: a few minutes (only once)";
        attente.ForeColor = Color.FromArgb(240, 180, 41);
        attente.Font = new Font("Segoe UI", 16f);
        attente.Dock = DockStyle.Fill;
        attente.TextAlign = ContentAlignment.MiddleCenter;
        Controls.Add(attente);
        Shown += (s, e) => Demarrer();
        FormClosed += (s, e) => Arreter();
    }

    async void Demarrer()
    {
        port = Lanceur.LirePort();
        string url = "http://127.0.0.1:" + port + "/";
        // 1. le serveur (s'il ne tourne pas déjà)
        if (!Lanceur.PortOuvert(port))
        {
            string py = Lanceur.TrouverPythonw();
            if (py == null)
            {
                Lanceur.Erreur("Python (pythonw.exe) est introuvable.\nInstalle Python 3 depuis python.org, puis relance l'atelier.");
                Close(); return;
            }
            string log = Path.Combine(Lanceur.Dossier, "cache", "serveur.log");
            string jeu = null;
            while (true)
            {
                long debutLog = Lanceur.TailleFichier(log);
                var info = new ProcessStartInfo(py, "\"" + Path.Combine(Lanceur.Dossier, "serveur.py") + "\" --sans-navigateur" +
                                                    (jeu != null ? " --jeu \"" + jeu.TrimEnd('\\') + "\"" : ""));
                info.WorkingDirectory = Lanceur.Dossier;
                info.UseShellExecute = false;
                info.CreateNoWindow = true;
                serveur = Process.Start(info);
                bool pret = await System.Threading.Tasks.Task.Run(() =>
                {
                    var debut = DateTime.Now;
                    while (!Lanceur.PortOuvert(port))
                    {
                        if (serveur.HasExited || (DateTime.Now - debut).TotalSeconds > 900) return false;
                        Thread.Sleep(250);
                    }
                    return true;
                });
                if (pret) break;
                string fin = Lanceur.FinJournal(log, debutLog);
                // jeu introuvable : on demande où il est (dossier qui contient nie.exe), puis on relance le serveur
                if (serveur.HasExited && fin.Contains("JEU INTROUVABLE"))
                {
                    jeu = Lanceur.ChoisirJeu();
                    if (jeu != null) continue;
                    Close(); return;
                }
                Lanceur.Erreur("Le serveur de l'atelier n'a pas démarré / The Atelier server did not start.\n\n" +
                               (fin.Length > 0 ? fin : "(journal vide / empty log)") + "\n\nJournal / log : " + log);
                Close(); return;
            }
        }
        // 2. l'affichage (WebView2)
        try
        {
            Microsoft.Web.WebView2.Core.CoreWebView2Environment.SetLoaderDllFolderPath(Lanceur.Libs);
            var env = await Microsoft.Web.WebView2.Core.CoreWebView2Environment.CreateAsync(null,
                Path.Combine(Lanceur.Dossier, "cache", "webview2"));
            vue = new Microsoft.Web.WebView2.WinForms.WebView2();
            vue.Dock = DockStyle.Fill;
            vue.DefaultBackgroundColor = Color.FromArgb(15, 17, 23);
            Controls.Add(vue);
            await vue.EnsureCoreWebView2Async(env);
            var r = vue.CoreWebView2.Settings;
            r.IsStatusBarEnabled = false;            // pas d'adresse en bas de la fenêtre
            r.AreDevToolsEnabled = false;
            r.IsZoomControlEnabled = false;
            vue.CoreWebView2.DocumentTitleChanged += (s, e) => Text = Lanceur.TitreComplet();
            vue.CoreWebView2.NewWindowRequested += (s, e) => e.Handled = true;   // pas de fenêtre de navigateur
            vue.CoreWebView2.Navigate(url);
            vue.BringToFront();
            Controls.Remove(attente);
        }
        catch (Exception ex)
        {
            Lanceur.Erreur("L'affichage de l'atelier (WebView2) n'a pas pu démarrer :\n" + ex.Message +
                           "\n\nL'atelier s'ouvre dans le navigateur à la place.");
            try { Process.Start(url); } catch (Exception) { }
            serveur = null;                          // le serveur reste ouvert pour le navigateur
            Close();
        }
    }

    void Arreter()
    {
        try { if (vue != null) vue.Dispose(); } catch (Exception) { }
        try { if (serveur != null && !serveur.HasExited) serveur.Kill(); } catch (Exception) { }
    }
}
