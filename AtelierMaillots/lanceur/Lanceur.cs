// Atelier Maillots.exe : lance atelier.py (dans le dossier de l'exe) avec pythonw, sans fenêtre de console.
using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

[assembly: System.Reflection.AssemblyTitle("Atelier Maillots")]
[assembly: System.Reflection.AssemblyProduct("Atelier Maillots")]
[assembly: System.Reflection.AssemblyVersion("1.0.0.0")]

static class Lanceur
{
    static string TrouverPythonw()
    {
        string[] fixes = {
            @"C:\Python314\pythonw.exe",
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), @"Programs\Python\Python314\pythonw.exe"),
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), @"Programs\Python\Python313\pythonw.exe"),
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), @"Programs\Python\Python312\pythonw.exe"),
        };
        foreach (string f in fixes)
            if (File.Exists(f)) return f;
        string chemin = Environment.GetEnvironmentVariable("PATH") ?? "";
        foreach (string d in chemin.Split(';'))
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

    [STAThread]
    static void Main()
    {
        string dossier = AppDomain.CurrentDomain.BaseDirectory;
        string script = Path.Combine(dossier, "atelier.py");
        if (!File.Exists(script))
        {
            MessageBox.Show("atelier.py est introuvable à côté de ce programme :\n" + dossier +
                "\n\nGarde « Atelier Maillots.exe » dans le dossier de l'atelier (utilise un raccourci pour le bureau).",
                "Atelier Maillots", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return;
        }
        string py = TrouverPythonw();
        if (py == null)
        {
            MessageBox.Show("Python (pythonw.exe) est introuvable.\nInstalle Python 3 depuis python.org, puis relance l'atelier.",
                "Atelier Maillots", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return;
        }
        var info = new ProcessStartInfo(py, "\"" + script + "\"");
        info.WorkingDirectory = dossier;
        info.UseShellExecute = false;
        Process.Start(info);
    }
}
