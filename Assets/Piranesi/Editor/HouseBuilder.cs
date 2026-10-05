// Piranesi > Build House
// Turns the generated data (Meshes/*.bytes, Data/HouseLayout.json, Textures, Audio) into a complete
// VRChat world scene: architecture, statues, sea, sky, lights, light shafts, particles, sound,
// reflection probes, post-processing and the Udon systems (HouseClock + HouseFootsteps).
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.PostProcessing;
using UdonSharp;
using UdonSharpEditor;
using VRC.SDK3.Components;
using Object = UnityEngine.Object;

namespace Piranesi.EditorTools
{
    [InitializeOnLoad]
    public static class HouseBuilder
    {
        const string RetryKey = "Piranesi.BuildRetry";
        static double retryAt;

        static HouseBuilder()
        {
            // resume a build that was waiting for UdonSharp to compile (survives domain reloads)
            if (SessionState.GetInt(RetryKey, 0) > 0)
            {
                retryAt = EditorApplication.timeSinceStartup + 3;
                EditorApplication.update -= RetryTick;
                EditorApplication.update += RetryTick;
            }
        }

        static void ScheduleRetry()
        {
            int n = SessionState.GetInt(RetryKey, 0);
            if (n >= 3)
            {
                SessionState.EraseInt(RetryKey);
                Debug.LogError("[Piranesi] Udon programs did not finish compiling. Wait a moment, then run Piranesi > Build House again.");
                return;
            }
            SessionState.SetInt(RetryKey, n + 1);
            Debug.Log("[Piranesi] Waiting for UdonSharp to compile; the build will continue automatically.");
            retryAt = EditorApplication.timeSinceStartup + 3;
            EditorApplication.update -= RetryTick;
            EditorApplication.update += RetryTick;
        }

        static void RetryTick()
        {
            if (EditorApplication.isCompiling || EditorApplication.isUpdating || EditorApplication.timeSinceStartup < retryAt) return;
            EditorApplication.update -= RetryTick;
            BuildHouse();
        }

        public const string Root = "Assets/Piranesi";
        public const string Gen = Root + "/Generated";
        public const string ScenePath = Root + "/Scenes/PiranesiHouse.unity";
        const int WaterLayer = 4;

        // ------------------------------------------------------------------ layout json
        [Serializable] class LObj { public string name, mesh, col, tag, mv; public float[] p, s, e, spin; public float r; public bool stat, lie, noshadow; }
        [Serializable] class LStatue { public string mesh, role; public float[] p; public float r, s; }
        [Serializable] class LLight { public string kind; public float[] p, color, dir; public float range, intensity, angle; }
        [Serializable] class LShaft { public string kind; public float[] p; public float radius, height, face, dim; }
        [Serializable] class LEmitter { public string kind; public float[] p, size; public float fall, rot; }
        [Serializable] class LProbe { public string name; public float[] p, size; }
        [Serializable] class LReverb { public string preset; public float[] p; public float minD, maxD; }
        [Serializable] class LSound { public string clip; public float[] p; public float vol, minD, maxD, spatial; }
        [Serializable] class LSpawn { public float[] p; public float r; }
        [Serializable] class LTrigger { public float[] p, size; }
        [Serializable] class LSeat { public string kind, text; public float[] p, exit, size; public float r; public LTrigger trigger; }
        [Serializable] class LItem { public string mesh; public float[] p; public float r, s; }
        [Serializable] class LBoat { public string name; public float[] p; public float r; public bool drivable; public LItem[] items; }
        [Serializable] class LCrab { public float[] p; public float r; }
        [Serializable] class LRoute { public float[] a, b; }
        [Serializable] class LDolphins { public float period, duration; public LRoute[] routes; }
        [Serializable] class LVariant { public string name; public float[] @base, tip; public float glow; }
        [Serializable] class LWade { public float y, size; }
        [Serializable] class LSlide { public float[] exit, path; public float exitR; }
        [Serializable] class Layout
        {
            public LObj[] objects; public LStatue[] statues; public LLight[] lights; public LShaft[] shafts;
            public LEmitter[] emitters; public LProbe[] probes; public LReverb[] reverbs; public LSound[] sounds; public LSpawn spawn;
            // v2
            public LSeat[] seats; public LBoat[] boats; public LCrab[] crabs; public LDolphins dolphins; public LVariant[] variants;
            public LWade wade; public LSlide slide;
        }
        // flattened material manifest (gen/manifest_u.py)
        [Serializable] class MEntry
        {
            public string sub, shader, albedo, normal, mask, alpha, key; public bool doubleSided;
            public float[] tint, @base, tip; public float smooth, metal, cutoff, wind, windScale, translucency, vertexTint, height, detail, glow;
        }
        [Serializable] class MList { public MEntry[] entries; }

        static MList LoadManifest()
        {
            string path = Root + "/Data/MaterialsU.json";
            if (!File.Exists(path)) return new MList { entries = new MEntry[0] };
            var ml = JsonUtility.FromJson<MList>(File.ReadAllText(path));
            if (ml.entries == null) ml.entries = new MEntry[0];
            return ml;
        }

        static Vector3 V(float[] a) => a == null || a.Length < 3 ? Vector3.zero : new Vector3(a[0], a[1], a[2]);

        // ------------------------------------------------------------------ entry points
        [MenuItem("Piranesi/Build House", priority = 0)]
        public static void BuildHouse()
        {
            try
            {
                Progress("Preparing project", 0.02f);
                EnsureFolders();
                ConfigureProject();
                Progress("Configuring texture & audio import", 0.05f);
                ConfigureImporters();
                Progress("Compiling Udon programs", 0.1f);
                if (EnsureUdonPrograms()) { ScheduleRetry(); return; }
                Progress("Building meshes", 0.15f);
                var meshes = BuildMeshes();
                Progress("Creating materials", 0.3f);
                var mats = BuildMaterials();
                BuildManifestMaterials(LoadManifest());
                var layout = JsonUtility.FromJson<Layout>(File.ReadAllText(Root + "/Data/HouseLayout.json"));
                Progress("Building scene", 0.4f);
                BuildScene(layout, meshes, mats);
                Progress("Baking reflection probes", 0.85f);
                BakeProbes();
                EditorSceneManager.MarkSceneDirty(EditorSceneManager.GetActiveScene());
                EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene(), ScenePath);
                FrameSpawn(layout);
                SessionState.EraseInt(RetryKey);
                Debug.Log("[Piranesi] The House is built. Open Piranesi > Time, Season & Tide Preview to explore lighting states.");
            }
            catch (InvalidOperationException e) when (e.Message.Contains("outdated script version") || e.Message.Contains("compiled"))
            {
                ScheduleRetry();
            }
            catch (Exception e)
            {
                Debug.LogError("[Piranesi] Build failed: " + e);
                throw;
            }
            finally { EditorUtility.ClearProgressBar(); }
        }

        [MenuItem("Piranesi/Rebake Reflection Probes", priority = 20)]
        public static void BakeProbes()
        {
            HousePreviewWindow.ApplyState(0.32f, 1.3f, 0.25f, false);
            Directory.CreateDirectory(Gen + "/Probes");
            var probes = Object.FindObjectsOfType<ReflectionProbe>();
            int i = 0;
            foreach (var p in probes)
            {
                Progress("Baking probe " + p.name, 0.85f + 0.12f * i++ / Mathf.Max(1, probes.Length));
                string path = $"{Gen}/Probes/{p.name}.exr";
                if (Lightmapping.BakeReflectionProbe(p, path))
                {
                    AssetDatabase.ImportAsset(path);
                    p.customBakedTexture = AssetDatabase.LoadAssetAtPath<Texture>(path);
                    EditorUtility.SetDirty(p);
                }
            }
            HousePreviewWindow.ApplyState(HousePreviewWindow.Day, HousePreviewWindow.Season, HousePreviewWindow.Tide, false);
        }

        [MenuItem("Piranesi/Bake Occlusion Culling", priority = 21)]
        public static void BakeOcclusion()
        {
            StaticOcclusionCulling.smallestOccluder = 3f;
            StaticOcclusionCulling.smallestHole = 0.3f;
            StaticOcclusionCulling.backfaceThreshold = 100;
            StaticOcclusionCulling.GenerateInBackground();
        }

        static void Progress(string msg, float t) => EditorUtility.DisplayProgressBar("Building the House", msg, t);

        // ------------------------------------------------------------------ project setup
        static void EnsureFolders()
        {
            foreach (var d in new[] { Gen, Gen + "/Meshes", Gen + "/Materials", Gen + "/Probes", Root + "/Scenes" })
                Directory.CreateDirectory(d);
            AssetDatabase.Refresh();
        }

        public static int PostLayer;

        static void ConfigureProject()
        {
            if (PlayerSettings.colorSpace != ColorSpace.Linear) PlayerSettings.colorSpace = ColorSpace.Linear;
            var tm = new SerializedObject(AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/TagManager.asset")[0]);
            var layers = tm.FindProperty("layers");
            PostLayer = -1;
            for (int i = 22; i < 32; i++)
            {
                var sp = layers.GetArrayElementAtIndex(i);
                if (sp.stringValue == "PostProcessing") { PostLayer = i; break; }
            }
            if (PostLayer < 0)
            {
                for (int i = 22; i < 32; i++)
                {
                    var sp = layers.GetArrayElementAtIndex(i);
                    if (string.IsNullOrEmpty(sp.stringValue)) { sp.stringValue = "PostProcessing"; PostLayer = i; break; }
                }
                tm.ApplyModifiedProperties();
            }
            if (PostLayer < 0) PostLayer = 22;
            QualitySettings.shadowDistance = Mathf.Max(QualitySettings.shadowDistance, 110f);
        }

        static void ConfigureImporters()
        {
            foreach (var guid in AssetDatabase.FindAssets("t:Texture2D", new[] { Root + "/Textures" }))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                var ti = AssetImporter.GetAtPath(path) as TextureImporter;
                if (ti == null) continue;
                string n = Path.GetFileNameWithoutExtension(path);
                bool normal = n.Contains("Normal");
                bool linear = n.Contains("_Mask") || n == "Noise" || n == "Caustics";
                bool changed = false;
                if (normal && ti.textureType != TextureImporterType.NormalMap) { ti.textureType = TextureImporterType.NormalMap; changed = true; }
                if (!normal && ti.textureType != TextureImporterType.Default) { ti.textureType = TextureImporterType.Default; changed = true; }
                if (linear && ti.sRGBTexture) { ti.sRGBTexture = false; changed = true; }
                if (n == "ParticleAtlas")
                {
                    if (!ti.alphaIsTransparency) { ti.alphaIsTransparency = true; changed = true; }
                    if (ti.wrapMode != TextureWrapMode.Clamp) { ti.wrapMode = TextureWrapMode.Clamp; changed = true; }
                }
                if (ti.maxTextureSize != 2048) { ti.maxTextureSize = 2048; changed = true; }
                if (ti.anisoLevel != 8) { ti.anisoLevel = 8; changed = true; }
                if (ti.mipmapFilter != TextureImporterMipFilter.KaiserFilter) { ti.mipmapFilter = TextureImporterMipFilter.KaiserFilter; changed = true; }
                if (ti.textureCompression != TextureImporterCompression.CompressedHQ) { ti.textureCompression = TextureImporterCompression.CompressedHQ; changed = true; }
                if (changed) ti.SaveAndReimport();
            }
            // v2: scanned/packed prop textures (Imported/<asset>/<sub>_Albedo|_Normal|_Mask.png)
            if (AssetDatabase.IsValidFolder(Root + "/Imported"))
            {
                var alphaTest = new Dictionary<string, float>();
                foreach (var e in LoadManifest().entries)
                    if (!string.IsNullOrEmpty(e.albedo) && (e.alpha == "MASK" || e.alpha == "BLEND"))
                        alphaTest[$"{Root}/Imported/{e.albedo}"] = Mathf.Max(0.05f, e.cutoff);
                AssetDatabase.StartAssetEditing();
                try
                {
                    foreach (var guid in AssetDatabase.FindAssets("t:Texture2D", new[] { Root + "/Imported" }))
                    {
                        string path = AssetDatabase.GUIDToAssetPath(guid);
                        var ti = AssetImporter.GetAtPath(path) as TextureImporter;
                        if (ti == null) continue;
                        string n = Path.GetFileNameWithoutExtension(path);
                        bool normal = n.EndsWith("_Normal");
                        bool linear = n.EndsWith("_Mask");
                        bool changed = false;
                        var want = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
                        if (ti.textureType != want) { ti.textureType = want; changed = true; }
                        if (linear == ti.sRGBTexture && !normal) { ti.sRGBTexture = !linear; changed = true; }
                        if (alphaTest.TryGetValue(path, out float cut))
                        {
                            if (!ti.alphaIsTransparency) { ti.alphaIsTransparency = true; changed = true; }
                            if (!ti.mipMapsPreserveCoverage || Mathf.Abs(ti.alphaTestReferenceValue - cut) > 0.001f)
                            { ti.mipMapsPreserveCoverage = true; ti.alphaTestReferenceValue = cut; changed = true; }
                        }
                        if (ti.maxTextureSize != 2048) { ti.maxTextureSize = 2048; changed = true; }
                        if (ti.anisoLevel != 8) { ti.anisoLevel = 8; changed = true; }
                        if (ti.mipmapFilter != TextureImporterMipFilter.KaiserFilter) { ti.mipmapFilter = TextureImporterMipFilter.KaiserFilter; changed = true; }
                        if (ti.textureCompression != TextureImporterCompression.CompressedHQ) { ti.textureCompression = TextureImporterCompression.CompressedHQ; changed = true; }
                        if (changed) ti.SaveAndReimport();
                    }
                }
                finally { AssetDatabase.StopAssetEditing(); }
            }
            foreach (var guid in AssetDatabase.FindAssets("t:AudioClip", new[] { Root + "/Audio" }))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                var ai = AssetImporter.GetAtPath(path) as AudioImporter;
                if (ai == null) continue;
                bool loop = path.Contains("Loop");
                var s = ai.defaultSampleSettings;
                var want = loop ? AudioClipLoadType.CompressedInMemory : AudioClipLoadType.DecompressOnLoad;
                if (s.loadType != want || s.compressionFormat != AudioCompressionFormat.Vorbis)
                {
                    s.loadType = want;
                    s.compressionFormat = AudioCompressionFormat.Vorbis;
                    s.quality = loop ? 0.55f : 0.8f;
                    ai.defaultSampleSettings = s;
                    ai.loadInBackground = loop;
                    ai.SaveAndReimport();
                }
            }
        }

        // ------------------------------------------------------------------ Udon
        static readonly Type[] UdonTypes = { typeof(HouseClock), typeof(HouseFootsteps), typeof(HouseSeat), typeof(HouseBoat),
                                             typeof(HouseSlide), typeof(HouseCrabs), typeof(HouseDolphins), typeof(HouseSpinner) };

        /// <returns>true if program assets were just created (they compile asynchronously)</returns>
        static bool EnsureUdonPrograms()
        {
            bool created = false;
            foreach (var t in UdonTypes)
            {
                var guid = AssetDatabase.FindAssets(t.Name + " t:MonoScript", new[] { Root + "/Scripts" }).FirstOrDefault();
                if (guid == null) throw new Exception("Script not found: " + t.Name);
                string scriptPath = AssetDatabase.GUIDToAssetPath(guid);
                string progPath = Path.ChangeExtension(scriptPath, ".asset");
                if (AssetDatabase.LoadAssetAtPath<UdonSharpProgramAsset>(progPath) == null)
                {
                    var pa = ScriptableObject.CreateInstance<UdonSharpProgramAsset>();
                    pa.sourceCsScript = AssetDatabase.LoadAssetAtPath<MonoScript>(scriptPath);
                    AssetDatabase.CreateAsset(pa, progPath);
                    created = true;
                }
            }
            if (created)
            {
                AssetDatabase.SaveAssets();
                AssetDatabase.Refresh();
                typeof(UdonSharpProgramAsset).GetMethod("ClearProgramAssetCache", BindingFlags.NonPublic | BindingFlags.Static)?.Invoke(null, null);
            }
            UdonSharpProgramAsset.CompileAllCsPrograms(true);
            return created;
        }

        static T AddUdon<T>(GameObject go) where T : UdonSharpBehaviour
        {
            var b = go.AddComponent<T>();
            var setup = typeof(UdonSharpEditorUtility).GetMethod("RunBehaviourSetup", BindingFlags.NonPublic | BindingFlags.Static, null, new[] { typeof(UdonSharpBehaviour) }, null);
            if (UdonSharpEditorUtility.GetBackingUdonBehaviour(b) == null && setup != null) setup.Invoke(null, new object[] { b });
            return b;
        }

        // ------------------------------------------------------------------ meshes
        public class MeshEntry { public Mesh mesh; public string[] subs; }

        static Dictionary<string, MeshEntry> BuildMeshes()
        {
            var dict = new Dictionary<string, MeshEntry>();
            var files = Directory.GetFiles(Root + "/Meshes", "*.bytes");
            int i = 0;
            foreach (var f in files)
            {
                string name = Path.GetFileNameWithoutExtension(f);
                Progress("Mesh " + name, 0.15f + 0.15f * i++ / files.Length);
                var mesh = ParseMesh(f, out var subs);
                mesh.name = name;
                string path = $"{Gen}/Meshes/{name}.asset";
                var existing = AssetDatabase.LoadAssetAtPath<Mesh>(path);
                if (existing != null)
                {
                    EditorUtility.CopySerialized(mesh, existing);
                    mesh = existing;
                }
                else AssetDatabase.CreateAsset(mesh, path);
                dict[name] = new MeshEntry { mesh = mesh, subs = subs };
            }
            dict["__Shaft"] = new MeshEntry { mesh = SaveMesh(MakeShaftMesh(), "__Shaft"), subs = new[] { "Shaft" } };
            dict["__Quad"] = new MeshEntry { mesh = SaveMesh(MakeQuad(), "__Quad"), subs = new[] { "Glow" } };
            dict["__OceanNear"] = new MeshEntry { mesh = SaveMesh(MakeOceanNear(360f, 1.5f), "__OceanNear"), subs = new[] { "Ocean" } };
            dict["__OceanFar"] = new MeshEntry { mesh = SaveMesh(MakeOceanFar(360f, 1.5f), "__OceanFar"), subs = new[] { "Ocean" } };
            AssetDatabase.SaveAssets();
            return dict;
        }

        static Mesh SaveMesh(Mesh m, string name)
        {
            m.name = name;
            string path = $"{Gen}/Meshes/{name}.asset";
            var existing = AssetDatabase.LoadAssetAtPath<Mesh>(path);
            if (existing != null) { EditorUtility.CopySerialized(m, existing); return existing; }
            AssetDatabase.CreateAsset(m, path);
            return m;
        }

        public static Mesh ParseMesh(string path, out string[] subs)
        {
            using (var br = new BinaryReader(File.OpenRead(path)))
            {
                string magic = Encoding.ASCII.GetString(br.ReadBytes(4));
                bool uvMesh = magic == "PMS2";
                if (magic != "PMS1" && !uvMesh) throw new Exception("Bad mesh file " + path);
                int nv = br.ReadInt32(), ns = br.ReadInt32(); br.ReadInt32();
                var P = new Vector3[nv]; var N = new Vector3[nv]; var C = new Color32[nv];
                for (int i = 0; i < nv; i++) P[i] = new Vector3(br.ReadSingle(), br.ReadSingle(), br.ReadSingle());
                for (int i = 0; i < nv; i++) N[i] = new Vector3(br.ReadSingle(), br.ReadSingle(), br.ReadSingle());
                for (int i = 0; i < nv; i++) C[i] = new Color32(br.ReadByte(), br.ReadByte(), br.ReadByte(), br.ReadByte());
                var mesh = new Mesh { indexFormat = nv > 65000 ? IndexFormat.UInt32 : IndexFormat.UInt16 };
                mesh.vertices = P; mesh.normals = N; mesh.colors32 = C;
                if (uvMesh)
                {
                    var UV0 = new Vector2[nv];
                    for (int i = 0; i < nv; i++) UV0[i] = new Vector2(br.ReadSingle(), br.ReadSingle());
                    mesh.uv = UV0;
                }
                else
                {
                    // stone kit meshes are shaded triplanar: tangents/UVs are placeholders
                    var T = new Vector4[nv]; var UV = new Vector2[nv];
                    for (int i = 0; i < nv; i++)
                    {
                        var n = N[i];
                        var t = Vector3.Cross(n, Mathf.Abs(n.y) < 0.99f ? Vector3.up : Vector3.right).normalized;
                        T[i] = new Vector4(t.x, t.y, t.z, 1f);
                        UV[i] = new Vector2(P[i].x + P[i].z, P[i].y) * 0.25f;
                    }
                    mesh.tangents = T; mesh.uv = UV;
                }
                subs = new string[ns];
                mesh.subMeshCount = ns;
                for (int s = 0; s < ns; s++)
                {
                    int ln = br.ReadInt32();
                    subs[s] = Encoding.UTF8.GetString(br.ReadBytes(ln));
                    int ni = br.ReadInt32();
                    var idx = new int[ni];
                    for (int k = 0; k < ni; k++) idx[k] = br.ReadInt32();
                    mesh.SetTriangles(idx, s, false);
                }
                mesh.RecalculateBounds();
                if (uvMesh) mesh.RecalculateTangents();
                return mesh;
            }
        }

        static Mesh MakeShaftMesh()
        {
            int seg = 24, rings = 6;
            var v = new List<Vector3>(); var tri = new List<int>();
            for (int r = 0; r < rings; r++)
            {
                float y = -(float)r / (rings - 1);
                for (int s = 0; s < seg; s++)
                {
                    float a = s * Mathf.PI * 2f / seg;
                    v.Add(new Vector3(Mathf.Cos(a), y, Mathf.Sin(a)));
                }
            }
            for (int r = 0; r < rings - 1; r++)
                for (int s = 0; s < seg; s++)
                {
                    int a = r * seg + s, b = r * seg + (s + 1) % seg;
                    tri.AddRange(new[] { a, b, b + seg, a, b + seg, a + seg });
                }
            var m = new Mesh(); m.SetVertices(v); m.SetTriangles(tri, 0);
            m.bounds = new Bounds(new Vector3(0, -0.5f, 0), new Vector3(6, 6, 6)); // sheared in shader: keep generous bounds
            return m;
        }

        static Mesh MakeQuad()
        {
            var m = new Mesh();
            m.vertices = new[] { new Vector3(-0.5f, -0.5f, 0), new Vector3(0.5f, -0.5f, 0), new Vector3(0.5f, 0.5f, 0), new Vector3(-0.5f, 0.5f, 0) };
            m.uv = new[] { new Vector2(0, 0), new Vector2(1, 0), new Vector2(1, 1), new Vector2(0, 1) };
            m.triangles = new[] { 0, 2, 1, 0, 3, 2 };
            m.bounds = new Bounds(Vector3.zero, Vector3.one * 3);
            return m;
        }

        static Mesh MakeOceanNear(float size, float step)
        {
            int n = Mathf.RoundToInt(size / step) + 1;
            var v = new Vector3[n * n];
            for (int j = 0; j < n; j++)
                for (int i = 0; i < n; i++)
                    v[j * n + i] = new Vector3(-size / 2 + i * step, 0, -size / 2 + j * step);
            var t = new int[(n - 1) * (n - 1) * 6]; int k = 0;
            for (int j = 0; j < n - 1; j++)
                for (int i = 0; i < n - 1; i++)
                {
                    int a = j * n + i;
                    t[k++] = a; t[k++] = a + n; t[k++] = a + 1;
                    t[k++] = a + 1; t[k++] = a + n; t[k++] = a + n + 1;
                }
            var m = new Mesh { indexFormat = IndexFormat.UInt32 };
            m.vertices = v; m.triangles = t;
            m.normals = Enumerable.Repeat(Vector3.up, v.Length).ToArray();
            m.bounds = new Bounds(Vector3.zero, new Vector3(size + 20, 10, size + 20));
            return m;
        }

        static Mesh MakeOceanFar(float size, float step)
        {
            // rings expanding outward from the near-grid boundary (vertices match exactly -> no seam)
            int n = Mathf.RoundToInt(size / step);
            var boundary = new List<Vector3>();
            float h = size / 2;
            for (int i = 0; i < n; i += 4) boundary.Add(new Vector3(-h + i * step, 0, -h));
            for (int i = 0; i < n; i += 4) boundary.Add(new Vector3(h, 0, -h + i * step));
            for (int i = 0; i < n; i += 4) boundary.Add(new Vector3(h - i * step, 0, h));
            for (int i = 0; i < n; i += 4) boundary.Add(new Vector3(-h, 0, h - i * step));
            float[] scales = { 1f, 1.25f, 1.6f, 2.2f, 3.2f, 5f, 9f, 18f, 35f };
            int bc = boundary.Count;
            var v = new List<Vector3>();
            foreach (var s in scales) foreach (var b in boundary) v.Add(b * s);
            var t = new List<int>();
            for (int r = 0; r < scales.Length - 1; r++)
                for (int i = 0; i < bc; i++)
                {
                    int a = r * bc + i, b = r * bc + (i + 1) % bc;
                    t.AddRange(new[] { a, b, b + bc, a, b + bc, a + bc });
                }
            var m = new Mesh { indexFormat = IndexFormat.UInt32 };
            m.SetVertices(v); m.SetTriangles(t, 0);
            m.normals = Enumerable.Repeat(Vector3.up, v.Count).ToArray();
            m.bounds = new Bounds(Vector3.zero, new Vector3(size * 36, 20, size * 36));
            return m;
        }

        // ------------------------------------------------------------------ materials
        static Texture2D Tex(string n) => AssetDatabase.LoadAssetAtPath<Texture2D>($"{Root}/Textures/{n}.png");

        static Material Mat(string name, string shader, Action<Material> setup)
        {
            string path = $"{Gen}/Materials/{name}.mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            var sh = Shader.Find(shader);
            if (sh == null) throw new Exception("Shader not found: " + shader);
            if (m == null) { m = new Material(sh); AssetDatabase.CreateAsset(m, path); }
            m.shader = sh;
            setup(m);
            EditorUtility.SetDirty(m);
            return m;
        }

        static Material StoneMat(string name, string set, float tile, float smooth, float sparkle, float vao, Color tint, float normal = 1f, float snow = 1f)
        {
            return Mat(name, "Piranesi/Stone", m =>
            {
                m.SetTexture("_MainTex", Tex(set + "_Albedo"));
                m.SetTexture("_BumpMap", Tex(set + "_Normal"));
                m.SetTexture("_MaskTex", Tex(set + "_Mask"));
                m.SetTexture("_Caustics", Tex("Caustics"));
                m.SetTexture("_NoiseTex", Tex("Noise"));
                m.SetFloat("_Tile", tile);
                m.SetFloat("_Smoothness", smooth);
                m.SetFloat("_Sparkle", sparkle);
                m.SetFloat("_VertexAO", vao);
                m.SetFloat("_NormalScale", normal);
                m.SetFloat("_SnowAllowed", snow);
                m.SetColor("_Color", tint);
                m.enableInstancing = true;
            });
        }

        static Material ParticleMat(string name, int tile, Color c, bool additive, float lit)
        {
            return Mat(name, "Piranesi/Particle", m =>
            {
                m.SetTexture("_MainTex", Tex("ParticleAtlas"));
                m.SetFloat("_Tile", tile);
                m.SetColor("_Color", c);
                m.SetFloat("_Lit", lit);
                m.SetFloat("_SrcBlend", additive ? (float)BlendMode.One : (float)BlendMode.SrcAlpha);
                m.SetFloat("_DstBlend", additive ? (float)BlendMode.One : (float)BlendMode.OneMinusSrcAlpha);
                m.enableInstancing = true;
            });
        }

        static Dictionary<string, Material> BuildMaterials()
        {
            var d = new Dictionary<string, Material>();
            d["Floor"] = StoneMat("M_Floor", "Floor", 4f, 1f, 0.5f, 0.6f, Color.white);
            d["Wall"] = StoneMat("M_Wall", "Wall", 4.8f, 0.85f, 0.15f, 0.8f, Color.white);
            d["Stone"] = StoneMat("M_Stone", "Wall", 4.8f, 0.6f, 0.1f, 0.8f, new Color(0.86f, 0.88f, 0.88f));
            d["Marble"] = StoneMat("M_Marble", "MarbleWhite", 3f, 1f, 0.3f, 1f, Color.white);
            d["Verde"] = StoneMat("M_Verde", "MarbleVerde", 1.5f, 1f, 0.3f, 0.6f, Color.white);
            d["Statue"] = StoneMat("M_Statue", "MarbleWhite", 1.6f, 0.85f, 0.25f, 1f, new Color(1f, 0.99f, 0.97f), 0.8f);
            d["Sand"] = StoneMat("M_Sand", "Sand", 4f, 1f, 1.2f, 0f, Color.white, 1.2f);
            d["Gold"] = Mat("M_Gold", "Standard", m =>
            {
                m.SetColor("_Color", new Color(1f, 0.77f, 0.4f)); m.SetFloat("_Metallic", 1f); m.SetFloat("_Glossiness", 0.72f); m.enableInstancing = true;
            });
            d["Iron"] = Mat("M_Iron", "Standard", m =>
            {
                m.SetColor("_Color", new Color(0.05f, 0.05f, 0.055f)); m.SetFloat("_Metallic", 0.6f); m.SetFloat("_Glossiness", 0.35f); m.enableInstancing = true;
            });
            d["Flame"] = Mat("M_Flame", "Piranesi/Flame", m => { m.SetColor("_Color", new Color(1f, 0.62f, 0.3f)); m.SetFloat("_Intensity", 5f); m.enableInstancing = true; });
            d["Glass"] = Mat("M_SkyWindow", "Piranesi/SkyWindow", m => { m.SetTexture("_NoiseTex", Tex("Noise")); m.SetFloat("_Brightness", 1.6f); });
            d["Water"] = Mat("M_Cascade", "Piranesi/Cascade", m => { m.SetTexture("_NoiseTex", Tex("Noise")); });
            d["Ocean"] = Mat("M_Ocean", "Piranesi/Ocean", m =>
            {
                m.SetTexture("_Normal0", Tex("Water_Normal0")); m.SetTexture("_Normal1", Tex("Water_Normal1")); m.SetTexture("_NoiseTex", Tex("Noise"));
            });
            d["Sky"] = Mat("M_Sky", "Piranesi/Sky", m => { m.SetTexture("_NoiseTex", Tex("Noise")); });
            d["ShaftOculus"] = Mat("M_ShaftOculus", "Piranesi/LightShaft", m => { m.SetTexture("_NoiseTex", Tex("Noise")); m.SetFloat("_Intensity", 0.32f); m.SetFloat("_UseFacing", 0f); });
            d["ShaftWindow"] = Mat("M_ShaftWindow", "Piranesi/LightShaft", m => { m.SetTexture("_NoiseTex", Tex("Noise")); m.SetFloat("_Intensity", 0.22f); m.SetFloat("_UseFacing", 1f); m.SetFloat("_Spread", 0.15f); });
            d["ShaftDim"] = Mat("M_ShaftDim", "Piranesi/LightShaft", m => { m.SetTexture("_NoiseTex", Tex("Noise")); m.SetFloat("_Intensity", 0.12f); m.SetFloat("_UseFacing", 1f); m.SetFloat("_Spread", 0.1f); });
            d["Glass2"] = Mat("M_Glass", "Piranesi/Glass", m => { m.SetTexture("_NoiseTex", Tex("Noise")); m.enableInstancing = true; });
            d["ShaftPalm"] = Mat("M_ShaftPalm", "Piranesi/LightShaft", m => { m.SetTexture("_NoiseTex", Tex("Noise")); m.SetFloat("_Intensity", 0.5f); m.SetFloat("_UseFacing", 0f); m.SetFloat("_Spread", 0.04f); m.SetFloat("_Vertical", 1f); });
            d["Glow"] = Mat("M_Glow", "Piranesi/Glow", m => { m.SetFloat("_Size", 1.4f); m.SetFloat("_Intensity", 0.55f); m.enableInstancing = true; });
            d["P_Petal"] = ParticleMat("M_P_Petal", 1, new Color(1f, 0.86f, 0.9f, 0.95f), false, 0.7f);
            d["P_Leaf"] = ParticleMat("M_P_Leaf", 2, Color.white, false, 0.8f);
            d["P_Snow"] = ParticleMat("M_P_Snow", 3, new Color(1f, 1f, 1f, 0.9f), false, 0.6f);
            d["P_Sparkle"] = ParticleMat("M_P_Sparkle", 0, new Color(1f, 0.92f, 0.75f, 0.55f), true, 0f);
            d["P_Mote"] = ParticleMat("M_P_Mote", 0, new Color(1f, 0.85f, 0.55f, 0.8f), true, 0f);
            d["P_Mist"] = ParticleMat("M_P_Mist", 0, new Color(0.9f, 0.95f, 1f, 0.07f), false, 0.8f);
            d["P_Drop"] = ParticleMat("M_P_Drop", 3, new Color(0.85f, 0.95f, 1f, 0.7f), false, 0.7f);
            d["Default"] = d["Marble"];
            AssetDatabase.SaveAssets();
            return d;
        }

        // ------------------------------------------------------------------ manifest (prop / foliage / coral / flow) materials
        static readonly Dictionary<string, Material> subMats = new Dictionary<string, Material>();
        static readonly Dictionary<string, MEntry> subEntries = new Dictionary<string, MEntry>();
        static readonly Dictionary<string, Material> variantMats = new Dictionary<string, Material>();
        static Dictionary<string, LVariant> variants = new Dictionary<string, LVariant>();

        static Texture2D ImpTex(string rel) => string.IsNullOrEmpty(rel) ? null : AssetDatabase.LoadAssetAtPath<Texture2D>($"{Root}/Imported/{rel}");
        static Color Col(float[] c, float a = 1f) => c == null || c.Length < 3 ? Color.white : new Color(c[0], c[1], c[2], a);
        static string Safe(string n) => new string(n.Select(ch => char.IsLetterOrDigit(ch) || ch == '_' ? ch : '_').ToArray());

        static void BuildManifestMaterials(MList ml)
        {
            subMats.Clear(); subEntries.Clear(); variantMats.Clear();
            var byKey = new Dictionary<string, Material>();
            int i = 0;
            foreach (var e in ml.entries)
            {
                if (++i % 10 == 0) Progress("Material " + e.sub, 0.3f + 0.08f * i / Mathf.Max(1, ml.entries.Length));
                if (!byKey.TryGetValue(e.key ?? e.sub, out var mat))
                {
                    mat = MakeManifestMat(e);
                    byKey[e.key ?? e.sub] = mat;
                }
                subMats[e.sub] = mat; subEntries[e.sub] = e;
            }
            AssetDatabase.SaveAssets();
        }

        static Material MakeManifestMat(MEntry e)
        {
            string name = "PM_" + Safe(e.sub);
            switch (e.shader)
            {
                case "foliage":
                    return Mat(name, "Piranesi/Foliage", m =>
                    {
                        m.SetTexture("_MainTex", ImpTex(e.albedo)); m.SetTexture("_BumpMap", ImpTex(e.normal)); m.SetTexture("_MaskTex", ImpTex(e.mask));
                        m.SetColor("_Color", Col(e.tint)); m.SetFloat("_Cutoff", e.cutoff > 0 ? e.cutoff : 0.45f); m.SetFloat("_Smoothness", e.smooth);
                        m.SetFloat("_Wind", e.wind); m.SetFloat("_WindScale", Mathf.Max(0.1f, e.windScale)); m.SetFloat("_Translucency", e.translucency);
                        m.SetFloat("_VertexTint", e.vertexTint); m.SetTexture("_Caustics", Tex("Caustics"));
                        m.enableInstancing = true;
                    });
                case "coral":
                    return Mat(name, "Piranesi/Coral", m =>
                    {
                        m.SetTexture("_MainTex", ImpTex(e.albedo)); m.SetTexture("_BumpMap", ImpTex(e.normal));
                        m.SetColor("_BaseColor", Col(e.@base)); m.SetColor("_TipColor", Col(e.tip));
                        m.SetFloat("_Height", Mathf.Max(0.05f, e.height)); m.SetFloat("_Detail", e.detail); m.SetFloat("_Glow", e.glow);
                        m.SetFloat("_Smoothness", e.smooth); m.SetTexture("_Caustics", Tex("Caustics"));
                        m.enableInstancing = true;
                    });
                case "flow":
                    return Mat(name, "Piranesi/WaterFlow", m =>
                    {
                        m.SetTexture("_Normal0", Tex("Water_Normal0")); m.SetTexture("_NoiseTex", Tex("Noise"));
                        m.SetColor("_Color", new Color(0.55f, 0.85f, 0.9f, 0.72f));
                        m.enableInstancing = true;
                    });
                default:
                    return Mat(name, "Piranesi/Prop", m =>
                    {
                        m.SetTexture("_MainTex", ImpTex(e.albedo)); m.SetTexture("_BumpMap", ImpTex(e.normal)); m.SetTexture("_MaskTex", ImpTex(e.mask));
                        m.SetColor("_Color", Col(e.tint)); m.SetFloat("_Smoothness", e.smooth); m.SetFloat("_Metallic", e.metal);
                        m.SetFloat("_Cutoff", e.cutoff); m.SetFloat("_Cull", e.doubleSided ? 0f : 2f);
                        m.SetTexture("_Caustics", Tex("Caustics")); m.SetFloat("_VertexAO", 0.5f);
                        m.enableInstancing = true;
                    });
            }
        }

        static Material VariantMat(string sub, Material baseMat, string variant)
        {
            if (!variants.TryGetValue(variant, out var v)) return baseMat;
            string key = sub + "#" + variant;
            if (variantMats.TryGetValue(key, out var vm)) return vm;
            vm = Mat("PMV_" + Safe(sub) + "_" + Safe(variant), "Piranesi/Coral", m =>
            {
                m.CopyPropertiesFromMaterial(baseMat);
                m.SetColor("_BaseColor", Col(v.@base)); m.SetColor("_TipColor", Col(v.tip)); m.SetFloat("_Glow", v.glow);
                m.enableInstancing = true;
            });
            variantMats[key] = vm;
            return vm;
        }

        static bool IsManifestMesh(MeshEntry me) => me.subs.Length > 0 && me.subs.All(sb => subEntries.ContainsKey(sb));

        // ------------------------------------------------------------------ scene
        static GameObject Child(Transform parent, string name)
        {
            var g = new GameObject(name);
            g.transform.SetParent(parent, false);
            return g;
        }

        static void BuildScene(Layout L, Dictionary<string, MeshEntry> meshes, Dictionary<string, Material> mats)
        {
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            EditorSceneManager.SaveScene(scene, ScenePath);
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };

            var lighting = AssetDatabase.LoadAssetAtPath<LightingSettings>(Gen + "/PiranesiLighting.lighting");
            if (lighting == null)
            {
                lighting = new LightingSettings { name = "PiranesiLighting", bakedGI = false, realtimeGI = false };
                AssetDatabase.CreateAsset(lighting, Gen + "/PiranesiLighting.lighting");
            }
            Lightmapping.lightingSettings = lighting;

            var root = new GameObject("The House").transform;
            var tArch = Child(root, "Architecture").transform;
            var tStat = Child(root, "Statues").transform;
            var tLight = Child(root, "Lights").transform;
            var tFx = Child(root, "Light Shafts & Particles").transform;
            var tAudio = Child(root, "Sound").transform;
            var tProbe = Child(root, "Reflection Probes").transform;
            var tSys = Child(root, "Systems").transform;

            variants = (L.variants ?? new LVariant[0]).Where(v => v != null && !string.IsNullOrEmpty(v.name)).ToDictionary(v => v.name, v => v);
            Material MatFor(string n, string mv = null)
            {
                if (mats.TryGetValue(n, out var m)) return m;
                if (subMats.TryGetValue(n, out var pm))
                    return !string.IsNullOrEmpty(mv) && subEntries[n].shader == "coral" ? VariantMat(n, pm, mv) : pm;
                return mats["Default"];
            }
            var archFlags = StaticEditorFlags.ContributeGI | StaticEditorFlags.OccluderStatic | StaticEditorFlags.OccludeeStatic | StaticEditorFlags.ReflectionProbeStatic;
            var propFlags = StaticEditorFlags.OccludeeStatic | StaticEditorFlags.ReflectionProbeStatic | StaticEditorFlags.BatchingStatic;
            var tProps = Child(root, "Islands & Props").transform;
            var tReef = Child(root, "Coral Reefs").transform;
            var tIvy = Child(root, "Ivy").transform;

            // ---- architecture & props
            int count = 0;
            foreach (var o in L.objects)
            {
                if (++count % 25 == 0) Progress("Placing " + o.name, 0.4f + 0.2f * count / L.objects.Length);
                bool isIvy = !string.IsNullOrEmpty(o.mesh) && o.mesh.StartsWith("Ivy_");
                meshes.TryGetValue(o.mesh ?? "", out var me);
                bool isProp = me != null && IsManifestMesh(me);
                Transform parent = o.tag == "reef" ? tReef : isIvy ? tIvy : isProp || (o.mesh ?? "").StartsWith("Isle_") ? tProps : tArch;
                var go = new GameObject(o.name);
                go.transform.SetParent(parent, false);
                go.transform.position = V(o.p);
                go.transform.rotation = o.e != null && o.e.Length == 3 ? Quaternion.Euler(o.e[0], o.e[1], o.e[2]) : Quaternion.Euler(o.lie ? 90f : 0f, o.r, 0f);
                go.transform.localScale = o.s != null && o.s.Length == 3 ? V(o.s) : Vector3.one;
                if (string.IsNullOrEmpty(o.mesh))
                {
                    go.transform.localScale = Vector3.one;
                    var bc = go.AddComponent<BoxCollider>();
                    bc.size = V(o.s);
                    continue;
                }
                if (me == null) { Debug.LogWarning("[Piranesi] Missing mesh " + o.mesh); continue; }
                var renderers = new List<Renderer>();
                if (meshes.TryGetValue(o.mesh + "_LOD1", out var lod1))
                {
                    var r0 = MakeRendererMulti(go.transform, "LOD0", me.mesh, me.subs.Select(sb => MatFor(sb, o.mv)).ToArray());
                    var r1 = MakeRendererMulti(go.transform, "LOD1", lod1.mesh, lod1.subs.Select(sb => MatFor(sb, o.mv)).ToArray());
                    var lg = go.AddComponent<LODGroup>();
                    float near = o.tag == "reef" ? 0.07f : isIvy ? 0.14f : 0.1f, far = o.tag == "reef" ? 0.012f : isIvy ? 0.006f : 0.008f;
                    lg.SetLODs(new[] { new LOD(near, new Renderer[] { r0 }), new LOD(far, new Renderer[] { r1 }) });
                    lg.RecalculateBounds();
                    renderers.Add(r0); renderers.Add(r1);
                }
                else
                {
                    go.AddComponent<MeshFilter>().sharedMesh = me.mesh;
                    var mr = go.AddComponent<MeshRenderer>();
                    mr.sharedMaterials = me.subs.Select(sb => MatFor(sb, o.mv)).ToArray();
                    renderers.Add(mr);
                }
                bool distant = o.mesh.StartsWith("Wing") || o.mesh.StartsWith("Seabed");
                bool water = o.mesh == "Cascade" || o.mesh == "AqueductWater" || o.mesh == "SlideWater";
                foreach (var r in renderers)
                {
                    if (distant || water || o.noshadow || o.mesh.StartsWith("Isle_")) r.shadowCastingMode = ShadowCastingMode.Off;
                    if (water) r.gameObject.layer = WaterLayer;
                    if (o.stat && !water && o.mesh != "Lantern")
                        GameObjectUtility.SetStaticEditorFlags(r.gameObject, distant ? StaticEditorFlags.ReflectionProbeStatic : (isIvy || isProp) ? propFlags : archFlags);
                }
                if (water) go.layer = WaterLayer;
                var bnd = me.mesh.bounds;
                switch (o.col)
                {
                    case "mesh": go.AddComponent<MeshCollider>().sharedMesh = me.mesh; break;
                    case "box": { var bc = go.AddComponent<BoxCollider>(); bc.center = bnd.center; bc.size = bnd.size; break; }
                    case "capsule":
                    {
                        var cc = go.AddComponent<CapsuleCollider>();
                        cc.direction = 1; cc.center = bnd.center; cc.height = bnd.size.y;
                        cc.radius = Mathf.Min(bnd.extents.x, bnd.extents.z) * 0.8f;
                        break;
                    }
                }
                if (o.spin != null && o.spin.Length == 4)
                {
                    var sp = AddUdon<HouseSpinner>(go);
                    sp.axis = new Vector3(o.spin[0], o.spin[1], o.spin[2]);
                    sp.degreesPerSecond = o.spin[3];
                    UdonSharpEditorUtility.CopyProxyToUdon(sp);
                }
            }

            // ---- statues (LOD0 / LOD1)
            count = 0;
            foreach (var s in L.statues)
            {
                if (++count % 25 == 0) Progress("Placing statues", 0.6f + 0.1f * count / L.statues.Length);
                if (!meshes.TryGetValue(s.mesh, out var m0)) continue;
                meshes.TryGetValue(s.mesh + "_LOD1", out var m1);
                string label = string.IsNullOrEmpty(s.role) ? s.mesh : s.role;
                var go = new GameObject("Statue - " + label);
                go.transform.SetParent(tStat, false);
                go.transform.position = V(s.p);
                go.transform.rotation = Quaternion.Euler(0, s.r, 0);
                go.transform.localScale = Vector3.one * (s.s <= 0 ? 1f : s.s);
                var r0 = MakeRenderer(go.transform, "LOD0", m0.mesh, mats["Statue"]);
                var lods = new List<LOD> { new LOD(0.16f, new Renderer[] { r0 }) };
                if (m1 != null)
                {
                    var r1 = MakeRenderer(go.transform, "LOD1", m1.mesh, mats["Statue"]);
                    lods.Add(new LOD(0.012f, new Renderer[] { r1 }));
                }
                var lg = go.AddComponent<LODGroup>();
                lg.SetLODs(lods.ToArray());
                lg.RecalculateBounds();
                foreach (var r in go.GetComponentsInChildren<Renderer>())
                    GameObjectUtility.SetStaticEditorFlags(r.gameObject, StaticEditorFlags.OccludeeStatic | StaticEditorFlags.ReflectionProbeStatic | StaticEditorFlags.ContributeGI);
            }

            // ---- sun / moon
            var sunGo = Child(tLight, "Sun & Moon");
            var sun = sunGo.AddComponent<Light>();
            sun.type = LightType.Directional;
            sun.shadows = LightShadows.Soft;
            sun.shadowStrength = 0.85f;
            sun.shadowBias = 0.04f;
            sun.shadowNormalBias = 0.35f;
            sun.lightmapBakeType = LightmapBakeType.Realtime;
            sun.renderMode = LightRenderMode.ForcePixel;
            sunGo.transform.rotation = Quaternion.Euler(50, -30, 0);

            // ---- lanterns
            var lanterns = new List<Light>();
            foreach (var l in L.lights)
            {
                if (l.kind == "spot")
                {
                    // the light from the oculus that always falls on the Colossus' palm
                    var sg = Child(tLight, "Oculus Spotlight (Colossus palm)");
                    sg.transform.position = V(l.p);
                    sg.transform.rotation = Quaternion.LookRotation(l.dir != null && l.dir.Length == 3 ? V(l.dir) : Vector3.down);
                    var sl = sg.AddComponent<Light>();
                    sl.type = LightType.Spot; sl.spotAngle = l.angle > 0 ? l.angle : 20f; sl.innerSpotAngle = sl.spotAngle * 0.55f;
                    sl.range = l.range; sl.intensity = l.intensity; sl.color = Col(l.color);
                    sl.shadows = LightShadows.Soft; sl.shadowStrength = 0.8f; sl.renderMode = LightRenderMode.ForcePixel;
                    sl.lightmapBakeType = LightmapBakeType.Realtime; sl.bounceIntensity = 0f;
                    continue;
                }
                var go = Child(tLight, "Lantern Light");
                go.transform.position = V(l.p);
                var lt = go.AddComponent<Light>();
                lt.type = LightType.Point;
                lt.range = l.range;
                lt.intensity = l.intensity;
                lt.color = new Color(l.color[0], l.color[1], l.color[2]);
                lt.shadows = LightShadows.None;
                lt.renderMode = LightRenderMode.ForcePixel; // 'Important': never swaps with other lights -> no flicker
                lt.bounceIntensity = 0f;
                lt.lightmapBakeType = LightmapBakeType.Realtime;
                lanterns.Add(lt);
                var glow = Child(go.transform, "Glow");
                glow.layer = WaterLayer;
                glow.transform.localPosition = new Vector3(0, -0.15f, 0);
                glow.AddComponent<MeshFilter>().sharedMesh = meshes["__Quad"].mesh;
                var gr = glow.AddComponent<MeshRenderer>();
                gr.sharedMaterial = mats["Glow"];
                gr.shadowCastingMode = ShadowCastingMode.Off; gr.receiveShadows = false;
            }

            // ---- light shafts
            foreach (var s in L.shafts)
            {
                var go = Child(tFx, "Light Shaft (" + s.kind + ")");
                go.layer = WaterLayer;
                go.transform.position = V(s.p);
                go.transform.rotation = Quaternion.Euler(0, s.face, 0);
                go.transform.localScale = new Vector3(s.radius, s.height, s.radius);
                go.AddComponent<MeshFilter>().sharedMesh = meshes["__Shaft"].mesh;
                var r = go.AddComponent<MeshRenderer>();
                r.sharedMaterial = s.kind == "window" ? (s.dim > 0 ? mats["ShaftDim"] : mats["ShaftWindow"]) : s.kind == "palm" ? mats["ShaftPalm"] : mats["ShaftOculus"];
                r.shadowCastingMode = ShadowCastingMode.Off; r.receiveShadows = false;
            }

            // ---- particles
            var seasonSystems = new List<ParticleSystem>[4];
            for (int i = 0; i < 4; i++) seasonSystems[i] = new List<ParticleSystem>();
            foreach (var e in L.emitters)
            {
                var size = V(e.size);
                var pos = V(e.p);
                switch (e.kind)
                {
                    case "season":
                        seasonSystems[0].Add(MakeFall(tFx, "Spring Petals", pos, size, e.fall, mats["P_Petal"], 0.06f, 0.1f, 0.9f, Rate(size, 0.35f, 4f), new Color(1f, 0.85f, 0.9f), new Color(1f, 0.97f, 0.98f), true));
                        seasonSystems[1].Add(MakeFall(tFx, "Summer Motes", pos, size, e.fall, mats["P_Mote"], 0.03f, 0.06f, 0.18f, Rate(size, 0.3f, 3f), new Color(1f, 0.9f, 0.6f), new Color(1f, 0.8f, 0.45f), false));
                        seasonSystems[2].Add(MakeFall(tFx, "Autumn Leaves", pos, size, e.fall, mats["P_Leaf"], 0.12f, 0.2f, 1.25f, Rate(size, 0.25f, 3f), new Color(1f, 0.6f, 0.25f), new Color(0.75f, 0.28f, 0.12f), true));
                        seasonSystems[3].Add(MakeFall(tFx, "Winter Snow", pos, size, e.fall, mats["P_Snow"], 0.035f, 0.07f, 0.8f, Rate(size, 1.6f, 14f), Color.white, new Color(0.9f, 0.95f, 1f), true));
                        break;
                    case "dust":
                        MakeDust(tFx, pos, size, e.rot, mats["P_Sparkle"]);
                        break;
                    case "spray":
                        MakeMist(tFx, "Sea Spray", pos, size, mats["P_Mist"], 6f, 2.5f);
                        break;
                    case "splash":
                        MakeMist(tFx, "Cascade Mist", pos, size, mats["P_Mist"], 10f, 3f);
                        MakeSplash(tFx, pos, size, mats["P_Drop"]);
                        break;
                    case "sparkle":
                        MakeSparkle(tFx, pos, size, mats["P_Sparkle"]);
                        break;
                }
            }

            // ---- sea
            var ocean = Child(root, "Sea (moves with the tide)");
            ocean.layer = WaterLayer;
            ocean.transform.position = new Vector3(0, 0.2f, 0);
            foreach (var key in new[] { "__OceanNear", "__OceanFar" })
            {
                var g = Child(ocean.transform, key == "__OceanNear" ? "Near" : "Far");
                g.layer = WaterLayer;
                g.AddComponent<MeshFilter>().sharedMesh = meshes[key].mesh;
                var r = g.AddComponent<MeshRenderer>();
                r.sharedMaterial = mats["Ocean"];
                r.shadowCastingMode = ShadowCastingMode.Off;
                r.receiveShadows = true;
            }

            // ---- sound
            var windSources = new List<AudioSource>();
            foreach (var s in L.sounds)
            {
                var clip = AssetDatabase.LoadAssetAtPath<AudioClip>($"{Root}/Audio/{s.clip}.wav");
                if (clip == null) { Debug.LogWarning("[Piranesi] Missing clip " + s.clip); continue; }
                var go = Child(tAudio, s.clip);
                go.transform.position = V(s.p);
                var a = go.AddComponent<AudioSource>();
                a.clip = clip; a.loop = true; a.playOnAwake = true; a.volume = s.vol;
                a.spatialBlend = s.spatial; a.rolloffMode = AudioRolloffMode.Logarithmic;
                a.minDistance = Mathf.Max(0.5f, s.minD); a.maxDistance = Mathf.Max(5f, s.maxD); a.dopplerLevel = 0f;
                var sp = go.AddComponent<VRCSpatialAudioSource>();
                sp.EnableSpatialization = s.spatial > 0.5f;
                sp.Near = 0f; sp.Far = Mathf.Max(5f, s.maxD); sp.Gain = 0f; sp.UseAudioSourceVolumeCurve = true;
                if (s.clip == "Wind_Loop") windSources.Add(a);
            }
            foreach (var rv in L.reverbs)
            {
                var go = Child(tAudio, "Reverb " + rv.preset);
                go.transform.position = V(rv.p);
                var z = go.AddComponent<AudioReverbZone>();
                z.minDistance = rv.minD; z.maxDistance = rv.maxD;
                if (Enum.TryParse(rv.preset, out AudioReverbPreset preset)) z.reverbPreset = preset;
            }
            var shimmerGo = Child(tAudio, "Season Shimmer");
            var shimmer = shimmerGo.AddComponent<AudioSource>();
            shimmer.clip = AssetDatabase.LoadAssetAtPath<AudioClip>($"{Root}/Audio/Season_Shimmer.wav");
            shimmer.playOnAwake = false; shimmer.spatialBlend = 0f; shimmer.volume = 0.35f;
            var shSp = shimmerGo.AddComponent<VRCSpatialAudioSource>();
            shSp.EnableSpatialization = false; shSp.Gain = 0f; shSp.UseAudioSourceVolumeCurve = true;

            // ---- reflection probes
            foreach (var p in L.probes)
            {
                var go = Child(tProbe, "Probe_" + p.name);
                go.transform.position = V(p.p);
                var rp = go.AddComponent<ReflectionProbe>();
                rp.mode = ReflectionProbeMode.Custom;
                rp.boxProjection = true;
                rp.size = V(p.size);
                rp.resolution = 256; rp.hdr = true; rp.importance = 1; rp.blendDistance = 3f;
                rp.cullingMask = ~(1 << WaterLayer);
                rp.nearClipPlane = 0.3f; rp.farClipPlane = 600f;
            }
            {
                var go = Child(tProbe, "Probe_Sky");
                go.transform.position = new Vector3(0, 20, 0);
                var rp = go.AddComponent<ReflectionProbe>();
                rp.mode = ReflectionProbeMode.Custom; rp.boxProjection = false;
                rp.size = new Vector3(4000, 800, 4000); rp.resolution = 256; rp.hdr = true; rp.importance = 0;
                rp.cullingMask = ~(1 << WaterLayer); rp.farClipPlane = 3000f;
            }

            // ---- environment
            RenderSettings.skybox = mats["Sky"];
            RenderSettings.sun = sun;
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.Exponential;
            RenderSettings.fogDensity = 0.006f;

            // ---- reference camera + post processing
            var camGo = Child(tSys, "Reference Camera");
            var cam = camGo.AddComponent<Camera>();
            cam.nearClipPlane = 0.05f; cam.farClipPlane = 3000f; cam.allowHDR = true; cam.allowMSAA = true;
            cam.enabled = false;
            var ppl = camGo.AddComponent<PostProcessLayer>();
            var res = AssetDatabase.LoadAssetAtPath<PostProcessResources>("Packages/com.unity.postprocessing/PostProcessing/PostProcessResources.asset");
            if (res != null) ppl.Init(res);
            ppl.volumeLayer = 1 << PostLayer;
            ppl.volumeTrigger = camGo.transform;
            ppl.antialiasingMode = PostProcessLayer.Antialiasing.None;
            var ppGo = Child(tSys, "Post Processing");
            ppGo.layer = PostLayer;
            var vol = ppGo.AddComponent<PostProcessVolume>();
            vol.isGlobal = true; vol.priority = 1; vol.sharedProfile = BuildPostProfile();

            // ---- VRChat world descriptor + spawn
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>("Packages/com.vrchat.worlds/Samples/UdonExampleScene/Prefabs/VRCWorld.prefab");
            GameObject world = prefab != null ? (GameObject)PrefabUtility.InstantiatePrefab(prefab) : new GameObject("VRCWorld");
            world.transform.SetParent(tSys, true);
            world.transform.position = V(L.spawn.p);
            world.transform.rotation = Quaternion.Euler(0, L.spawn.r, 0);
            var desc = world.GetComponent<VRCSceneDescriptor>();
            if (desc == null) desc = world.AddComponent<VRCSceneDescriptor>();
            desc.spawns = new[] { world.transform };
            desc.ReferenceCamera = camGo;
            desc.RespawnHeightY = -25f;
            EditorUtility.SetDirty(desc);

            // ---- v2: seats, gondolas, slide, crabs, dolphins, wading floor
            var v2 = BuildV2Systems(L, meshes, mats, root, ocean.transform, MatFor);

            // ---- Udon systems
            var fsGo = Child(tSys, "Footsteps");
            var fsSrc = fsGo.AddComponent<AudioSource>();
            fsSrc.playOnAwake = false; fsSrc.spatialBlend = 1f; fsSrc.minDistance = 0.6f; fsSrc.maxDistance = 14f; fsSrc.rolloffMode = AudioRolloffMode.Logarithmic; fsSrc.dopplerLevel = 0;
            var fsSp = fsGo.AddComponent<VRCSpatialAudioSource>();
            fsSp.Near = 0f; fsSp.Far = 14f; fsSp.Gain = 0f; fsSp.UseAudioSourceVolumeCurve = true;
            var steps = AddUdon<HouseFootsteps>(fsGo);
            steps.source = fsSrc;
            steps.marble = Clips("Step_Marble_");
            steps.sand = Clips("Step_Sand_");
            steps.water = Clips("Step_Water_");
            UdonSharpEditorUtility.CopyProxyToUdon(steps);

            var clockGo = Child(tSys, "House Clock");
            var clock = AddUdon<HouseClock>(clockGo);
            clock.mainLight = sun;
            clock.water = ocean.transform;
            clock.lanterns = lanterns.ToArray();
            clock.spring = seasonSystems[0].ToArray();
            clock.summer = seasonSystems[1].ToArray();
            clock.autumn = seasonSystems[2].ToArray();
            clock.winter = seasonSystems[3].ToArray();
            clock.windSources = windSources.ToArray();
            clock.shimmer = shimmer;
            clock.footsteps = steps;
            clock.boats = v2.boats;
            clock.dolphins = v2.dolphins;
            SetPalettes(clock);
            UdonSharpEditorUtility.CopyProxyToUdon(clock);

            HousePreviewWindow.ApplyState(HousePreviewWindow.Day, HousePreviewWindow.Season, HousePreviewWindow.Tide, false);
            EditorSceneManager.SaveScene(scene, ScenePath);
        }

        // ------------------------------------------------------------------ v2 systems
        class V2Result { public HouseBoat[] boats = new HouseBoat[0]; public HouseDolphins dolphins; }

        static readonly Vector3[] GondolaSeats = { new Vector3(0f, 0.5f, -1.9f), new Vector3(0f, 0.5f, -0.4f), new Vector3(0f, 0.5f, 1.1f) };
        const float HullDrop = -0.18f;

        static GameObject MakeMeshObject(Transform parent, string name, string mesh, Dictionary<string, MeshEntry> meshes, Func<string, string, Material> matFor, bool shadows = true)
        {
            var go = Child(parent, name);
            if (!meshes.TryGetValue(mesh, out var me)) { Debug.LogWarning("[Piranesi] Missing mesh " + mesh); return go; }
            var rs = new List<Renderer>();
            if (meshes.TryGetValue(mesh + "_LOD1", out var l1))
            {
                rs.Add(MakeRendererMulti(go.transform, "LOD0", me.mesh, me.subs.Select(sb => matFor(sb, null)).ToArray()));
                rs.Add(MakeRendererMulti(go.transform, "LOD1", l1.mesh, l1.subs.Select(sb => matFor(sb, null)).ToArray()));
                var lg = go.AddComponent<LODGroup>();
                lg.SetLODs(new[] { new LOD(0.1f, new[] { rs[0] }), new LOD(0.008f, new[] { rs[1] }) });
                lg.RecalculateBounds();
            }
            else
            {
                go.AddComponent<MeshFilter>().sharedMesh = me.mesh;
                var mr = go.AddComponent<MeshRenderer>();
                mr.sharedMaterials = me.subs.Select(sb => matFor(sb, null)).ToArray();
                rs.Add(mr);
            }
            if (!shadows) foreach (var r in rs) r.shadowCastingMode = ShadowCastingMode.Off;
            return go;
        }

        static HouseSeat MakeSeat(Transform parent, string name, Vector3 pos, float yaw, Vector3 exit, string text, Vector3 colSize,
                                  VRC.SDKBase.VRCStation.Mobility mobility, VRCStation existing = null, float proximity = 2.5f)
        {
            var go = Child(parent, name);
            go.transform.SetPositionAndRotation(pos, Quaternion.Euler(0f, yaw, 0f));
            VRCStation st = existing;
            if (st == null)
            {
                var exitT = Child(go.transform, "Exit").transform;
                exitT.SetPositionAndRotation(exit, Quaternion.Euler(0f, yaw, 0f));
                st = go.AddComponent<VRCStation>();
                st.PlayerMobility = mobility;
                st.seated = true;
                st.canUseStationFromStation = false;
                st.disableStationExit = false;
                st.stationEnterPlayerLocation = go.transform;
                st.stationExitPlayerLocation = exitT;
            }
            var bc = go.AddComponent<BoxCollider>();
            bc.isTrigger = true; bc.size = colSize; bc.center = new Vector3(0f, colSize.y * 0.5f, 0f);
            var seat = AddUdon<HouseSeat>(go);
            seat.station = st;
            UdonSharpEditorUtility.CopyProxyToUdon(seat);
            var ub = UdonSharpEditorUtility.GetBackingUdonBehaviour(seat);
            if (ub != null) { ub.interactText = text; ub.proximity = proximity; EditorUtility.SetDirty(ub); }
            return seat;
        }

        static void SetInteract(UdonSharpBehaviour b, string text, float proximity)
        {
            var ub = UdonSharpEditorUtility.GetBackingUdonBehaviour(b);
            if (ub != null) { ub.interactText = text; ub.proximity = proximity; EditorUtility.SetDirty(ub); }
        }

        static AudioSource MakeOneShot(Transform parent, string name, AudioClip clip, float vol, float maxD, bool loop = false)
        {
            var g = Child(parent, name);
            var a = g.AddComponent<AudioSource>();
            a.clip = clip; a.playOnAwake = false; a.loop = loop; a.volume = vol; a.spatialBlend = 1f;
            a.minDistance = 1f; a.maxDistance = maxD; a.rolloffMode = AudioRolloffMode.Logarithmic; a.dopplerLevel = 0f;
            var sp = g.AddComponent<VRCSpatialAudioSource>();
            sp.Near = 0f; sp.Far = maxD; sp.Gain = 0f; sp.UseAudioSourceVolumeCurve = true;
            return a;
        }

        static V2Result BuildV2Systems(Layout L, Dictionary<string, MeshEntry> meshes, Dictionary<string, Material> mats, Transform root,
                                       Transform sea, Func<string, string, Material> matFor)
        {
            var res = new V2Result();
            var water = Clips("Step_Water_");
            AudioClip WaterClip(int i) => water.Length > 0 ? water[i % water.Length] : null;
            var tSeats = Child(root, "Seats (window seats, benches, hammocks, the palm)").transform;
            var immobile = VRC.SDKBase.VRCStation.Mobility.Immobilize;
            var vehicle = VRC.SDKBase.VRCStation.Mobility.ImmobilizeForVehicle;

            // ---- seats
            int n = 0;
            foreach (var s in L.seats ?? new LSeat[0])
            {
                if (s == null || s.p == null || s.p.Length < 3) continue;
                Progress("Seats", 0.62f + 0.04f * n++ / Mathf.Max(1, L.seats.Length));
                var size = s.size != null && s.size.Length == 3 ? V(s.size) : new Vector3(0.8f, 0.5f, 0.8f);
                var seat = MakeSeat(tSeats, "Seat (" + s.kind + ")", V(s.p), s.r, s.exit != null && s.exit.Length == 3 ? V(s.exit) : V(s.p) + Vector3.up * 0.2f,
                                    string.IsNullOrEmpty(s.text) ? "Sit" : s.text, size, immobile);
                if (s.trigger != null && s.trigger.p != null && s.trigger.p.Length == 3)
                {
                    // the palm is 14 m up: the interaction lives on the pedestal and lifts you into the hand
                    var tg = MakeSeat(tSeats, "Rest in the palm (pedestal)", V(s.trigger.p), s.r, Vector3.zero, s.text,
                                      s.trigger.size != null && s.trigger.size.Length == 3 ? V(s.trigger.size) : Vector3.one, immobile, (VRCStation)seat.station, 4f);
                    tg.transform.position = V(s.trigger.p) - Vector3.up * (tg.GetComponent<BoxCollider>().size.y * 0.5f);
                }
            }

            // ---- gondolas (Venetian long canoes): row from the stern seat
            var tBoats = Child(root, "Gondolas").transform;
            var boats = new List<HouseBoat>();
            int bi = 0;
            foreach (var b in L.boats ?? new LBoat[0])
            {
                var go = Child(tBoats, "Gondola - " + (b.name ?? "boat") + " " + (++bi));
                go.transform.SetPositionAndRotation(new Vector3(b.p[0], 0.2f, b.p[2]), Quaternion.Euler(0f, b.r, 0f));
                var hull = MakeMeshObject(go.transform, "Hull", "Gondola", meshes, matFor);
                hull.transform.localPosition = new Vector3(0f, HullDrop, 0f);
                foreach (var it in b.items ?? new LItem[0])
                {
                    var ig = MakeMeshObject(hull.transform, it.mesh, it.mesh, meshes, matFor, false);
                    ig.transform.localPosition = V(it.p);
                    ig.transform.localRotation = Quaternion.Euler(0f, it.r, 0f);
                    ig.transform.localScale = Vector3.one * (it.s > 0 ? it.s : 1f);
                }
                HouseBoat hb = null;
                if (b.drivable)
                {
                    var paddle = MakeOneShot(go.transform, "Paddle", WaterClip(bi), 0.6f, 18f);
                    hb = AddUdon<HouseBoat>(go);
                    hb.paddleSound = paddle;
                    hb.hitMask = 1;
                    UdonSharpEditorUtility.CopyProxyToUdon(hb);
                    boats.Add(hb);
                }
                for (int i = 0; i < GondolaSeats.Length; i++)
                {
                    var lp = GondolaSeats[i] + new Vector3(0f, HullDrop, 0f);
                    bool driver = i == 0 && hb != null;
                    var seat = MakeSeat(go.transform, driver ? "Seat (rower, stern)" : "Seat (passenger)", go.transform.TransformPoint(lp), b.r,
                                        go.transform.TransformPoint(new Vector3(1.5f, 0.4f, lp.z)),
                                        driver ? "Row the gondola (move to paddle, turn to steer)" : "Sit in the gondola",
                                        new Vector3(0.9f, 0.5f, 0.6f), hb != null ? vehicle : immobile, null, 3f);
                    seat.boat = hb; seat.isDriver = driver;
                    UdonSharpEditorUtility.CopyProxyToUdon(seat);
                }
            }
            res.boats = boats.ToArray();

            // ---- the water slide from the top of the stair tower to the south beach
            if (L.slide != null && L.slide.path != null && L.slide.path.Length >= 6)
            {
                var pts = new Vector3[L.slide.path.Length / 3];
                for (int i = 0; i < pts.Length; i++) pts[i] = new Vector3(L.slide.path[i * 3], L.slide.path[i * 3 + 1], L.slide.path[i * 3 + 2]);
                var sgo = Child(root, "Water Slide (ride)");
                sgo.transform.position = pts[0];
                var trig = sgo.AddComponent<BoxCollider>();
                trig.isTrigger = true; trig.size = new Vector3(1.6f, 1.2f, 1.6f); trig.center = new Vector3(0f, 0.3f, 0f);
                var sled = Child(sgo.transform, "Sled");
                var vis = GameObject.CreatePrimitive(PrimitiveType.Cube);
                vis.name = "Sled cushion"; vis.transform.SetParent(sled.transform, false);
                vis.transform.localScale = new Vector3(0.7f, 0.1f, 1.1f); vis.transform.localPosition = new Vector3(0f, 0.05f, 0f);
                Object.DestroyImmediate(vis.GetComponent<BoxCollider>());
                vis.GetComponent<MeshRenderer>().sharedMaterial = subMats.TryGetValue("Gondola_LinenRed", out var linen) ? linen : mats["Gold"];
                var seatT = Child(sled.transform, "Seat"); seatT.transform.localPosition = new Vector3(0f, 0.12f, 0f);
                var exitT = Child(root, "Water Slide exit (beach)").transform;
                exitT.SetPositionAndRotation(L.slide.exit != null && L.slide.exit.Length == 3 ? V(L.slide.exit) : pts[pts.Length - 1], Quaternion.Euler(0f, L.slide.exitR, 0f));
                var st = seatT.AddComponent<VRCStation>();
                st.PlayerMobility = vehicle; st.seated = true; st.canUseStationFromStation = false; st.disableStationExit = false;
                st.stationEnterPlayerLocation = seatT.transform; st.stationExitPlayerLocation = exitT;
                var ride = MakeOneShot(sled.transform, "Ride", AssetDatabase.LoadAssetAtPath<AudioClip>($"{Root}/Audio/Cascade_Loop.wav"), 0.45f, 25f, true);
                var endGo = Child(root, "Water Slide splash"); endGo.transform.position = pts[pts.Length - 1];
                var splashA = MakeOneShot(endGo.transform, "Splash", WaterClip(3), 1f, 30f);
                var hs = AddUdon<HouseSlide>(sgo);
                hs.station = st; hs.sled = sled.transform; hs.path = pts; hs.exitPoint = exitT;
                hs.rideSound = ride; hs.splashSound = splashA; hs.splashFx = MakeBurst(endGo.transform, mats["P_Drop"], 120);
                UdonSharpEditorUtility.CopyProxyToUdon(hs);
                SetInteract(hs, "Ride the slide", 3f);
            }

            // ---- crabs
            if (L.crabs != null && L.crabs.Length > 0)
            {
                var croot = Child(root, "Crabs");
                var list = new List<Transform>();
                foreach (var c in L.crabs)
                {
                    var cg = MakeMeshObject(croot.transform, "Crab", "Crab_Blue", meshes, matFor);
                    cg.transform.SetPositionAndRotation(V(c.p), Quaternion.Euler(0f, c.r, 0f));
                    list.Add(cg.transform);
                }
                var hc = AddUdon<HouseCrabs>(croot);
                hc.crabs = list.ToArray(); hc.groundMask = 1;
                UdonSharpEditorUtility.CopyProxyToUdon(hc);
            }

            // ---- dolphins (occasionally)
            if (L.dolphins != null && L.dolphins.routes != null && L.dolphins.routes.Length > 0)
            {
                var droot = Child(root, "Dolphins");
                var ds = new List<Transform>();
                for (int i = 0; i < 3; i++)
                {
                    var d = Child(droot.transform, "Dolphin " + (i + 1));
                    var m = MakeMeshObject(d.transform, "Body", "Dolphin", meshes, matFor);
                    m.transform.localRotation = Quaternion.Euler(0f, -90f, 0f);     // mesh nose is +X; the script steers +Z
                    m.transform.localScale = Vector3.one * (i == 1 ? 1.08f : 0.95f);
                    ds.Add(d.transform);
                }
                var hd = AddUdon<HouseDolphins>(droot);
                hd.dolphins = ds.ToArray();
                hd.routeStart = L.dolphins.routes.Select(r => V(r.a)).ToArray();
                hd.routeEnd = L.dolphins.routes.Select(r => V(r.b)).ToArray();
                hd.period = L.dolphins.period > 0 ? L.dolphins.period : 110f;
                hd.duration = L.dolphins.duration > 0 ? L.dolphins.duration : 22f;
                hd.splash = MakeBurst(droot.transform, mats["P_Drop"], 60);
                hd.splashSound = MakeOneShot(droot.transform, "Splash", WaterClip(1), 0.9f, 60f);
                UdonSharpEditorUtility.CopyProxyToUdon(hd);
                res.dolphins = hd;
            }

            // ---- wading floor: open water is chest-deep everywhere (rises and falls with the sea)
            if (L.wade != null && L.wade.size > 0)
            {
                var wg = Child(sea, "Wading floor");
                int env = LayerMask.NameToLayer("Environment");
                wg.layer = env >= 0 ? env : 11;
                var bc = wg.AddComponent<BoxCollider>();
                bc.size = new Vector3(L.wade.size, 0.4f, L.wade.size);
                bc.center = new Vector3(0f, L.wade.y - 0.2f, 0f);
            }
            return res;
        }

        static void MakeSparkle(Transform parent, Vector3 pos, Vector3 size, Material mat)
        {
            var ps = NewSystem(parent, "Palm Sparkles", pos, mat, out var r);
            r.maxParticleSize = 0.2f;
            var main = ps.main;
            main.loop = true; main.playOnAwake = true; main.prewarm = true; main.duration = 5f;
            main.startLifetime = new ParticleSystem.MinMaxCurve(1.5f, 3.5f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(0f, 0.08f);
            main.startSize = new ParticleSystem.MinMaxCurve(0.02f, 0.07f);
            main.startColor = new ParticleSystem.MinMaxGradient(new Color(1f, 0.95f, 0.8f, 0.9f), new Color(0.85f, 0.95f, 1f, 0.7f));
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.gravityModifier = -0.01f;
            main.maxParticles = 300;
            var em = ps.emission; em.rateOverTime = 45f;
            var sh = ps.shape; sh.enabled = true; sh.shapeType = ParticleSystemShapeType.Sphere; sh.radius = Mathf.Max(size.x, size.z) * 0.5f;
            var nz = ps.noise; nz.enabled = true; nz.strength = 0.08f; nz.frequency = 0.6f; nz.scrollSpeed = 0.2f;
            var g = new Gradient();
            g.SetKeys(new[] { new GradientColorKey(Color.white, 0), new GradientColorKey(Color.white, 1) },
                      new[] { new GradientAlphaKey(0, 0), new GradientAlphaKey(1, 0.1f), new GradientAlphaKey(0.2f, 0.4f), new GradientAlphaKey(1, 0.6f), new GradientAlphaKey(0, 1) });
            var col = ps.colorOverLifetime; col.enabled = true; col.color = new ParticleSystem.MinMaxGradient(g);
            ps.Play();
        }

        static ParticleSystem MakeBurst(Transform parent, Material mat, int maxP)
        {
            var ps = NewSystem(parent, "Splash", parent.position, mat, out var r);
            var main = ps.main;
            main.loop = false; main.playOnAwake = false; main.duration = 1f;
            main.startLifetime = new ParticleSystem.MinMaxCurve(0.6f, 1.4f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(2f, 5.5f);
            main.startSize = new ParticleSystem.MinMaxCurve(0.04f, 0.14f);
            main.gravityModifier = 1f;
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.maxParticles = maxP;
            var em = ps.emission; em.enabled = true; em.rateOverTime = 0f;
            em.SetBursts(new[] { new ParticleSystem.Burst(0f, (short)(maxP * 0.8f)) });
            var sh = ps.shape; sh.enabled = true; sh.shapeType = ParticleSystemShapeType.Cone; sh.angle = 28f; sh.radius = 0.6f;
            sh.rotation = new Vector3(-90f, 0f, 0f);
            return ps;
        }

        static AudioClip[] Clips(string prefix)
        {
            var list = new List<AudioClip>();
            for (int i = 0; i < 12; i++)
            {
                var c = AssetDatabase.LoadAssetAtPath<AudioClip>($"{Root}/Audio/{prefix}{i}.wav");
                if (c != null) list.Add(c);
            }
            return list.ToArray();
        }

        static Renderer MakeRendererMulti(Transform parent, string name, Mesh mesh, Material[] mats)
        {
            var g = Child(parent, name);
            g.AddComponent<MeshFilter>().sharedMesh = mesh;
            var r = g.AddComponent<MeshRenderer>();
            r.sharedMaterials = mats;
            return r;
        }

        static Renderer MakeRenderer(Transform parent, string name, Mesh mesh, Material mat)
        {
            var g = Child(parent, name);
            g.AddComponent<MeshFilter>().sharedMesh = mesh;
            var r = g.AddComponent<MeshRenderer>();
            r.sharedMaterial = mat;
            return r;
        }

        static float Rate(Vector3 size, float perM2, float min) => Mathf.Max(min, size.x * size.z * perM2);

        static ParticleSystem NewSystem(Transform parent, string name, Vector3 pos, Material mat, out ParticleSystemRenderer renderer)
        {
            var go = Child(parent, name);
            go.layer = WaterLayer;
            go.transform.position = pos;
            var ps = go.AddComponent<ParticleSystem>();
            ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            renderer = go.GetComponent<ParticleSystemRenderer>();
            renderer.renderMode = ParticleSystemRenderMode.Billboard;
            renderer.sharedMaterial = mat;
            renderer.shadowCastingMode = ShadowCastingMode.Off;
            renderer.receiveShadows = false;
            renderer.maxParticleSize = 0.5f;
            renderer.allowRoll = false;
            return ps;
        }

        static Gradient FadeGradient(float peak = 1f)
        {
            var g = new Gradient();
            g.SetKeys(new[] { new GradientColorKey(Color.white, 0), new GradientColorKey(Color.white, 1) },
                      new[] { new GradientAlphaKey(0, 0), new GradientAlphaKey(peak, 0.12f), new GradientAlphaKey(peak, 0.8f), new GradientAlphaKey(0, 1) });
            return g;
        }

        static ParticleSystem MakeFall(Transform parent, string name, Vector3 pos, Vector3 size, float fall, Material mat,
            float sMin, float sMax, float speed, float rate, Color c1, Color c2, bool spin)
        {
            var ps = NewSystem(parent, name, pos, mat, out _);
            var main = ps.main;
            main.loop = true; main.playOnAwake = false; main.duration = 10f;
            float life = Mathf.Max(fall, 2f) / Mathf.Max(speed, 0.05f) * 1.05f;
            if (speed < 0.3f) life = 14f;
            main.startLifetime = new ParticleSystem.MinMaxCurve(life * 0.9f, life);
            main.startSpeed = 0f;
            main.startSize = new ParticleSystem.MinMaxCurve(sMin, sMax);
            main.startColor = new ParticleSystem.MinMaxGradient(c1, c2);
            main.startRotation = new ParticleSystem.MinMaxCurve(0f, Mathf.PI * 2f);
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.maxParticles = 900;
            main.scalingMode = ParticleSystemScalingMode.Shape;
            var em = ps.emission; em.rateOverTime = rate;
            var sh = ps.shape; sh.enabled = true; sh.shapeType = ParticleSystemShapeType.Box; sh.scale = size;
            var vel = ps.velocityOverLifetime; vel.enabled = true; vel.space = ParticleSystemSimulationSpace.World;
            float drift = speed < 0.3f ? 0.08f : 0.25f;
            vel.x = new ParticleSystem.MinMaxCurve(-drift, drift);
            vel.y = speed < 0.3f ? new ParticleSystem.MinMaxCurve(-0.08f, 0.08f) : new ParticleSystem.MinMaxCurve(-speed * 1.15f, -speed * 0.85f);
            vel.z = new ParticleSystem.MinMaxCurve(-drift, drift);
            var nz = ps.noise; nz.enabled = true; nz.strength = speed < 0.3f ? 0.15f : 0.45f; nz.frequency = 0.25f; nz.scrollSpeed = 0.15f; nz.quality = ParticleSystemNoiseQuality.Medium;
            if (spin) { var rol = ps.rotationOverLifetime; rol.enabled = true; rol.z = new ParticleSystem.MinMaxCurve(-2.5f, 2.5f); }
            var col = ps.colorOverLifetime; col.enabled = true; col.color = new ParticleSystem.MinMaxGradient(FadeGradient());
            return ps;
        }

        static void MakeDust(Transform parent, Vector3 pos, Vector3 size, float rot, Material mat)
        {
            var ps = NewSystem(parent, "Dust Sparkles", pos, mat, out _);
            ps.transform.rotation = Quaternion.Euler(0, rot, 0);
            var main = ps.main;
            main.loop = true; main.playOnAwake = true; main.prewarm = true; main.duration = 10f;
            main.startLifetime = new ParticleSystem.MinMaxCurve(6f, 11f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(0f, 0.04f);
            main.startSize = new ParticleSystem.MinMaxCurve(0.012f, 0.035f);
            main.startColor = new ParticleSystem.MinMaxGradient(new Color(1f, 0.95f, 0.85f, 0.6f), new Color(0.85f, 0.95f, 1f, 0.4f));
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.maxParticles = 400;
            main.scalingMode = ParticleSystemScalingMode.Shape;
            var em = ps.emission; em.rateOverTime = Mathf.Clamp(size.x * size.y * size.z * 0.008f, 8f, 45f);
            var sh = ps.shape; sh.enabled = true; sh.shapeType = ParticleSystemShapeType.Box; sh.scale = size;
            var nz = ps.noise; nz.enabled = true; nz.strength = 0.12f; nz.frequency = 0.2f; nz.scrollSpeed = 0.05f;
            var col = ps.colorOverLifetime; col.enabled = true; col.color = new ParticleSystem.MinMaxGradient(FadeGradient());
            ps.Play();
        }

        static void MakeMist(Transform parent, string name, Vector3 pos, Vector3 size, Material mat, float rate, float sz)
        {
            var ps = NewSystem(parent, name, pos, mat, out var r);
            r.maxParticleSize = 2f;
            var main = ps.main;
            main.loop = true; main.playOnAwake = true; main.prewarm = true;
            main.startLifetime = new ParticleSystem.MinMaxCurve(3f, 6f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(0.1f, 0.5f);
            main.startSize = new ParticleSystem.MinMaxCurve(sz * 0.6f, sz);
            main.startRotation = new ParticleSystem.MinMaxCurve(0f, Mathf.PI * 2f);
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.gravityModifier = -0.01f;
            var em = ps.emission; em.rateOverTime = rate;
            var sh = ps.shape; sh.enabled = true; sh.shapeType = ParticleSystemShapeType.Box; sh.scale = size;
            var col = ps.colorOverLifetime; col.enabled = true; col.color = new ParticleSystem.MinMaxGradient(FadeGradient());
            var rol = ps.rotationOverLifetime; rol.enabled = true; rol.z = new ParticleSystem.MinMaxCurve(-0.3f, 0.3f);
            ps.Play();
        }

        static void MakeSplash(Transform parent, Vector3 pos, Vector3 size, Material mat)
        {
            var ps = NewSystem(parent, "Cascade Droplets", pos, mat, out _);
            var main = ps.main;
            main.loop = true; main.playOnAwake = true; main.prewarm = true;
            main.startLifetime = new ParticleSystem.MinMaxCurve(0.6f, 1.3f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(1.5f, 4f);
            main.startSize = new ParticleSystem.MinMaxCurve(0.03f, 0.08f);
            main.gravityModifier = 1f;
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            var em = ps.emission; em.rateOverTime = 60f;
            var sh = ps.shape; sh.enabled = true; sh.shapeType = ParticleSystemShapeType.Box; sh.scale = size;
            sh.rotation = new Vector3(-90, 0, 0);
            sh.randomDirectionAmount = 0.5f;
            ps.Play();
        }

        static PostProcessProfile BuildPostProfile()
        {
            string path = Gen + "/HousePostProcessing.asset";
            var existing = AssetDatabase.LoadAssetAtPath<PostProcessProfile>(path);
            if (existing != null) AssetDatabase.DeleteAsset(path);
            var profile = ScriptableObject.CreateInstance<PostProcessProfile>();
            AssetDatabase.CreateAsset(profile, path);

            var bloom = profile.AddSettings<Bloom>();
            bloom.enabled.Override(true);
            bloom.intensity.Override(1.35f);
            bloom.threshold.Override(1.05f);
            bloom.softKnee.Override(0.6f);
            bloom.diffusion.Override(7.5f);
            bloom.color.Override(new Color(1f, 0.97f, 0.92f));
            AssetDatabase.AddObjectToAsset(bloom, profile);

            var cg = profile.AddSettings<ColorGrading>();
            cg.enabled.Override(true);
            cg.gradingMode.Override(GradingMode.HighDefinitionRange);
            cg.tonemapper.Override(Tonemapper.ACES);
            cg.postExposure.Override(0.45f);
            cg.temperature.Override(-5f);
            cg.saturation.Override(8f);
            cg.contrast.Override(12f);
            cg.lift.Override(new Vector4(0.97f, 1.0f, 1.04f, -0.01f));
            cg.gain.Override(new Vector4(1.02f, 1.0f, 0.97f, 0f));
            AssetDatabase.AddObjectToAsset(cg, profile);

            EditorUtility.SetDirty(profile);
            AssetDatabase.SaveAssets();
            return profile;
        }

        static Color C(float r, float g, float b) => new Color(r, g, b);

        static void SetPalettes(HouseClock c)
        {
            c.skyTop = new[] { C(0.32f, 0.52f, 0.78f), C(0.22f, 0.45f, 0.80f), C(0.30f, 0.42f, 0.60f), C(0.42f, 0.50f, 0.62f) };
            c.skyHorizon = new[] { C(0.78f, 0.85f, 0.88f), C(0.75f, 0.85f, 0.92f), C(0.85f, 0.75f, 0.62f), C(0.80f, 0.84f, 0.88f) };
            c.sunColor = new[] { C(1.0f, 0.95f, 0.86f), C(1.0f, 0.93f, 0.80f), C(1.0f, 0.82f, 0.60f), C(0.90f, 0.92f, 1.0f) };
            c.fogColor = new[] { C(0.58f, 0.70f, 0.73f), C(0.56f, 0.72f, 0.77f), C(0.64f, 0.62f, 0.58f), C(0.70f, 0.76f, 0.82f) };
            c.waterShallow = new[] { C(0.22f, 0.78f, 0.74f), C(0.12f, 0.85f, 0.80f), C(0.20f, 0.62f, 0.58f), C(0.25f, 0.55f, 0.62f) };
            c.waterDeep = new[] { C(0.03f, 0.22f, 0.32f), C(0.02f, 0.25f, 0.38f), C(0.04f, 0.16f, 0.22f), C(0.04f, 0.12f, 0.20f) };
            c.ambientSky = new[] { C(0.50f, 0.60f, 0.70f), C(0.55f, 0.65f, 0.75f), C(0.48f, 0.50f, 0.55f), C(0.56f, 0.62f, 0.72f) };
            c.ambientEquator = new[] { C(0.40f, 0.45f, 0.45f), C(0.45f, 0.50f, 0.50f), C(0.46f, 0.42f, 0.36f), C(0.46f, 0.50f, 0.55f) };
            c.ambientGround = new[] { C(0.26f, 0.28f, 0.27f), C(0.30f, 0.30f, 0.28f), C(0.28f, 0.24f, 0.20f), C(0.32f, 0.34f, 0.38f) };
            c.fogDensity = new[] { 0.0065f, 0.005f, 0.0075f, 0.009f };
            c.sunMaxElevation = new[] { 52f, 68f, 40f, 26f };
            c.cloudCover = new[] { 0.45f, 0.25f, 0.6f, 0.75f };
            c.windVolume = new[] { 0.3f, 0.22f, 0.45f, 0.6f };
        }

        static void FrameSpawn(Layout L)
        {
            var sv = SceneView.lastActiveSceneView;
            if (sv == null) return;
            var rot = Quaternion.Euler(4f, L.spawn.r, 0);
            var eye = V(L.spawn.p) + Vector3.up * 1.65f;
            sv.LookAtDirect(eye + rot * Vector3.forward * 1.5f, rot, 1.5f);
            sv.Repaint();
        }
    }
}
