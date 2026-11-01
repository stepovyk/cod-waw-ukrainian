// Інсталятор української локалізації Call of Duty: World at War.
// Латає файли гри гравця на місці (латки містять старі й нові байти), додає власні файли локалізації,
// а видалення повертає старі байти. Файлів Activision інсталятор не містить.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Text;
using System.Threading;
using System.Windows.Forms;
using Microsoft.Win32;

namespace WawUkrainian
{
    class Patch { public int Offset; public byte[] Old; public byte[] New; }

    class Record
    {
        public int Kind;          // 0 – латка exe, 1 – латка зони, 2 – новий файл, 3 – заміна з резервною копією
        public string Path;
        public List<Patch> Patches = new List<Patch>();
        public byte[] Data;
    }

    static class Links
    {
        public const string Donate = "https://send.monobank.ua/jar/8aeC9dGFrn";
        public const string Repo = "https://github.com/stepovyk/cod-waw-ukrainian";
        public const string Telegram = "";
    }

    static class Payload
    {
        public static List<Record> Load()
        {
            var list = new List<Record>();
            using (var s = Assembly.GetExecutingAssembly().GetManifestResourceStream("payload.bin"))
            using (var r = new BinaryReader(s))
            {
                if (Encoding.ASCII.GetString(r.ReadBytes(6)) != "WAWUA1") throw new Exception("Пошкоджений інсталятор.");
                int count = r.ReadInt32();
                for (int i = 0; i < count; i++)
                {
                    var rec = new Record();
                    rec.Kind = r.ReadByte();
                    rec.Path = Encoding.UTF8.GetString(r.ReadBytes(r.ReadUInt16())).Replace('/', '\\');
                    if (rec.Kind <= 1)
                    {
                        int n = r.ReadInt32();
                        for (int k = 0; k < n; k++)
                        {
                            var p = new Patch();
                            p.Offset = r.ReadInt32();
                            int len = r.ReadInt32();
                            p.Old = r.ReadBytes(len);
                            p.New = r.ReadBytes(len);
                            rec.Patches.Add(p);
                        }
                    }
                    else rec.Data = r.ReadBytes(r.ReadInt32());
                    list.Add(rec);
                }
            }
            return list;
        }
    }

    static class Zone
    {
        // Fastfile гри: 12 байтів заголовка ("IWffu100" + версія), далі потік zlib.
        public static byte[] Unpack(byte[] file, out byte[] header)
        {
            header = new byte[12];
            Array.Copy(file, header, 12);
            using (var input = new MemoryStream(file, 14, file.Length - 14))
            using (var inflate = new DeflateStream(input, CompressionMode.Decompress))
            using (var output = new MemoryStream())
            {
                inflate.CopyTo(output);
                return output.ToArray();
            }
        }

        public static byte[] Pack(byte[] header, byte[] data)
        {
            using (var output = new MemoryStream())
            {
                output.Write(header, 0, header.Length);
                output.WriteByte(0x78);
                output.WriteByte(0xDA);
                using (var deflate = new DeflateStream(output, CompressionLevel.Optimal, true))
                    deflate.Write(data, 0, data.Length);
                uint a = 1, b = 0;
                for (int i = 0; i < data.Length; i++)
                {
                    a = (a + data[i]) % 65521;
                    b = (b + a) % 65521;
                }
                uint adler = (b << 16) | a;
                output.WriteByte((byte)(adler >> 24));
                output.WriteByte((byte)(adler >> 16));
                output.WriteByte((byte)(adler >> 8));
                output.WriteByte((byte)adler);
                return output.ToArray();
            }
        }
    }

    class Engine
    {
        const string BackupDir = "ukrainian_backup";
        readonly string game;
        readonly List<Record> records;
        public Action<string> Progress = delegate { };

        public Engine(string game, List<Record> records) { this.game = game; this.records = records; }

        public static bool IsGameDir(string dir)
        {
            try
            {
                return !string.IsNullOrEmpty(dir) && File.Exists(Path.Combine(dir, "CoDWaW.exe"))
                    && Directory.Exists(Path.Combine(dir, "zone", "english"));
            }
            catch (ArgumentException) { return false; }
        }

        public bool Installed
        {
            get
            {
                foreach (var r in records)
                    if (r.Kind == 2 && File.Exists(Path.Combine(game, r.Path))) return true;
                return false;
            }
        }

        static bool Same(byte[] buf, int offset, byte[] what)
        {
            if (offset + what.Length > buf.Length) return false;
            for (int i = 0; i < what.Length; i++) if (buf[offset + i] != what[i]) return false;
            return true;
        }

        byte[] Read(Record r, out byte[] header)
        {
            header = null;
            byte[] file = File.ReadAllBytes(Path.Combine(game, r.Path));
            return r.Kind == 1 ? Zone.Unpack(file, out header) : file;
        }

        void Write(Record r, byte[] header, byte[] data)
        {
            string path = Path.Combine(game, r.Path);
            string tmp = path + ".ukr-tmp";
            File.WriteAllBytes(tmp, r.Kind == 1 ? Zone.Pack(header, data) : data);
            File.Copy(tmp, path, true);
            File.Delete(tmp);
        }

        // toUkrainian: true – ставимо нові байти, false – повертаємо старі
        void ApplyPatches(bool toUkrainian)
        {
            // спершу перевірка всіх файлів, потім запис: гра не лишиться напівзалатаною
            var plan = new List<Record>();
            foreach (var r in records)
            {
                if (r.Kind > 1) continue;
                Progress("Перевірка: " + r.Path);
                if (!File.Exists(Path.Combine(game, r.Path)))
                    throw new Exception("Не знайдено файл гри: " + r.Path);
                byte[] header;
                byte[] data = Read(r, out header);
                int from = 0, to = 0;
                foreach (var p in r.Patches)
                {
                    if (Same(data, p.Offset, toUkrainian ? p.Old : p.New)) from++;
                    else if (Same(data, p.Offset, toUkrainian ? p.New : p.Old)) to++;
                    else throw new Exception("Ця версія файлу не підтримується: " + r.Path +
                        "\nПотрібна Call of Duty: World at War версії 1.7 з англійською мовою.");
                }
                if (from > 0 && to > 0) throw new Exception("Файл змінено частково: " + r.Path);
                if (from > 0) plan.Add(r);
            }
            foreach (var r in plan)
            {
                Progress((toUkrainian ? "Встановлення: " : "Відновлення: ") + r.Path);
                byte[] header;
                byte[] data = Read(r, out header);
                foreach (var p in r.Patches)
                {
                    byte[] src = toUkrainian ? p.New : p.Old;
                    Array.Copy(src, 0, data, p.Offset, src.Length);
                }
                Write(r, header, data);
            }
        }

        public void Install()
        {
            ApplyPatches(true);
            foreach (var r in records)
            {
                string path = Path.Combine(game, r.Path);
                if (r.Kind == 3)
                {
                    string backup = Path.Combine(game, BackupDir, r.Path);
                    if (!File.Exists(backup) && File.Exists(path))
                    {
                        Directory.CreateDirectory(Path.GetDirectoryName(backup));
                        File.Copy(path, backup);
                    }
                }
                if (r.Kind >= 2)
                {
                    Progress("Встановлення: " + r.Path);
                    Directory.CreateDirectory(Path.GetDirectoryName(path));
                    File.WriteAllBytes(path, r.Data);
                }
            }
            Profiles.ClassNames(true);
        }

        public void Remove()
        {
            ApplyPatches(false);
            foreach (var r in records)
            {
                string path = Path.Combine(game, r.Path);
                if (r.Kind == 2 && File.Exists(path)) File.Delete(path);
                if (r.Kind == 3)
                {
                    string backup = Path.Combine(game, BackupDir, r.Path);
                    if (File.Exists(backup))
                    {
                        File.Copy(backup, path, true);
                        File.Delete(backup);
                    }
                }
            }
            string dir = Path.Combine(game, BackupDir);
            if (Directory.Exists(dir) && Directory.GetFiles(dir, "*", SearchOption.AllDirectories).Length == 0)
                Directory.Delete(dir, true);
            Profiles.ClassNames(false);
        }
    }

    static class Profiles
    {
        // Стандартні назви своїх класів зберігаються в профілі гравця (seta customclassN "Custom N").
        public static void ClassNames(bool toUkrainian)
        {
            string root = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "Activision", "CoDWaW", "players", "profiles");
            if (!Directory.Exists(root)) return;
            var enc = Encoding.GetEncoding(1251);
            foreach (string dir in Directory.GetDirectories(root))
                foreach (string cfg in Directory.GetFiles(dir, "config*.cfg"))
                {
                    try
                    {
                        string text = enc.GetString(File.ReadAllBytes(cfg)), result = text;
                        for (int n = 1; n <= 10; n++)
                        {
                            string en = "seta customclass" + n + " \"Custom " + n + "\"";
                            string uk = "seta customclass" + n + " \"Свій клас " + n + "\"";
                            result = toUkrainian ? result.Replace(en, uk) : result.Replace(uk, en);
                        }
                        if (result != text) File.WriteAllBytes(cfg, enc.GetBytes(result));
                    }
                    catch (IOException) { }
                }
        }
    }

    class MainForm : Form
    {
        readonly List<Record> records = Payload.Load();
        readonly TextBox path = new TextBox();
        readonly Label status = new Label();
        readonly Button install = new Button(), remove = new Button(), browse = new Button();

        static readonly Color Ink = Color.FromArgb(240, 240, 240), Muted = Color.FromArgb(160, 164, 170),
            Back = Color.FromArgb(22, 24, 27), Panel = Color.FromArgb(36, 39, 44), Accent = Color.FromArgb(255, 205, 0);

        public MainForm()
        {
            Text = "Call of Duty: World at War українською";
            Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath);
            FormBorderStyle = FormBorderStyle.FixedSingle;
            MaximizeBox = false;
            StartPosition = FormStartPosition.CenterScreen;
            BackColor = Back;
            ForeColor = Ink;
            Font = new Font("Segoe UI", 10f);
            AutoScaleMode = AutoScaleMode.Dpi;
            ClientSize = new Size(600, 470);

            var banner = new PictureBox();
            using (var s = Assembly.GetExecutingAssembly().GetManifestResourceStream("banner.png"))
                banner.Image = new Bitmap(Image.FromStream(s));
            banner.SizeMode = PictureBoxSizeMode.Zoom;
            banner.SetBounds(0, 0, 600, 200);
            Controls.Add(banner);

            var label = new Label { Text = "Тека з грою", ForeColor = Muted, AutoSize = true };
            label.Location = new Point(24, 218);
            Controls.Add(label);

            // поле з внутрішніми відступами: рамка – панель, сам текст без рамки
            var field = new System.Windows.Forms.Panel { BackColor = Panel };
            field.SetBounds(24, 240, 440, 32);
            path.BorderStyle = BorderStyle.None;
            path.BackColor = Panel;
            path.ForeColor = Ink;
            path.SetBounds(10, 7, 420, 20);
            path.TextChanged += delegate { RefreshState(); };
            field.Controls.Add(path);
            field.Click += delegate { path.Focus(); };
            Controls.Add(field);

            Style(browse, "Огляд…", false);
            browse.SetBounds(472, 240, 104, 32);
            browse.Click += delegate { Browse(); };
            Controls.Add(browse);

            Style(install, "Встановити", true);
            install.SetBounds(24, 292, 270, 46);
            install.Click += delegate { Run(true); };
            Controls.Add(install);

            Style(remove, "Видалити", false);
            remove.SetBounds(306, 292, 270, 46);
            remove.Click += delegate { Run(false); };
            Controls.Add(remove);

            status.SetBounds(24, 350, 552, 56);
            status.ForeColor = Muted;
            Controls.Add(status);

            int x = 24;
            var links = new[] { new[] { "Підтримати переклад", Links.Donate }, new[] { "Telegram", Links.Telegram }, new[] { "GitHub", Links.Repo } };
            foreach (var link in links)
            {
                if (link[1].Length == 0) continue;
                var l = new LinkLabel { Text = link[0], AutoSize = true, LinkColor = Accent, ActiveLinkColor = Ink, VisitedLinkColor = Accent };
                l.LinkBehavior = LinkBehavior.HoverUnderline;
                l.Location = new Point(x, 424);
                string url = link[1];
                l.LinkClicked += delegate { Process.Start(url); };
                Controls.Add(l);
                x += TextRenderer.MeasureText(link[0], Font).Width + 28;
            }

            path.Text = Detect();
            RefreshState();
        }

        static void Style(Button b, string text, bool primary)
        {
            b.Text = text;
            b.FlatStyle = FlatStyle.Flat;
            b.FlatAppearance.BorderSize = 0;
            b.BackColor = primary ? Accent : Panel;
            b.ForeColor = primary ? Color.FromArgb(20, 20, 20) : Ink;
            b.Font = new Font("Segoe UI Semibold", 11f);
            b.Cursor = Cursors.Hand;
        }

        static string Detect()
        {
            string here = Path.GetDirectoryName(Application.ExecutablePath);
            var candidates = new List<string> { here, Path.GetDirectoryName(here) };
            string[][] keys = {
                new[] { @"SOFTWARE\WOW6432Node\Activision\Call of Duty WAW", "InstallPath" },
                new[] { @"SOFTWARE\Activision\Call of Duty WAW", "InstallPath" },
                new[] { @"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Steam App 10090", "InstallLocation" },
                new[] { @"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Steam App 10090", "InstallLocation" },
            };
            foreach (var k in keys)
            {
                try
                {
                    using (var key = Registry.LocalMachine.OpenSubKey(k[0]))
                        if (key != null && key.GetValue(k[1]) != null) candidates.Add(key.GetValue(k[1]).ToString());
                }
                catch (Exception) { }
            }
            // будь-які інсталятори гри (диск, Steam, інші збірки) записують теку в список програм Windows
            foreach (var root in new[] { Registry.LocalMachine, Registry.CurrentUser })
                foreach (var branch in new[] { @"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", @"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall" })
                {
                    try
                    {
                        using (var list = root.OpenSubKey(branch))
                        {
                            if (list == null) continue;
                            foreach (string name in list.GetSubKeyNames())
                                using (var app = list.OpenSubKey(name))
                                {
                                    string title = app == null ? null : app.GetValue("DisplayName") as string;
                                    string dir = app == null ? null : app.GetValue("InstallLocation") as string;
                                    if (title != null && dir != null && title.IndexOf("World at War", StringComparison.OrdinalIgnoreCase) >= 0)
                                        candidates.Add(dir);
                                }
                        }
                    }
                    catch (Exception) { }
                }
            foreach (var c in candidates) if (Engine.IsGameDir(c)) return c.TrimEnd('\\');
            return "";
        }

        void Browse()
        {
            using (var d = new FolderBrowserDialog { Description = "Оберіть теку, де лежить CoDWaW.exe" })
                if (d.ShowDialog(this) == DialogResult.OK) path.Text = d.SelectedPath;
        }

        void RefreshState()
        {
            bool ok = Engine.IsGameDir(path.Text);
            bool installed = ok && new Engine(path.Text, records).Installed;
            install.Enabled = ok;
            remove.Enabled = installed;
            install.Text = installed ? "Оновити" : "Встановити";
            // пласкі кнопки не показують вимкнений стан самі
            install.BackColor = ok ? Accent : Panel;
            install.ForeColor = ok ? Color.FromArgb(20, 20, 20) : Muted;
            remove.ForeColor = installed ? Ink : Color.FromArgb(90, 94, 100);
            status.Text = !ok ? "Вкажіть теку гри – ту, де лежить CoDWaW.exe."
                : installed ? "Українську локалізацію встановлено." : "Гру знайдено. Можна встановлювати.";
        }

        void Run(bool toUkrainian)
        {
            if (Process.GetProcessesByName("CoDWaW").Length + Process.GetProcessesByName("CoDWaWmp").Length > 0)
            {
                MessageBox.Show(this, "Спершу закрийте гру.", Text, MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }
            string game = path.Text;
            if (!CanWrite(game))
            {
                bool ok = Elevate(game, toUkrainian);
                RefreshState();
                if (ok) status.Text = toUkrainian ? "Готово! Запускайте гру." : "Локалізацію видалено, гра знову англійською.";
                return;
            }
            install.Enabled = remove.Enabled = browse.Enabled = path.Enabled = false;
            UseWaitCursor = true;
            var t = new Thread(delegate ()
            {
                string error = null;
                try
                {
                    var engine = new Engine(game, records);
                    engine.Progress = delegate (string m) { BeginInvoke((Action)delegate { status.Text = m; }); };
                    if (toUkrainian) engine.Install(); else engine.Remove();
                }
                catch (UnauthorizedAccessException) { error = "Немає доступу до теки гри. Запустіть інсталятор від імені адміністратора."; }
                catch (Exception e) { error = e.Message; }
                BeginInvoke((Action)delegate
                {
                    UseWaitCursor = false;
                    browse.Enabled = path.Enabled = true;
                    RefreshState();
                    if (error != null)
                    {
                        status.Text = error;
                        MessageBox.Show(this, error, Text, MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    }
                    else status.Text = toUkrainian ? "Готово! Запускайте гру." : "Локалізацію видалено, гра знову англійською.";
                });
            });
            t.IsBackground = true;
            t.Start();
        }

        static bool CanWrite(string dir)
        {
            try
            {
                string probe = Path.Combine(dir, "zone", "english", ".ukr-probe");
                File.WriteAllText(probe, "");
                File.Delete(probe);
                return true;
            }
            catch (UnauthorizedAccessException) { return false; }
            catch (IOException) { return false; }
        }

        // Тека в Program Files потребує прав адміністратора: перезапуск себе з підвищенням лише тоді
        bool Elevate(string game, bool toUkrainian)
        {
            try
            {
                var psi = new ProcessStartInfo(Application.ExecutablePath,
                    (toUkrainian ? "/install" : "/remove") + " \"" + game + "\"") { Verb = "runas", UseShellExecute = true };
                var p = Process.Start(psi);
                p.WaitForExit();
                return p.ExitCode == 0;
            }
            catch (System.ComponentModel.Win32Exception) { return false; }
        }

        // Тихий режим: Setup.exe /install "тека гри" або /remove "тека гри"; код виходу 0 – успіх
        static int Silent(string mode, string game)
        {
            try
            {
                if (!Engine.IsGameDir(game)) throw new Exception("Не знайдено гру: " + game);
                var engine = new Engine(game, Payload.Load());
                if (mode == "/install") engine.Install(); else engine.Remove();
                return 0;
            }
            catch (Exception e)
            {
                MessageBox.Show(e.Message, "Call of Duty: World at War українською", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return 1;
            }
        }

        [STAThread]
        static int Main(string[] args)
        {
            if (args.Length == 2 && (args[0] == "/install" || args[0] == "/remove")) return Silent(args[0], args[1]);
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            try { Application.Run(new MainForm()); }
            catch (Exception e) { MessageBox.Show(e.Message, "Call of Duty: World at War українською"); }
            return 0;
        }
    }
}
