// « Atelier Inazuma.exe » à la RACINE du dossier téléchargé : le programme à double-cliquer, facile à trouver.
// Il lance simplement AtelierCouleurs\Atelier Inazuma.exe (la vraie fenêtre de l'Atelier).
// Root launcher: just starts AtelierCouleurs\Atelier Inazuma.exe.
using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

[assembly: System.Reflection.AssemblyTitle("Atelier Inazuma")]
[assembly: System.Reflection.AssemblyProduct("Atelier Inazuma")]
[assembly: System.Reflection.AssemblyVersion("2.0.0.0")]

static class Racine
{
    [STAThread]
    static void Main()
    {
        string d = AppDomain.CurrentDomain.BaseDirectory;
        string exe = Path.Combine(d, "AtelierCouleurs", "Atelier Inazuma.exe");
        if (!File.Exists(exe))
        {
            MessageBox.Show("AtelierCouleurs\\Atelier Inazuma.exe est introuvable.\nDécompresse tout le dossier avant de lancer l'Atelier." +
                            "\n\nAtelierCouleurs\\Atelier Inazuma.exe not found.\nExtract the whole folder before starting the Atelier.",
                            "Atelier Inazuma", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return;
        }
        var info = new ProcessStartInfo(exe);
        info.WorkingDirectory = Path.GetDirectoryName(exe);
        info.UseShellExecute = false;
        Process.Start(info);
    }
}
