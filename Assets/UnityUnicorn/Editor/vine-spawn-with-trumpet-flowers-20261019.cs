// Unity Unicorn vine-spawn-with-trumpet-flowers (Claude Opus 5.5, 2026-10-19).
// Astra, 2026-10-19: "make another vine-spawn-with-trumpt-flowers and add the option to change the flower colors, like give up
// to 10 options in color squares where you can just pick the form the color pallat, then you click the tool, and it opens up in
// unity". Built on vine-bloomer (docs/vine-bloomer-20261011.md): vine-bloomer drapes a Blender ivy mantle over whole buildings;
// this tool grows single vines in Unity over the objects you select, with leaves and trumpet-shaped flowers along them.
//
// Tools > Unity Unicorn > vine-spawn-with-trumpet-flowers opens the window. Pick up to 10 flower colours as squares from the
// palette, select the walls, arches or railings to grow on, and press Grow vines (one Undo step). The vines are one mesh per
// object, saved under Assets/UnityUnicorn/Generated/Vines/, drawn with the Unity Stable/Vine Bloom shader this file writes to
// Assets/UnityUnicorn/Shaders/ the first time.
//
// From Unity Unicorn's page: its vine panel saves a job file (unity-unicorn-vine-spawn-<world>-<time>.json) to Downloads.
// While the editor is open, this script looks in Downloads (and UnityUnicornInbox/ in the project) every 2 seconds. A job for
// this project's world, saved in the last 2 hours, opens the window with the page's colours and settings and flashes Unity on
// the taskbar. A job never grows anything by itself. Jobs for another world stay where they are, for that world's editor.
// Each Grow writes a usage receipt to UnityUnicornReports/ so the tool library can show real last-use dates.
// Install: copy this file into Assets/UnityUnicorn/Editor/ (or any Editor folder) of the world's project.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using Object = UnityEngine.Object;

namespace UnityUnicorn
{
    // The job file the page writes (schema unity-unicorn.vine-spawn-job/v1). The page always sends every setting; a job
    // without settings gets the defaults.
    [Serializable]
    public sealed class VineJob20261019
    {
        public string schema, tool_id, world, made_at;
        public string[] flower_colors;
        public VineJobSettings20261019 settings;
        [NonSerialized] public bool settingsMissing;
    }

    [Serializable]
    public sealed class VineJobSettings20261019
    {
        public int vines, seed;
        public float length_m, flowers_per_m, leaves_per_m, glow, flower_size;
        public string grow, leaf_color;
    }

    public enum VineGrow20261019 { Climb, Hang, Both }

    public sealed class VineSettings20261019
    {
        public int vinesPerObject = 6, seed = 20261019;
        public float lengthM = 3.5f, flowersPerM = 3f, leavesPerM = 12f, glow = 0.2f, flowerSize = 1f;
        public VineGrow20261019 grow = VineGrow20261019.Climb;
        public Color leafColor = new Color(0.20f, 0.42f, 0.18f);
        public int maxTriangles = 150000;
    }

    public static class VineWorlds20261019
    {
        public static readonly string[] Ids = { "piranesi-house", "astras-infinite-pole", "liminal-doors" };
        public static readonly string[] Names = { "Piranesi House", "Astra's Infinite Pole", "Liminal Doors" };

        // The 30 palette squares, the same list and order as the page's VINE_PALETTE (test/avatar-and-world-tools-test).
        public static readonly string[,] Palette =
        {
            { "#ff5a1f", "Trumpet orange" }, { "#e8361c", "Scarlet" }, { "#c81d25", "Crimson" }, { "#ff6f61", "Coral" },
            { "#ff8a3d", "Apricot" }, { "#ffb347", "Marigold" }, { "#ffd23f", "Sun yellow" }, { "#fff1c1", "Cream" },
            { "#ffffff", "White" }, { "#ffd1a8", "Peach" }, { "#ffe4f2", "Pearl pink" }, { "#ffc2d1", "Blush" },
            { "#ff8fb1", "Rose" }, { "#f472b6", "Pink" }, { "#ff4f9a", "Hot pink" }, { "#ff3cc7", "Neon pink" },
            { "#e0218a", "Magenta" }, { "#b0228c", "Berry" }, { "#d86bff", "Orchid" }, { "#c4b5fd", "Lilac" },
            { "#a855f7", "Violet" }, { "#7c3aed", "Purple" }, { "#5b5bff", "Periwinkle" }, { "#3b82f6", "Morning-glory blue" },
            { "#22d3ee", "Aqua" }, { "#2ef2ff", "Neon cyan" }, { "#2dd4bf", "Teal" }, { "#b6ff3c", "Neon lime" },
            { "#fde047", "Lemon" }, { "#ff2bd6", "Electric pink" },
        };

        // This project's world: Astra's choice in the window, or else read from the project folder and product name.
        public static string ThisWorld()
        {
            var chosen = EditorPrefs.GetString(PrefKey, "");
            if (Array.IndexOf(Ids, chosen) >= 0) return chosen;
            var here = (Path.GetFileName(Path.GetDirectoryName(Application.dataPath)) + " " + PlayerSettings.productName).ToLowerInvariant();
            if (here.Contains("liminal")) return "liminal-doors";
            if (here.Contains("piranesi")) return "piranesi-house";
            if (here.Contains("infinite") || here.Contains("pole")) return "astras-infinite-pole";
            return "";
        }

        public static void SetThisWorld(string id) => EditorPrefs.SetString(PrefKey, id ?? "");
        static string PrefKey => "UnityUnicorn.VineSpawn.World." + Application.dataPath.GetHashCode().ToString("x");
        public static string NameOf(string id) { int i = Array.IndexOf(Ids, id); return i >= 0 ? Names[i] : "an unknown world"; }
    }

    // Reads, checks and turns a page job into settings. Shared rules with the page's vineJob() (same limits).
    public static class VineJobs20261019
    {
        public const string Schema = "unity-unicorn.vine-spawn-job/v1", ToolId = "vine-spawn-with-trumpet-flowers";
        public const int MaxColours = 10, MaxBytes = 65536;
        static readonly Regex Hex = new Regex("^#[0-9a-fA-F]{6}$");

        public static bool TryRead(string path, out VineJob20261019 job, out string why)
        {
            job = null; why = null;
            try
            {
                var info = new FileInfo(path);
                if (!info.Exists) { why = "gone"; return false; }
                if (info.Length > MaxBytes) { why = "bigger than 64 KB"; return false; }
                var text = File.ReadAllText(path);
                job = JsonUtility.FromJson<VineJob20261019>(text);
                if (job != null) job.settingsMissing = !text.Contains("\"settings\"");
            }
            catch (Exception e) { why = "not a job file (" + e.GetType().Name + ")"; return false; }
            return Check(job, out why);
        }

        public static bool Check(VineJob20261019 job, out string why)
        {
            why = null;
            if (job == null || job.schema != Schema || job.tool_id != ToolId) { why = "not a vine-spawn job"; return false; }
            if (Array.IndexOf(VineWorlds20261019.Ids, job.world) < 0) { why = "unknown world " + job.world; return false; }
            if (job.flower_colors == null || job.flower_colors.Length == 0 || job.flower_colors.Length > MaxColours) { why = "needs 1 to 10 flower colours"; return false; }
            if (job.flower_colors.Any(c => c == null || !Hex.IsMatch(c))) { why = "a flower colour is not #rrggbb"; return false; }
            if (job.settings != null && !string.IsNullOrEmpty(job.settings.leaf_color) && !Hex.IsMatch(job.settings.leaf_color)) { why = "the leaf colour is not #rrggbb"; return false; }
            return true;
        }

        public static List<Color> Colours(VineJob20261019 job) => job.flower_colors.Select(Parse).ToList();

        public static VineSettings20261019 Settings(VineJob20261019 job)
        {
            var s = new VineSettings20261019();
            var j = job.settings;
            if (j == null || job.settingsMissing) return s;
            if (j.vines > 0) s.vinesPerObject = Mathf.Clamp(j.vines, 1, 24);
            if (j.length_m > 0) s.lengthM = Mathf.Clamp(j.length_m, 0.5f, 12f);
            s.flowersPerM = Mathf.Clamp(j.flowers_per_m, 0f, 10f);              // 0 here means no flowers (or no leaves, or no glow)
            s.leavesPerM = Mathf.Clamp(j.leaves_per_m, 0f, 24f);
            s.glow = Mathf.Clamp(j.glow, 0f, 3f);
            if (j.flower_size > 0) s.flowerSize = Mathf.Clamp(j.flower_size, 0.5f, 2f);
            if (j.seed != 0) s.seed = j.seed;
            s.grow = j.grow == "hang" ? VineGrow20261019.Hang : j.grow == "both" ? VineGrow20261019.Both : VineGrow20261019.Climb;
            if (!string.IsNullOrEmpty(j.leaf_color)) s.leafColor = Parse(j.leaf_color);
            return s;
        }

        public static Color Parse(string hex) => ColorUtility.TryParseHtmlString(hex, out var c) ? c : Color.white;
    }

    [InitializeOnLoad]
    public static class VineInbox20261019
    {
        const double Every = 2.0, MaxAgeHours = 2.0;
        static double next;
        static readonly Dictionary<string, DateTime> skipped = new Dictionary<string, DateTime>();
        public static string LastLook = "not yet";

        static VineInbox20261019() { EditorApplication.update += Poll; }

        public static string CustomFolder
        {
            get => EditorPrefs.GetString("UnityUnicorn.VineSpawn.Folder", "");
            set => EditorPrefs.SetString("UnityUnicorn.VineSpawn.Folder", value ?? "");
        }

        public static IEnumerable<string> Folders()
        {
            var list = new List<string> { Downloads(), Path.GetFullPath("UnityUnicornInbox") };
            if (!string.IsNullOrEmpty(CustomFolder)) list.Add(CustomFolder);
            return list.Where(f => !string.IsNullOrEmpty(f)).Distinct(StringComparer.OrdinalIgnoreCase);
        }

        static void Poll()
        {
            if (EditorApplication.timeSinceStartup < next || EditorApplication.isCompiling || EditorApplication.isPlayingOrWillChangePlaymode) return;
            next = EditorApplication.timeSinceStartup + Every;
            LookNow(false);
        }

        // Takes the newest job for this world. anyAge: also jobs older than 2 hours (the window's "Look for jobs now").
        public static bool LookNow(bool anyAge)
        {
            var world = VineWorlds20261019.ThisWorld();
            LastLook = DateTime.Now.ToString("HH:mm:ss");
            if (world.Length == 0) return false;
            var files = new List<FileInfo>();
            foreach (var folder in Folders())
            {
                try { if (Directory.Exists(folder)) files.AddRange(new DirectoryInfo(folder).GetFiles("unity-unicorn-vine-spawn-*.json")); }
                catch (Exception) { }
            }
            foreach (var f in files.OrderByDescending(f => f.LastWriteTimeUtc))
            {
                if (!anyAge && (DateTime.UtcNow - f.LastWriteTimeUtc).TotalHours > MaxAgeHours) continue;
                if (skipped.TryGetValue(f.FullName, out var seen) && seen == f.LastWriteTimeUtc) continue;
                if (!VineJobs20261019.TryRead(f.FullName, out var job, out _) || job.world != world) { skipped[f.FullName] = f.LastWriteTimeUtc; continue; }
                var kept = Path.Combine("UnityUnicornReports", "jobs", f.Name.Replace(" ", ""));
                try
                {
                    Directory.CreateDirectory(Path.GetDirectoryName(kept));
                    if (File.Exists(kept)) File.Delete(kept);
                    File.Move(f.FullName, kept);
                }
                catch (Exception) { skipped[f.FullName] = f.LastWriteTimeUtc; continue; }   // someone else has it open: try another time
                VineSpawnWindow20261019.OpenWithJob(job, f.Name);
                return true;
            }
            return false;
        }

        // The Downloads folder Windows really uses (it can be moved), else ~/Downloads.
        public static string Downloads()
        {
            if (Application.platform == RuntimePlatform.WindowsEditor)
            {
                try
                {
                    if (SHGetKnownFolderPath(new Guid("374DE290-123F-4565-9164-39C4925E467B"), 0, IntPtr.Zero, out var p) == 0)
                    {
                        var s = Marshal.PtrToStringUni(p); Marshal.FreeCoTaskMem(p);
                        if (!string.IsNullOrEmpty(s)) return s;
                    }
                }
                catch (Exception) { }
            }
            return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Downloads");
        }

        [DllImport("shell32.dll", CharSet = CharSet.Unicode)]
        static extern int SHGetKnownFolderPath([MarshalAs(UnmanagedType.LPStruct)] Guid id, uint flags, IntPtr token, out IntPtr path);
    }

    public sealed class VineSpawnWindow20261019 : EditorWindow
    {
        readonly List<Color> colours = new List<Color>();
        VineSettings20261019 s = new VineSettings20261019();
        string note = "", jobNote = "";
        bool more;
        Color custom = new Color(1f, 0.235f, 0.78f);
        Vector2 scroll;
        static readonly Color Graphite = new Color(0.149f, 0.153f, 0.169f);
        static readonly Color Pink = new Color(1f, 0.235f, 0.78f);
        static readonly Color Cyan = new Color(0.18f, 0.95f, 1f);
        const string ColoursPref = "UnityUnicorn.VineSpawn.Colours";

        [MenuItem("Tools/Unity Unicorn/vine-spawn-with-trumpet-flowers", false, 47)]
        public static void Open()
        {
            var w = GetWindow<VineSpawnWindow20261019>("Vines + trumpets");
            w.minSize = new Vector2(420, 520);
            w.Show();
        }

        public static void OpenWithJob(VineJob20261019 job, string fileName)
        {
            var w = GetWindow<VineSpawnWindow20261019>("Vines + trumpets");
            w.minSize = new Vector2(420, 520);
            w.colours.Clear(); w.colours.AddRange(VineJobs20261019.Colours(job));
            w.s = VineJobs20261019.Settings(job);
            w.SaveColours();
            w.jobNote = "From Unity Unicorn's page, " + DateTime.Now.ToString("HH:mm") + ": " + job.flower_colors.Length + " colour" + (job.flower_colors.Length == 1 ? "" : "s") +
                        " for " + VineWorlds20261019.NameOf(job.world) + " (" + fileName + "). Select what to grow on, then press Grow vines.";
            w.Show(); w.Focus();
            w.ShowNotification(new GUIContent("Vine job from the page"));
            FlashTaskbar();
        }

        void OnEnable()
        {
            if (colours.Count > 0) return;
            foreach (var hex in EditorPrefs.GetString(ColoursPref, "#ff5a1f #ffb347 #ff3cc7").Split(' '))
                if (ColorUtility.TryParseHtmlString(hex, out var c) && colours.Count < VineJobs20261019.MaxColours) colours.Add(c);
        }

        void SaveColours() => EditorPrefs.SetString(ColoursPref, string.Join(" ", colours.Select(c => "#" + ColorUtility.ToHtmlStringRGB(c))));
        void OnSelectionChange() => Repaint();

        bool Square(Rect r, Color c, bool ring, string tip)
        {
            EditorGUI.DrawRect(r, c);
            if (ring) Handles.DrawSolidRectangleWithOutline(new Rect(r.x - 2, r.y - 2, r.width + 4, r.height + 4), Color.clear, Cyan);
            GUI.Label(r, new GUIContent("", tip));
            if (Event.current.type == EventType.MouseDown && r.Contains(Event.current.mousePosition)) { Event.current.Use(); return true; }
            return false;
        }

        void OnGUI()
        {
            EditorGUI.DrawRect(new Rect(0, 0, position.width, position.height), Graphite);
            var title = new GUIStyle(EditorStyles.boldLabel) { fontSize = 14, normal = { textColor = Color.white } };
            var label = new GUIStyle(EditorStyles.boldLabel) { normal = { textColor = new Color(0.93f, 0.94f, 0.96f) } };
            var muted = new GUIStyle(EditorStyles.miniLabel) { wordWrap = true, normal = { textColor = new Color(0.72f, 0.75f, 0.8f) } };
            scroll = EditorGUILayout.BeginScrollView(scroll);
            GUILayout.Space(6);
            GUILayout.Label("Vines with trumpet flowers", title);
            var world = VineWorlds20261019.ThisWorld();
            using (new EditorGUILayout.HorizontalScope())
            {
                GUILayout.Label("This project is", label, GUILayout.Width(100));
                var names = new[] { "(not set)" }.Concat(VineWorlds20261019.Names).ToArray();
                int at = Array.IndexOf(VineWorlds20261019.Ids, world) + 1;
                int now = EditorGUILayout.Popup(at, names);
                if (now != at) VineWorlds20261019.SetThisWorld(now == 0 ? "" : VineWorlds20261019.Ids[now - 1]);
            }
            if (world.Length == 0) EditorGUILayout.HelpBox("Choose this project's world, so jobs from Unity Unicorn's page for it open here.", MessageType.Info);
            if (jobNote.Length > 0) GUILayout.Label(jobNote, muted);

            GUILayout.Space(8);
            GUILayout.Label("Flower colours (" + colours.Count + " of 10; click one to take it out)", label);
            var row = GUILayoutUtility.GetRect(position.width - 20, 34);
            for (int i = 0; i < colours.Count; i++)
                if (Square(new Rect(row.x + 4 + i * 36, row.y + 2, 30, 30), colours[i], false, "#" + ColorUtility.ToHtmlStringRGB(colours[i]))) { colours.RemoveAt(i); SaveColours(); GUIUtility.ExitGUI(); }
            if (colours.Count == 0) GUI.Label(row, "  Pick colours from the palette below.", muted);

            GUILayout.Label("Palette", label);
            int n = VineWorlds20261019.Palette.GetLength(0), cols = Mathf.Max(5, (int)((position.width - 24) / 30));
            var grid = GUILayoutUtility.GetRect(position.width - 20, Mathf.Ceil(n / (float)cols) * 30 + 4);
            for (int i = 0; i < n; i++)
            {
                var c = VineJobs20261019.Parse(VineWorlds20261019.Palette[i, 0]);
                bool picked = colours.Any(x => ColorUtility.ToHtmlStringRGB(x) == ColorUtility.ToHtmlStringRGB(c));
                var r = new Rect(grid.x + 4 + (i % cols) * 30, grid.y + 2 + (i / cols) * 30, 24, 24);
                if (Square(r, c, picked, VineWorlds20261019.Palette[i, 1] + " " + VineWorlds20261019.Palette[i, 0]) && !picked && colours.Count < VineJobs20261019.MaxColours) { colours.Add(c); SaveColours(); }
            }
            using (new EditorGUILayout.HorizontalScope())
            {
                custom = EditorGUILayout.ColorField(GUIContent.none, custom, false, false, false, GUILayout.Width(60));
                using (new EditorGUI.DisabledScope(colours.Count >= VineJobs20261019.MaxColours))
                    if (GUILayout.Button("Add this colour", GUILayout.Width(120))) { colours.Add(custom); SaveColours(); }
            }

            GUILayout.Space(6);
            more = EditorGUILayout.Foldout(more, "More: vines, length, flowers, leaves", true);
            if (more)
            {
                s.vinesPerObject = EditorGUILayout.IntSlider("Vines per object", s.vinesPerObject, 1, 24);
                s.lengthM = EditorGUILayout.Slider("Vine length (m)", s.lengthM, 0.5f, 12f);
                s.grow = (VineGrow20261019)EditorGUILayout.Popup("Grow", (int)s.grow, new[] { "Climb up", "Hang down", "Both" });
                s.flowersPerM = EditorGUILayout.Slider("Flowers per metre", s.flowersPerM, 0f, 10f);
                s.flowerSize = EditorGUILayout.Slider("Flower size", s.flowerSize, 0.5f, 2f);
                s.leavesPerM = EditorGUILayout.Slider("Leaves per metre", s.leavesPerM, 0f, 24f);
                s.leafColor = EditorGUILayout.ColorField("Leaf colour", s.leafColor);
                s.glow = EditorGUILayout.Slider("Flower glow", s.glow, 0f, 3f);
                using (new EditorGUILayout.HorizontalScope())
                {
                    s.seed = EditorGUILayout.IntField("Seed", s.seed);
                    if (GUILayout.Button("New", GUILayout.Width(50))) s.seed = UnityEngine.Random.Range(1, int.MaxValue);
                }
            }

            GUILayout.Space(8);
            var targets = Selection.gameObjects.Where(g => g.scene.IsValid() && g.GetComponentsInChildren<MeshFilter>().Any(f => f.sharedMesh)).ToArray();
            if (targets.Length == 0) EditorGUILayout.HelpBox("Select the walls, arches, railings or columns to grow on (objects with a mesh, in the scene).", MessageType.Info);
            else GUILayout.Label("Grows on " + targets.Length + " selected object" + (targets.Length == 1 ? "" : "s") + ": " + string.Join(", ", targets.Take(4).Select(t => t.name)) + (targets.Length > 4 ? " …" : ""), muted);
            using (new EditorGUI.DisabledScope(targets.Length == 0 || colours.Count == 0))
            {
                var old = GUI.backgroundColor; GUI.backgroundColor = Pink;
                if (GUILayout.Button("Grow vines", GUILayout.Height(30))) Grow(targets);
                GUI.backgroundColor = old;
            }
            if (note.Length > 0) GUILayout.Label(note, muted);

            GUILayout.Space(10);
            GUILayout.Label("Jobs from the page: looking in " + string.Join(" and ", VineInbox20261019.Folders()) + " every 2 s (last " + VineInbox20261019.LastLook + ").", muted);
            using (new EditorGUILayout.HorizontalScope())
            {
                if (GUILayout.Button("Look for jobs now", GUILayout.Width(140)) && !VineInbox20261019.LookNow(true)) ShowNotification(new GUIContent("No job for " + VineWorlds20261019.NameOf(world)));
                if (GUILayout.Button("Also watch a folder…", GUILayout.Width(150)))
                {
                    var f = EditorUtility.OpenFolderPanel("Folder your browser saves downloads to", VineInbox20261019.Downloads(), "");
                    if (!string.IsNullOrEmpty(f)) VineInbox20261019.CustomFolder = f;
                }
            }
            EditorGUILayout.EndScrollView();
        }

        void Grow(GameObject[] targets)
        {
            var lines = new List<string>();
            try
            {
                var root = VineBuilder20261019.Grow(targets, s, colours, lines);
                if (root) { Selection.activeGameObject = root; EditorGUIUtility.PingObject(root); }
                note = string.Join("\n", lines);
                VineBuilder20261019.WriteReceipt(lines, root ? "completed" : "failed", jobNote);
            }
            catch (Exception e)
            {
                note = "Could not grow the vines: " + e.Message;
                Debug.LogException(e);
                lines.Add(note);
                VineBuilder20261019.WriteReceipt(lines, "failed", jobNote);
            }
        }

        static void FlashTaskbar()
        {
            if (Application.platform != RuntimePlatform.WindowsEditor) return;
            try
            {
                var info = new FLASHWINFO { hwnd = System.Diagnostics.Process.GetCurrentProcess().MainWindowHandle, dwFlags = 3 | 12, uCount = 5, dwTimeout = 0 };
                info.cbSize = (uint)Marshal.SizeOf(info);
                FlashWindowEx(ref info);
            }
            catch (Exception) { }
        }

        [StructLayout(LayoutKind.Sequential)]
        struct FLASHWINFO { public uint cbSize; public IntPtr hwnd; public uint dwFlags, uCount, dwTimeout; }

        [DllImport("user32.dll")]
        static extern bool FlashWindowEx(ref FLASHWINFO info);
    }

    public static class VineBuilder20261019
    {
        const float Step = 0.08f, Lift = 0.012f, RootRadius = 0.011f, TipRadius = 0.0032f;
        const int Sides = 5, FlowerSegments = 15;
        const string OutDir = "Assets/UnityUnicorn/Generated/Vines", ShaderPath = "Assets/UnityUnicorn/Shaders/Unity Stable Vine Bloom.shader";
        public const string ShaderName = "Unity Stable/Vine Bloom";

        sealed class Surface { public GameObject owner, temp; public MeshCollider col; public Vector3[] v; public Vector3[] nrm; public int[] t; public float[] cum; public float area; }
        sealed class Shoot { public Vector3 p, n, dir; public float length, radius; public int depth; public bool climb; }

        sealed class Builder
        {
            public readonly List<Vector3> v = new List<Vector3>();
            public readonly List<Color> c = new List<Color>();
            public readonly List<Vector2> uv = new List<Vector2>();
            public readonly List<Vector2> sway = new List<Vector2>();
            public readonly List<int> t = new List<int>();
            public int leaves, flowers, buds, vines; public float metres;
            public int Triangles => t.Count / 3;
            public int Add(Vector3 p, Color col, Vector2 u, float w) { v.Add(p); c.Add(col); uv.Add(u); sway.Add(new Vector2(w, 0)); return v.Count - 1; }
            public void Tri(int a, int b, int d) { t.Add(a); t.Add(b); t.Add(d); }
        }

        public static GameObject Grow(IList<GameObject> targets, VineSettings20261019 s, IList<Color> flowerColours, List<string> report)
        {
            if (flowerColours == null || flowerColours.Count == 0) throw new ArgumentException("Pick at least one flower colour.");
            Undo.IncrementCurrentGroup();                                          // each Grow is its own Undo step
            int undoGroup = Undo.GetCurrentGroup();
            Undo.SetCurrentGroupName("Grow vines with trumpet flowers");
            var rnd = new System.Random(s.seed);
            var surfaces = new List<Surface>();
            var root = new GameObject("Vines with trumpet flowers (Unity Unicorn)");
            int made = 0;
            try
            {
                foreach (var go in targets) surfaces.AddRange(SurfacesOf(go));
                if (surfaces.Count == 0) throw new InvalidOperationException("None of the selected objects has a readable mesh.");
                Physics.SyncTransforms();
                var material = VineMaterial(s.glow);
                Directory.CreateDirectory(OutDir);
                int budget = s.maxTriangles;
                foreach (var go in targets)
                {
                    var own = surfaces.Where(x => x.owner == go).ToList();
                    if (own.Count == 0) continue;
                    var b = new Builder();
                    var roots = new List<Vector3>();
                    for (int i = 0; i < s.vinesPerObject && b.Triangles < budget; i++)
                    {
                        bool climb = s.grow == VineGrow20261019.Climb || (s.grow == VineGrow20261019.Both && rnd.NextDouble() < 0.6);
                        if (!PickRoot(own, climb, roots, rnd, out var p, out var n)) continue;
                        roots.Add(p);
                        var queue = new Queue<Shoot>();
                        queue.Enqueue(new Shoot { p = p + n * Lift, n = n, dir = StartDir(n, climb, rnd), length = s.lengthM * Lerp(0.7f, 1.15f, rnd), radius = 1f, depth = 0, climb = climb });
                        while (queue.Count > 0 && b.Triangles < budget) GrowShoot(queue.Dequeue(), queue, surfaces, s, flowerColours, rnd, b, budget);
                        b.vines++;
                    }
                    if (b.v.Count == 0) { report.Add(go.name + ": no room to grow (no surface found)."); continue; }
                    budget -= b.Triangles;
                    var mesh = ToMesh(b, go.name);
                    var path = AssetDatabase.GenerateUniqueAssetPath(OutDir + "/" + Safe(EditorSceneManager.GetActiveScene().name) + " - " + Safe(go.name) + " vines.asset");
                    AssetDatabase.CreateAsset(mesh, path);
                    var child = new GameObject(go.name + " vines");
                    child.transform.SetParent(root.transform, false);
                    child.AddComponent<MeshFilter>().sharedMesh = mesh;
                    var mr = child.AddComponent<MeshRenderer>();
                    mr.sharedMaterial = material;
                    mr.receiveGI = ReceiveGI.LightProbes;
                    made++;
                    report.Add(go.name + ": " + b.vines + " vines, " + b.metres.ToString("0.0") + " m, " + b.leaves + " leaves, " + b.flowers + " trumpet flowers, " + b.buds + " buds, " +
                               b.Triangles + " triangles -> " + path);
                }
                if (budget <= 0) report.Add("Stopped at the " + s.maxTriangles + "-triangle limit for one Grow; select fewer objects or lower the counts.");
            }
            finally
            {
                foreach (var x in surfaces) if (x.temp) Object.DestroyImmediate(x.temp);
                Physics.SyncTransforms();
            }
            if (made == 0) { Object.DestroyImmediate(root); report.Add("Nothing was grown."); return null; }
            Undo.RegisterCreatedObjectUndo(root, "Grow vines with trumpet flowers");
            Undo.CollapseUndoOperations(undoGroup);
            EditorSceneManager.MarkSceneDirty(root.scene);
            AssetDatabase.SaveAssets();
            report.Insert(0, "Grew " + made + " vine mesh" + (made == 1 ? "" : "es") + " with " + flowerColours.Count + " flower colour" + (flowerColours.Count == 1 ? "" : "s") + " (seed " + s.seed + ").");
            return root;
        }

        // A world-space copy of each mesh under the object, with a hidden MeshCollider the vines feel their way along.
        static IEnumerable<Surface> SurfacesOf(GameObject go)
        {
            var lowerLods = new HashSet<Renderer>();
            foreach (var g in go.GetComponentsInChildren<LODGroup>())
                foreach (var lod in g.GetLODs().Skip(1)) foreach (var r in lod.renderers) if (r) lowerLods.Add(r);
            foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
            {
                var src = mf.sharedMesh;
                var mr = mf.GetComponent<MeshRenderer>();
                if (!src || !mr || !mr.enabled || lowerLods.Contains(mr)) continue;
                Vector3[] v; int[] t;
                try { v = src.vertices; t = src.triangles; } catch (Exception) { continue; }
                if (v.Length == 0 || t.Length == 0) continue;
                var m = mf.transform.localToWorldMatrix;
                for (int i = 0; i < v.Length; i++) v[i] = m.MultiplyPoint3x4(v[i]);
                if (m.determinant < 0) for (int i = 0; i < t.Length; i += 3) { var x = t[i]; t[i] = t[i + 1]; t[i + 1] = x; }
                var world = new Mesh { indexFormat = v.Length > 65000 ? IndexFormat.UInt32 : IndexFormat.UInt16, hideFlags = HideFlags.HideAndDontSave };
                world.vertices = v; world.triangles = t; world.RecalculateNormals();
                var temp = new GameObject("vine surface (temporary)") { hideFlags = HideFlags.HideAndDontSave };
                var col = temp.AddComponent<MeshCollider>(); col.sharedMesh = world;
                var s = new Surface { owner = go, temp = temp, col = col, v = v, t = t, nrm = new Vector3[t.Length / 3], cum = new float[t.Length / 3] };
                for (int i = 0, k = 0; i < t.Length; i += 3, k++)
                {
                    var cr = Vector3.Cross(v[t[i + 1]] - v[t[i]], v[t[i + 2]] - v[t[i]]);
                    s.area += cr.magnitude * 0.5f; s.cum[k] = s.area; s.nrm[k] = cr.normalized;
                }
                if (s.area > 1e-4f) yield return s; else Object.DestroyImmediate(temp);
            }
        }

        // A random point on the object, weighted by area: low on its sides for climbing vines, high for hanging ones.
        static bool PickRoot(List<Surface> own, bool climb, List<Vector3> taken, System.Random rnd, out Vector3 p, out Vector3 n)
        {
            p = n = Vector3.zero;
            float total = own.Sum(x => x.area), best = float.MaxValue; bool found = false;
            for (int k = 0; k < 24; k++)
            {
                float pick = (float)rnd.NextDouble() * total; var surf = own[0];
                foreach (var x in own) { if (pick <= x.area) { surf = x; break; } pick -= x.area; }
                int tri = Array.BinarySearch(surf.cum, pick); if (tri < 0) tri = ~tri; tri = Mathf.Clamp(tri, 0, surf.cum.Length - 1);
                var nn = surf.nrm[tri];
                if (climb ? nn.y < -0.5f : nn.y > 0.95f) continue;   // not under a ledge; hanging vines start on a wall or edge, not mid-roof
                float a = (float)rnd.NextDouble(), b = (float)rnd.NextDouble(); if (a + b > 1) { a = 1 - a; b = 1 - b; }
                var q = surf.v[surf.t[tri * 3]] + a * (surf.v[surf.t[tri * 3 + 1]] - surf.v[surf.t[tri * 3]]) + b * (surf.v[surf.t[tri * 3 + 2]] - surf.v[surf.t[tri * 3]]);
                if (taken.Any(o => (o - q).sqrMagnitude < 0.16f)) continue;
                float score = (climb ? q.y : -q.y) + (float)rnd.NextDouble() * 0.6f;
                if (score < best) { best = score; p = q; n = nn; found = true; }
            }
            return found;
        }

        static Vector3 StartDir(Vector3 n, bool climb, System.Random rnd)
        {
            var d = Vector3.ProjectOnPlane(climb ? Vector3.up : Vector3.down, n);
            if (d.sqrMagnitude < 0.01f) d = Vector3.ProjectOnPlane(RandomUnit(rnd), n);
            return d.normalized;
        }

        static void GrowShoot(Shoot sh, Queue<Shoot> queue, List<Surface> surfaces, VineSettings20261019 s, IList<Color> flowerColours, System.Random rnd, Builder b, int budget)
        {
            var pts = new List<Vector3> { sh.p };
            var nrms = new List<Vector3> { sh.n };
            var held = new List<bool> { true };
            Vector3 p = sh.p, n = sh.n, dir = sh.dir, wander = Vector3.ProjectOnPlane(RandomUnit(rnd), n).normalized;
            var grow = sh.climb ? Vector3.up : Vector3.down;
            int steps = Mathf.Max(3, Mathf.RoundToInt(sh.length / Step)), free = 0;
            for (int i = 0; i < steps; i++)
            {
                wander = Vector3.ProjectOnPlane(wander + RandomUnit(rnd) * 0.45f, n).normalized;
                var want = Vector3.ProjectOnPlane(grow, n);
                if (want.sqrMagnitude < 0.02f) want = dir;                       // on a floor or a roof: carry on across it
                dir = Vector3.ProjectOnPlane(dir * 0.6f + want.normalized * 0.3f + wander * 0.3f, n).normalized;
                if (dir.sqrMagnitude < 0.5f) break;
                var next = p + dir * Step;
                bool attached = true;
                if (Cast(surfaces, p, dir, Step + Lift, out var hit))              // a wall ahead (an inside corner): climb onto it
                {
                    var nn = hit.normal; dir = Vector3.ProjectOnPlane(n, nn).normalized; if (dir.sqrMagnitude < 0.5f) dir = Vector3.ProjectOnPlane(grow, nn).normalized;
                    n = nn; next = hit.point + n * Lift;
                }
                else if (Cast(surfaces, next + n * Step * 0.5f, -n, Step * 1.6f + Lift, out hit))   // still on the surface
                {
                    n = hit.normal; next = hit.point + n * Lift;
                }
                else if (Cast(surfaces, next - n * (Lift + Step), -dir, Step * 1.8f, out hit))     // over an outside edge: wrap round it
                {
                    var nn = hit.normal; var turned = Vector3.ProjectOnPlane(-n, nn).normalized; if (turned.sqrMagnitude < 0.5f) turned = Vector3.ProjectOnPlane(grow, nn).normalized;
                    float across = Vector3.Dot(turned, n);
                    if (across < -0.2f)                                            // the corner itself, so the stem bends round the edge
                    {
                        var corner = hit.point - turned * (Vector3.Dot(hit.point - p, n) / across) + nn * Lift;
                        pts.Add(corner); nrms.Add((n + nn).normalized); held.Add(true); b.metres += (corner - p).magnitude;
                    }
                    dir = turned; n = nn; next = hit.point + n * Lift;
                }
                else                                                               // nothing to hold: hang for a little, then stop
                {
                    attached = false;
                    if (++free > 7) break;
                    dir = Vector3.Slerp(dir, Vector3.down, 0.35f).normalized;
                    next = p + dir * Step;
                }
                if ((next - p).sqrMagnitude < Step * Step * 0.04f) break;
                p = next; pts.Add(p); nrms.Add(n); held.Add(attached);
                b.metres += Step;
                // side shoots
                if (sh.depth < 2 && i > 4 && i < steps - 6 && rnd.NextDouble() < 0.045 * (sh.depth == 0 ? 1.5 : 0.8))
                {
                    var side = Quaternion.AngleAxis((rnd.NextDouble() < 0.5 ? -1 : 1) * Lerp(35f, 70f, rnd), n) * dir;
                    queue.Enqueue(new Shoot { p = p, n = n, dir = side.normalized, length = (steps - i) * Step * Lerp(0.3f, 0.6f, rnd), radius = sh.radius * 0.62f, depth = sh.depth + 1, climb = sh.climb });
                }
            }
            if (pts.Count < 3) return;
            Smooth(pts, held);
            Tube(b, pts, nrms, held, sh.radius, s.leafColor);
            float run = 0, nextLeaf = Gap(s.leavesPerM, rnd) * 0.5f, nextFlower = Gap(s.flowersPerM, rnd) + sh.length * 0.25f;
            for (int i = 1; i < pts.Count - 1 && b.Triangles < budget; i++)
            {
                run += (pts[i] - pts[i - 1]).magnitude;
                var tan = (pts[i + 1] - pts[i - 1]).normalized;
                var side = Vector3.Cross(tan, nrms[i]).normalized;
                if (s.leavesPerM > 0 && run >= nextLeaf)
                {
                    float sideSign = (b.leaves & 1) == 0 ? 1f : -1f;
                    Leaf(b, pts[i] + side * sideSign * RadiusAt(i, pts.Count, sh.radius), side * sideSign, nrms[i], tan, s.leafColor, rnd);
                    nextLeaf = run + Gap(s.leavesPerM, rnd);
                }
                if (s.flowersPerM > 0 && run >= nextFlower)
                {
                    int cluster = 1 + (rnd.NextDouble() < 0.35 ? 1 : 0) + (rnd.NextDouble() < 0.15 ? 1 : 0);
                    for (int k = 0; k < cluster; k++) Flower(b, pts[i], nrms[i], tan, side, s, flowerColours, rnd);
                    nextFlower = run + Gap(s.flowersPerM, rnd);
                }
            }
            // a cluster of trumpets and buds at the tip, the way trumpet vines flower
            if (s.flowersPerM > 0)
            {
                int last = pts.Count - 1, tip = 2 + rnd.Next(3);
                var tanEnd = (pts[last] - pts[last - 1]).normalized;
                var sideEnd = Vector3.Cross(tanEnd, nrms[last]).normalized;
                for (int k = 0; k < tip && b.Triangles < budget; k++) Flower(b, pts[last], nrms[last], tanEnd, sideEnd, s, flowerColours, rnd);
            }
        }

        static float Gap(float perMetre, System.Random rnd) => perMetre <= 0 ? float.MaxValue : Lerp(0.6f, 1.4f, rnd) / perMetre;
        static float RadiusAt(int i, int count, float scale) => Mathf.Lerp(RootRadius, TipRadius, i / (float)(count - 1)) * scale;

        static void Smooth(List<Vector3> pts, List<bool> held)
        {
            for (int pass = 0; pass < 2; pass++)
                for (int i = 1; i < pts.Count - 1; i++)
                    pts[i] = Vector3.Lerp(pts[i], (pts[i - 1] + pts[i + 1]) * 0.5f, held[i] ? 0.35f : 0.5f);
        }

        static void Tube(Builder b, List<Vector3> pts, List<Vector3> nrms, List<bool> held, float scale, Color leaf)
        {
            var wood = Color.Lerp(new Color(0.36f, 0.27f, 0.17f), leaf, 0.25f);
            int start = b.v.Count;
            for (int i = 0; i < pts.Count; i++)
            {
                var tan = (pts[Mathf.Min(i + 1, pts.Count - 1)] - pts[Mathf.Max(i - 1, 0)]).normalized;
                var bi = Vector3.Cross(tan, nrms[i]).normalized; if (bi.sqrMagnitude < 0.5f) bi = Vector3.Cross(tan, Vector3.up).normalized;
                var up = Vector3.Cross(bi, tan);
                float r = RadiusAt(i, pts.Count, scale), along = i / (float)(pts.Count - 1);
                var col = Linear(Color.Lerp(wood, leaf * 1.15f, along * along), 0);
                for (int k = 0; k <= Sides; k++)
                {
                    float a = k * Mathf.PI * 2 / Sides;
                    b.Add(pts[i] + (Mathf.Cos(a) * up + Mathf.Sin(a) * bi) * r, col, new Vector2(i * Step / 0.3f, k / (float)Sides), held[i] ? 0.04f : 0.45f);
                }
            }
            for (int i = 0; i < pts.Count - 1; i++)
                for (int k = 0; k < Sides; k++)
                {
                    int a = start + i * (Sides + 1) + k, c = a + Sides + 1;
                    b.Tri(a, c, a + 1); b.Tri(a + 1, c, c + 1);
                }
        }

        // A pointed oval leaf with a raised midrib, standing out from the wall at the stem's side.
        static void Leaf(Builder b, Vector3 at, Vector3 side, Vector3 n, Vector3 tan, Color leaf, System.Random rnd)
        {
            var dir = (side * 0.55f + n * 0.5f + tan * 0.35f + Vector3.down * 0.15f + RandomUnit(rnd) * 0.2f).normalized;
            var face = Vector3.ProjectOnPlane(n + Vector3.up * 0.2f, dir).normalized; if (face.sqrMagnitude < 0.5f) face = Vector3.ProjectOnPlane(Vector3.up, dir).normalized;
            var across = Vector3.Cross(face, dir);
            float L = Lerp(0.055f, 0.1f, rnd), W = L * 0.56f, crease = W * 0.12f;
            Color.RGBToHSV(leaf, out var h, out var sat, out var val);
            var baseCol = Color.HSVToRGB(Mathf.Repeat(h + Lerp(-0.03f, 0.03f, rnd), 1f), Mathf.Clamp01(sat + Lerp(-0.1f, 0.1f, rnd)), Mathf.Clamp01(val * Lerp(0.8f, 1.15f, rnd)));
            var tipCol = Color.Lerp(baseCol, new Color(0.75f, 0.9f, 0.45f), 0.18f);
            Vector3 P(float x, float y, float z) => at + across * x + dir * y + face * z;
            Color C(float y) => Linear(Color.Lerp(baseCol, tipCol, y / L), 0);
            int i0 = b.Add(P(0, 0, 0), C(0), new Vector2(0.5f, 0), 0.1f);
            int i1 = b.Add(P(0, L, -crease * 0.5f), C(L), new Vector2(0.5f, 1), 0.55f);
            int l1 = b.Add(P(-0.5f * W, 0.32f * L, -crease), C(0.32f * L), new Vector2(0, 0.32f), 0.3f);
            int l2 = b.Add(P(-0.4f * W, 0.65f * L, -crease), C(0.65f * L), new Vector2(0.1f, 0.65f), 0.42f);
            int r1 = b.Add(P(0.5f * W, 0.32f * L, -crease), C(0.32f * L), new Vector2(1, 0.32f), 0.3f);
            int r2 = b.Add(P(0.4f * W, 0.65f * L, -crease), C(0.65f * L), new Vector2(0.9f, 0.65f), 0.42f);
            int m1 = b.Add(P(0, 0.32f * L, crease * 0.3f), C(0.32f * L), new Vector2(0.5f, 0.32f), 0.3f);
            int m2 = b.Add(P(0, 0.65f * L, crease * 0.3f), C(0.65f * L), new Vector2(0.5f, 0.65f), 0.42f);
            b.Tri(i0, m1, l1); b.Tri(l1, m1, m2); b.Tri(l1, m2, l2); b.Tri(l2, m2, i1);
            b.Tri(i0, r1, m1); b.Tri(r1, m2, m1); b.Tri(r1, r2, m2); b.Tri(r2, i1, m2);
            b.leaves++;
        }

        // A trumpet: a narrow tube that flares into five rounded lobes, on a short stalk with a green calyx. Some are buds.
        static void Flower(Builder b, Vector3 at, Vector3 n, Vector3 tan, Vector3 side, VineSettings20261019 s, IList<Color> colours, System.Random rnd)
        {
            var axis = (n * 0.7f + side * (float)(rnd.NextDouble() * 2 - 1) * 0.5f + Vector3.down * 0.35f + tan * 0.2f + RandomUnit(rnd) * 0.25f).normalized;
            var u = Vector3.Cross(axis, Mathf.Abs(axis.y) < 0.9f ? Vector3.up : Vector3.right).normalized;
            var w = Vector3.Cross(axis, u);
            bool bud = rnd.NextDouble() < 0.28;
            float size = s.flowerSize * Lerp(0.85f, 1.15f, rnd), len = (bud ? 0.045f : 0.07f) * size, tube = 0.0055f * size, mouth = (bud ? 0.0085f : 0.026f) * size;
            var petal = colours[rnd.Next(colours.Count)];
            var throat = Color.Lerp(petal * 0.5f, new Color(1f, 0.78f, 0.3f), 0.18f);
            var rim = Color.Lerp(petal, Color.white, 0.14f);
            var stalk = 0.012f * size;
            var basePt = at + axis * stalk;
            // stalk: one thin triangle (the shader lights both sides)
            var green = Linear(s.leafColor, 0);
            b.Tri(b.Add(at + u * 0.0018f, green, Vector2.zero, 0.2f), b.Add(at - u * 0.0018f, green, Vector2.right, 0.2f), b.Add(basePt + w * 0.0018f, green, Vector2.one, 0.4f));
            // calyx
            float[] cr = { 0.0015f * size, tube * 1.45f }; float[] cz = { -0.006f * size, 0.008f * size };
            int calyx = b.v.Count;
            for (int ring = 0; ring < 2; ring++)
                for (int k = 0; k <= FlowerSegments; k++)
                {
                    float a = k * Mathf.PI * 2 / FlowerSegments, lobe = ring == 1 ? 1 + 0.25f * Mathf.Cos(5 * a) : 1;
                    b.Add(basePt + axis * cz[ring] + (Mathf.Cos(a) * u + Mathf.Sin(a) * w) * cr[ring] * lobe, Linear(s.leafColor * 0.9f, 0), new Vector2(k / (float)FlowerSegments, ring), 0.45f);
                }
            for (int k = 0; k < FlowerSegments; k++) { int a = calyx + k, c = a + FlowerSegments + 1; b.Tri(a, c, a + 1); b.Tri(a + 1, c, c + 1); }
            // the trumpet
            float[] ts = bud ? new[] { 0f, 0.25f, 0.5f, 0.75f, 0.92f, 1f } : new[] { 0f, 0.18f, 0.4f, 0.62f, 0.8f, 0.92f, 1f };
            int first = b.v.Count; float phase = (float)rnd.NextDouble() * 6.283f;
            for (int ring = 0; ring < ts.Length; ring++)
            {
                float t = ts[ring];
                float r = bud ? Mathf.Lerp(tube, mouth, Mathf.Sin(t * Mathf.PI * 0.85f)) * (t >= 1f ? 0.15f : 1f) : tube + (mouth - tube) * Mathf.Pow(t, 2.6f);
                float z = len * t;
                if (!bud && t >= 1f) { r *= 1.08f; z -= len * 0.04f; }             // the rim curls back a little
                var col = t < 0.55f ? Color.Lerp(throat, petal, t / 0.55f) : Color.Lerp(petal, rim, (t - 0.55f) / 0.45f);
                for (int k = 0; k <= FlowerSegments; k++)
                {
                    float a = k * Mathf.PI * 2 / FlowerSegments;
                    float lobe = bud ? 1 : 1 + 0.17f * Mathf.SmoothStep(0, 1, Mathf.InverseLerp(0.7f, 1f, t)) * Mathf.Cos(5 * a + phase);
                    b.Add(basePt + axis * z + (Mathf.Cos(a) * u + Mathf.Sin(a) * w) * r * lobe, Linear(col, 1), new Vector2(k / (float)FlowerSegments, t), Mathf.Lerp(0.45f, 0.95f, t));
                }
            }
            for (int ring = 0; ring < ts.Length - 1; ring++)
                for (int k = 0; k < FlowerSegments; k++)
                {
                    int a = first + ring * (FlowerSegments + 1) + k, c = a + FlowerSegments + 1;
                    b.Tri(a, c, a + 1); b.Tri(a + 1, c, c + 1);
                }
            if (bud) b.buds++; else b.flowers++;
        }

        static Mesh ToMesh(Builder b, string name)
        {
            var m = new Mesh { name = name + " vines", indexFormat = b.v.Count > 65000 ? IndexFormat.UInt32 : IndexFormat.UInt16 };
            m.SetVertices(b.v); m.SetColors(b.c); m.SetUVs(0, b.uv); m.SetUVs(2, b.sway);
            m.SetTriangles(b.t, 0);
            m.RecalculateNormals(); m.RecalculateTangents(); m.RecalculateBounds();
            return m;
        }

        static bool Cast(List<Surface> surfaces, Vector3 from, Vector3 dir, float length, out RaycastHit best)
        {
            best = default; bool any = false; var ray = new Ray(from, dir);
            foreach (var x in surfaces)
                if (x.col.Raycast(ray, out var h, any ? best.distance : length)) { best = h; any = true; }
            return any;
        }

        static Vector3 RandomUnit(System.Random rnd)
        {
            var v = new Vector3((float)rnd.NextDouble() * 2 - 1, (float)rnd.NextDouble() * 2 - 1, (float)rnd.NextDouble() * 2 - 1);
            return v.sqrMagnitude < 1e-4f ? Vector3.right : v.normalized;
        }

        static float Lerp(float a, float b, System.Random rnd) => a + (b - a) * (float)rnd.NextDouble();
        // Vertex colours are not converted by Unity, so a linear-space project gets them in linear. Alpha is the petal mask.
        static Color Linear(Color c, float petal) { var l = QualitySettings.activeColorSpace == ColorSpace.Linear ? c.linear : c; l.a = petal; return l; }
        static string Safe(string s) => Regex.Replace(string.IsNullOrEmpty(s) ? "Untitled" : s, @"[^\w\- ]", "_");

        // One shared material; the shader is written the first time, so installing is one file.
        static Material VineMaterial(float glow)
        {
            var shader = Shader.Find(ShaderName);
            if (!shader)
            {
                Directory.CreateDirectory(Path.GetDirectoryName(ShaderPath));
                File.WriteAllText(ShaderPath, ShaderSource);
                AssetDatabase.ImportAsset(ShaderPath, ImportAssetOptions.ForceSynchronousImport);
                shader = AssetDatabase.LoadAssetAtPath<Shader>(ShaderPath);
            }
            if (!shader) throw new InvalidOperationException("Could not load the " + ShaderName + " shader.");
            var path = OutDir + "/Vine Bloom glow " + glow.ToString("0.0", System.Globalization.CultureInfo.InvariantCulture) + ".mat";
            Directory.CreateDirectory(OutDir);
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!mat) { mat = new Material(shader) { enableInstancing = true }; AssetDatabase.CreateAsset(mat, path); }
            mat.shader = shader;
            mat.SetFloat("_Glow", glow);
            EditorUtility.SetDirty(mat);
            return mat;
        }

        public static void WriteReceipt(List<string> findings, string status, string job)
        {
            Directory.CreateDirectory("UnityUnicornReports");
            var stamp = DateTime.UtcNow;
            var rows = string.Join(",\n", findings.Select(f => "        {\"severity\": \"info\", \"message\": \"" + f.Replace("\\", "/").Replace("\"", "'") + "\"}"));
            var json = "{\n    \"schema\": \"unity-unicorn.tool-usage/v1\",\n    \"tool_id\": \"vine-spawn-with-trumpet-flowers\",\n    \"project\": {\"name\": \"" + Path.GetFileName(Directory.GetCurrentDirectory()) + "\"},\n" +
                       "    \"completed_at\": \"" + stamp.ToString("yyyy-MM-ddTHH:mm:ssZ") + "\",\n    \"status\": \"" + status + "\",\n    \"evidence\": \"" +
                       (string.IsNullOrEmpty(job) ? "Vines grown from the vine window" : "Vines grown from the vine window after a job from the page").Replace("\"", "'") + "\",\n" +
                       "    \"findings\": [\n" + rows + "\n    ]\n}\n";
            File.WriteAllText(Path.Combine("UnityUnicornReports", "vine-spawn-with-trumpet-flowers-" + stamp.ToString("yyyyMMdd-HHmmss") + ".json"), json);
        }

        // Unity Stable/Vine Bloom: vertex colours lit by Unity's Standard lighting, both sides of leaves and petals lit,
        // petals (vertex alpha 1) can glow, and leaf and flower tips sway a little (uv2.x = how free a point is).
        const string ShaderSource =
@"// Unity Stable shaders (Unity Unicorn), written by vine-spawn-with-trumpet-flowers, Claude Opus 5.5, 2026-10-19.
// Own work for Astra; free to use in her worlds. Vertex colours, Standard lighting, two-sided, petals glow, tips sway.
Shader ""Unity Stable/Vine Bloom""
{
    Properties
    {
        _Tint (""Tint"", Color) = (1,1,1,1)
        _Gloss (""Stem and leaf gloss"", Range(0,1)) = 0.32
        _PetalGloss (""Petal gloss"", Range(0,1)) = 0.5
        _Glow (""Flower glow"", Range(0,3)) = 0.2
        _Sway (""Sway (m)"", Range(0,0.05)) = 0.006
        _SwaySpeed (""Sway speed"", Range(0,4)) = 1.2
    }
    SubShader
    {
        Tags { ""RenderType""=""Opaque"" ""Queue""=""Geometry"" }
        Cull Off
        CGPROGRAM
        #pragma surface surf Standard vertex:vert addshadow fullforwardshadows
        #pragma target 3.0
        #pragma multi_compile_instancing
        fixed4 _Tint; half _Gloss, _PetalGloss, _Glow, _Sway, _SwaySpeed;
        struct Input { float4 color : COLOR; float facing : VFACE; };
        void vert(inout appdata_full v)
        {
            float free = v.texcoord2.x;
            float3 wp = mul(unity_ObjectToWorld, v.vertex).xyz;
            float t = _Time.y * _SwaySpeed + dot(wp, float3(1.7, 0.9, 1.3));
            float3 off = float3(sin(t), 0.5 * sin(t * 0.73 + 1.1), cos(t * 0.91)) * (_Sway * free);
            v.vertex.xyz += mul((float3x3)unity_WorldToObject, off);
        }
        void surf(Input IN, inout SurfaceOutputStandard o)
        {
            half petal = IN.color.a;
            o.Albedo = IN.color.rgb * _Tint.rgb;
            o.Smoothness = lerp(_Gloss, _PetalGloss, petal);
            o.Metallic = 0;
            o.Emission = IN.color.rgb * _Glow * petal;
            o.Normal = float3(0, 0, IN.facing > 0 ? 1 : -1);
        }
        ENDCG
    }
    FallBack ""Diffuse""
}
";
    }
}
