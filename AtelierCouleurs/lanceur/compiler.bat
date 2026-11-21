@echo off
rem Recompile « Atelier Inazuma.exe » (compilateur C# de Windows, WebView2 de lanceur\webview2) et le pose dans AtelierCouleurs
cd /d "%~dp0"
"%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe" /nologo /target:winexe /platform:x64 /win32icon:inazuma.ico /r:System.Windows.Forms.dll /r:System.Drawing.dll /r:webview2\Microsoft.Web.WebView2.Core.dll /r:webview2\Microsoft.Web.WebView2.WinForms.dll /out:"..\Atelier Inazuma.exe" Lanceur.cs
pause
