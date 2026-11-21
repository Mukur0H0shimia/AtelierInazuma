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

    // raccourci « Atelier Inazuma » sur le bureau, créé au 1er lancement seulement (s'il est supprimé, il ne revient pas)
    static void RaccourciBureau()
    {
        try
        {
            string marque = Path.Combine(Dossier, "cache", "raccourci_bureau.txt");
            if (File.Exists(marque)) return;
            string lnk = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), "Atelier Inazuma.lnk");
            if (!File.Exists(lnk))
            {
                Type t = Type.GetTypeFromProgID("WScript.Shell");
                object sh = Activator.CreateInstance(t);
                object s = t.InvokeMember("CreateShortcut", BindingFlags.InvokeMethod, null, sh, new object[] { lnk });
                Type st = s.GetType();
                st.InvokeMember("TargetPath", BindingFlags.SetProperty, null, s, new object[] { Application.ExecutablePath });
                st.InvokeMember("WorkingDirectory", BindingFlags.SetProperty, null, s, new object[] { Dossier });
                st.InvokeMember("IconLocation", BindingFlags.SetProperty, null, s, new object[] { Application.ExecutablePath + ",0" });
                st.InvokeMember("Description", BindingFlags.SetProperty, null, s, new object[] { "Atelier Inazuma" });
                st.InvokeMember("Save", BindingFlags.InvokeMethod, null, s, null);
            }
            Directory.CreateDirectory(Path.GetDirectoryName(marque));
            File.WriteAllText(marque, lnk);
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
        Text = Lanceur.TITRE;
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
            var info = new ProcessStartInfo(py, "\"" + Path.Combine(Lanceur.Dossier, "serveur.py") + "\" --sans-navigateur");
            info.WorkingDirectory = Lanceur.Dossier;
            info.UseShellExecute = false;
            info.CreateNoWindow = true;
            serveur = Process.Start(info);
            string log = Path.Combine(Lanceur.Dossier, "cache", "serveur.log");
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
            if (!pret)
            {
                Lanceur.Erreur("Le serveur de l'atelier n'a pas démarré.\nJournal : " + log);
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
            vue.CoreWebView2.DocumentTitleChanged += (s, e) => Text = Lanceur.TITRE;
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
