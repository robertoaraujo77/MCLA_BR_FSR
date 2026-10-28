// Standalone Windows Forms setup. No game assets, no credentials, no external UI packages.
// Built with the .NET Framework compiler included with Windows; C# 5 syntax.
using System;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace MclaBrFsrSetup {
    static class Program {
        [STAThread]
        static void Main(string[] args) {
            if (args.Length == 2 && args[0] == "--unpack-for-test") {
                try { EmbeddedPayload.Extract(args[1]); Environment.ExitCode = 0; }
                catch (Exception error) { File.WriteAllText(args[1] + ".error.txt", error.ToString()); Environment.ExitCode = 1; }
                return;
            }
            if(args.Length == 2 && (args[0] == "--verify-shortcut" || args[0] == "--create-shortcut")) {
                try { GameShortcut.Create(args[1], args[0] == "--verify-shortcut" ? Path.Combine(args[1], "launch-check.lnk") : null); }
                catch(Exception error) {File.WriteAllText(Path.Combine(args[1], "shortcut-error.txt"),error.ToString());Environment.ExitCode=1;}
                return;
            }
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            bool preview = Array.IndexOf(args, "--preview") >= 0;
#if PREVIEW
            preview = true;
#endif
            var app = new System.Windows.Application();
            app.Run(ModernLauncher.Create());
        }
    }

    static class EmbeddedPayload {
        public const string Hash = "579d14d81e1b19103966fa4b1d8e374404d022036c368b0ca543736d4cc67654";
        public const string Version = "1.0.2";
        public static string Extract(string requested) {
            string parent = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "MCLA_LA_Recompiled", "Installer", "Packages");
            string target = requested ?? Path.Combine(parent, Hash.Substring(0,16));
            string ready = Path.Combine(target, ".bundle-ready");
            if (File.Exists(ready) && File.ReadAllText(ready) == Hash) return target;
            if (Directory.Exists(target) && Directory.GetFileSystemEntries(target).Length != 0)
                throw new IOException("O cache do pacote está incompleto. Escolha outra pasta.");
            Directory.CreateDirectory(target);
            string prefix = Path.GetFullPath(target).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            using (var resource = Assembly.GetExecutingAssembly().GetManifestResourceStream("MclaSetup.offline.bundle.zip"))
            using (var zip = new ZipArchive(resource, ZipArchiveMode.Read)) {
                foreach (var item in zip.Entries) {
                    string output = Path.GetFullPath(Path.Combine(target, item.FullName));
                    if (!output.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                        throw new IOException("Caminho inválido no pacote interno.");
                    if (String.IsNullOrEmpty(item.Name)) { Directory.CreateDirectory(output); continue; }
                    Directory.CreateDirectory(Path.GetDirectoryName(output));
                    item.ExtractToFile(output, false);
                }
            }
            File.WriteAllText(ready, Hash);
            return target;
        }
    }

    static class GameShortcut {
        public static void Create(string directory, string shortcutPath = null) {
            Type shellType=Type.GetTypeFromProgID("WScript.Shell");
            object shell=Activator.CreateInstance(shellType);
            object link=null;
            try {
                string path=shortcutPath ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory),"Midnight Club L.A. Recompiled.lnk");
                if(shortcutPath == null && File.Exists(path)) {
                    object existing=shellType.InvokeMember("CreateShortcut",BindingFlags.InvokeMethod,null,shell,new object[]{path});
                    string previous=Convert.ToString(existing.GetType().InvokeMember("TargetPath",BindingFlags.GetProperty,null,existing,null));
                    System.Runtime.InteropServices.Marshal.FinalReleaseComObject(existing);
                    if(!String.Equals(previous,Path.Combine(directory,"mcla.exe"),StringComparison.OrdinalIgnoreCase)) {
                        string stem=Path.Combine(Path.GetDirectoryName(path),Path.GetFileNameWithoutExtension(path));
                        int suffix=2;while(File.Exists(stem+" ("+suffix+").lnk")) suffix++;
                        path=stem+" ("+suffix+").lnk";
                    }
                }
                link=shellType.InvokeMember("CreateShortcut",BindingFlags.InvokeMethod,null,shell,new object[]{path});
                Type type=link.GetType();
                foreach(var pair in new[]{new[]{"TargetPath",Path.Combine(directory,"mcla.exe")},new[]{"WorkingDirectory",Path.GetDirectoryName(Path.Combine(directory,"mcla.exe"))},new[]{"IconLocation",Path.Combine(directory,"game.ico")+",0"},new[]{"Description","Midnight Club L.A. Recompiled"}})
                    type.InvokeMember(pair[0],BindingFlags.SetProperty,null,link,new object[]{pair[1]});
                type.InvokeMember("Save",BindingFlags.InvokeMethod,null,link,null);
            } finally {if(link!=null) System.Runtime.InteropServices.Marshal.FinalReleaseComObject(link);System.Runtime.InteropServices.Marshal.FinalReleaseComObject(shell);}
        }
    }

}
