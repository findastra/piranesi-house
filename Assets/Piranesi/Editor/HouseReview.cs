// Piranesi > Review Shots: renders a set of fixed views of the built House to Review/Shots/*.jpg (a storm and a stair view
// too, previewed in the editor), so the build can be checked without walking round it.
// It also watches for two trigger files so the build can be run from outside the editor (no clicking needed):
//   Review/do_build -> refresh assets, wait for scripts to compile, Piranesi > Build House; result in Review/build_result.txt
//   Review/do_shots -> Review Shots; result in Review/shots_result.txt
// Errors and [Piranesi] messages logged during a build are written into the result file.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using Object = UnityEngine.Object;

namespace Piranesi.EditorTools
{
    [InitializeOnLoad]
    public static class HouseReview
    {
        const string Dir = "Review";
        const string RefreshKey = "Piranesi.TriggerRefreshed";
        static double next;
        static readonly List<string> log = new List<string>();
        static bool capturing;
        static DateTime started;

        static HouseReview()
        {
            EditorApplication.update -= Poll;
            EditorApplication.update += Poll;
            Application.logMessageReceived -= OnLog;
            Application.logMessageReceived += OnLog;
        }

        // ------------------------------------------------------------------ triggers
        static void Poll()
        {
            if (EditorApplication.timeSinceStartup < next) return;
            next = EditorApplication.timeSinceStartup + 2.0;
            if (EditorApplication.isPlayingOrWillChangePlaymode) return;
            bool build = File.Exists(Dir + "/do_build"), shots = File.Exists(Dir + "/do_shots"), props = File.Exists(Dir + "/do_props");
            if (!build && !shots && !props) return;
            if (SessionState.GetInt(RefreshKey, 0) == 0)
            {
                SessionState.SetInt(RefreshKey, 1);
                File.WriteAllText(Dir + "/trigger_seen.txt", DateTime.Now.ToString("s") + (build ? " build" : " shots"));
                AssetDatabase.Refresh();
                return;
            }
            if (EditorApplication.isCompiling || EditorApplication.isUpdating) return;
            SessionState.SetInt(RefreshKey, 0);
            if (build)
            {
                File.Delete(Dir + "/do_build");
                try { HouseBuilder.BuildHouse(); }
                catch (Exception e) { BuildFinished("failed: " + e.Message); }
            }
            else if (shots)
            {
                File.Delete(Dir + "/do_shots");
                try { Shots(); File.WriteAllText(Dir + "/shots_result.txt", "ok " + DateTime.Now.ToString("s")); }
                catch (Exception e) { File.WriteAllText(Dir + "/shots_result.txt", "failed: " + e); }
            }
            else
            {
                var lines = File.ReadAllLines(Dir + "/do_props");
                File.Delete(Dir + "/do_props");
                try { Props(lines); File.WriteAllText(Dir + "/props_result.txt", "ok " + DateTime.Now.ToString("s")); }
                catch (Exception e) { File.WriteAllText(Dir + "/props_result.txt", "failed: " + e); }
            }
        }

        // close-ups: each line of Review/do_props is either "name part [| distance x]" (frames the first object whose name
        // contains it, from a three-quarter view) or "@ex,ey,ez > lx,ly,lz [| tide]" (an explicit camera); rendered to Shots/P_nn_*.jpg
        static void Props(string[] lines)
        {
            Directory.CreateDirectory(Dir + "/Shots");
            var go = new GameObject("Review camera") { hideFlags = HideFlags.HideAndDontSave };
            var cam = go.AddComponent<Camera>();
            cam.nearClipPlane = 0.02f; cam.farClipPlane = 4000f; cam.allowHDR = false; cam.allowMSAA = true;
            var all = Object.FindObjectsOfType<Renderer>();
            try
            {
                HousePreviewWindow.ApplyState(0.32f, 1.3f, 0.25f, false);
                int k = 0;
                foreach (var raw in lines)
                {
                    var line = raw.Trim(); if (line.Length == 0 || line.StartsWith("#")) continue;
                    k++;
                    var parts = line.Split('|'); var key = parts[0].Trim();
                    float opt = parts.Length > 1 && float.TryParse(parts[1].Trim(), System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var o) ? o : -1f;
                    string safe = new string(key.Where(char.IsLetterOrDigit).Take(28).ToArray());
                    if (key.StartsWith("@"))
                    {
                        var ab = key.Substring(1).Split('>');
                        Vector3 P(string s) { var f = s.Split(',').Select(x => float.Parse(x.Trim(), System.Globalization.CultureInfo.InvariantCulture)).ToArray(); return new Vector3(f[0], f[1], f[2]); }
                        if (opt > -1f) HousePreviewWindow.ApplyState(0.32f, 1.3f, opt, false);
                        Render(cam, $"P_{k:00}_cam", P(ab[0]), P(ab[1]), 1280, 800, 55f);
                        if (opt > -1f) HousePreviewWindow.ApplyState(0.32f, 1.3f, 0.25f, false);
                        continue;
                    }
                    bool Has(Transform t) => t != null && t.name.IndexOf(key, StringComparison.OrdinalIgnoreCase) >= 0;
                    var r = all.FirstOrDefault(x => x != null && x.enabled && x.gameObject.activeInHierarchy && (Has(x.transform) || Has(x.transform.parent)));
                    if (r == null) { File.AppendAllText(Dir + "/props_result.txt", "not found: " + key + "\n"); continue; }
                    var b = r.bounds;
                    foreach (var c in r.GetComponentsInChildren<Renderer>()) b.Encapsulate(c.bounds);
                    float rad = Mathf.Max(b.extents.magnitude, 0.08f) * (opt > 0 ? opt : 1f);
                    var dir = (r.transform.forward * 0.8f + r.transform.right * 0.6f + Vector3.up * 0.55f).normalized;
                    Render(cam, $"P_{k:00}_{safe}", b.center + dir * rad * 2.6f, b.center, 1280, 800, 40f);
                }
            }
            finally
            {
                Object.DestroyImmediate(go);
                HousePreviewWindow.ApplyState(HousePreviewWindow.Day, HousePreviewWindow.Season, HousePreviewWindow.Tide, false);
            }
        }

        public static void BuildStarted()
        {
            log.Clear(); capturing = true; started = DateTime.Now;
        }

        public static void BuildFinished(string status)
        {
            capturing = false;
            Directory.CreateDirectory(Dir);
            File.WriteAllText(Dir + "/build_result.txt", status + "\n" + DateTime.Now.ToString("s") + " (" + (DateTime.Now - started).TotalSeconds.ToString("0") + " s)\n" +
                                                           string.Join("\n", log.Take(400)));
        }

        static void OnLog(string msg, string stack, LogType type)
        {
            bool compileError = type == LogType.Error && msg.Contains("error CS");
            if (compileError)
            {
                try { Directory.CreateDirectory(Dir); File.AppendAllText(Dir + "/compile_errors.txt", DateTime.Now.ToString("s") + " " + msg + "\n"); } catch { }
            }
            if (!capturing) return;
            if (type == LogType.Error || type == LogType.Exception || type == LogType.Assert || msg.StartsWith("[Piranesi]") ||
                (type == LogType.Warning && msg.Contains("Piranesi")))
                log.Add(type + ": " + msg + (type == LogType.Exception ? "\n" + stack : ""));
        }

        // ------------------------------------------------------------------ shots
        [MenuItem("Piranesi/Review Shots", priority = 30)]
        public static void Shots()
        {
            Directory.CreateDirectory(Dir + "/Shots");
            var go = new GameObject("Review camera") { hideFlags = HideFlags.HideAndDontSave };
            var cam = go.AddComponent<Camera>();
            cam.nearClipPlane = 0.1f; cam.farClipPlane = 4000f; cam.fieldOfView = 62f; cam.allowHDR = false; cam.allowMSAA = true;
            try
            {
                HousePreviewWindow.ApplyState(0.32f, 1.3f, 0.25f, false);
                Render(cam, "01_spawn", new Vector3(199.5f, 1.65f, 60f), new Vector3(185f, 3f, 60f));
                Render(cam, "02_camp", new Vector3(205.5f, 4.5f, 66f), new Vector3(197.5f, 0.8f, 56.5f));
                Render(cam, "03_prize_shelf", new Vector3(199.3f, 1.7f, 54.6f), new Vector3(199.3f, 0.8f, 50.6f));
                Render(cam, "04_ruin_isle", new Vector3(246f, 9f, 34f), new Vector3(290f, 2f, 60f));
                Render(cam, "05_lived_in_hall", new Vector3(301.5f, 3.8f, 60f), new Vector3(330f, 3.2f, 60f));   // hall floor is at 2.1
                Render(cam, "06_colossus", new Vector3(7f, 2.5f, -6f), new Vector3(0f, 12f, 0f));
                Render(cam, "07_sea_gate_hall", new Vector3(-172f, 1.7f, -60f), new Vector3(-205f, 2f, -60f));
                Render(cam, "08_castellum_tubes", new Vector3(29f, 30f, 23f), new Vector3(31.5f, 26.5f, 31f));
                Render(cam, "09_drowned_halls", new Vector3(-405f, 0.8f, -60f), new Vector3(-440f, 1f, -60f));
                Render(cam, "10_minotaurs", new Vector3(288.5f, 1.7f, -288.5f), new Vector3(306f, 1.6f, -306f));
                bool fog0 = RenderSettings.fog; RenderSettings.fog = false;            // the overviews: no haze
                Render(cam, "11_aerial", new Vector3(0f, 520f, -620f), Vector3.zero, 1600, 900, 55f);
                cam.orthographic = true; cam.orthographicSize = 700f;
                Render(cam, "12_map", new Vector3(0f, 1500f, 0.01f), Vector3.zero, 1400, 1400);
                cam.orthographic = false;
                RenderSettings.fog = fog0;
                var bed = Object.FindObjectsOfType<Transform>().FirstOrDefault(t => t.name.StartsWith("Window daybed") || t.name.StartsWith("Marble daybed (window"));
                HousePreviewWindow.ApplyState(0.32f, 1.3f, 0.85f, false);
                if (bed != null)
                {
                    var f = bed.forward; f.y = 0; f.Normalize();                        // the bed sits out in the window bay
                    var br = bed.GetComponent<Renderer>(); var bc = br != null ? br.bounds.center : bed.position + f * 10f;
                    Render(cam, "13_high_tide_window", bc - f * 4.2f + Vector3.up * 1.2f, bc + Vector3.up * 0.3f);
                }
                HousePreviewWindow.ApplyState(0.82f, 1.3f, 0.25f, false);
                Render(cam, "14_night_painted_poles", new Vector3(-300f, 7f, -45f), new Vector3(-420f, 2f, -60f));
                Render(cam, "15_night_gate_neon", new Vector3(-174f, 2.5f, -54f), new Vector3(-200f, 1.5f, -62f));
                HousePreviewWindow.ApplyState(0.32f, 1.3f, 0.25f, false);
                StormShots(cam);
            }
            finally
            {
                Object.DestroyImmediate(go);
                HousePreviewWindow.ApplyState(HousePreviewWindow.Day, HousePreviewWindow.Season, HousePreviewWindow.Tide, false);
            }
            Debug.Log("[Piranesi] Review shots written to " + Path.GetFullPath(Dir + "/Shots"));
        }

        // the stair is only built at runtime (Udon); preview it here: open dome, pole, turns, storm sky, then the stars and the booth
        static void StormShots(Camera cam)
        {
            var storm = Object.FindObjectOfType<HouseStorm>();
            if (storm == null || storm.stair == null || storm.turns == null) return;
            var savedSky = RenderSettings.skybox; bool savedFog = RenderSettings.fog; var savedAmb = RenderSettings.ambientMode;
            try
            {
                storm.stair.SetActive(true);
                foreach (var g in storm.domeClosed ?? new GameObject[0]) if (g != null) g.SetActive(false);
                foreach (var g in storm.domeOpen ?? new GameObject[0]) if (g != null) g.SetActive(true);
                foreach (var g in storm.hideInStorm ?? new GameObject[0]) if (g != null) g.SetActive(false);
                if (storm.pole != null) storm.pole.localScale = Vector3.one;
                for (int i = 0; i < storm.turns.Length; i++) { storm.turns[i].gameObject.SetActive(true); storm.turns[i].localPosition = new Vector3(0, storm.baseY + i * storm.pitch, 0); }
                Shader.SetGlobalFloat("_UdonStorm", 1f);
                RenderSettings.skybox = storm.stormSky;
                Render(cam, "16_storm_stair_from_hall", new Vector3(7f, 3f, -7f), new Vector3(0f, 30f, 0f));
                Render(cam, "17_stair_from_palm", new Vector3(3.6f, 15.6f, -2.2f), new Vector3(-1f, 40f, 2f));
                Render(cam, "18_storm_house_from_stair", new Vector3(4f, 70f, 4f), new Vector3(120f, 0f, 120f));
                Shader.SetGlobalFloat("_UdonStorm", 0f);
                int top = storm.topTurns;
                for (int i = 0; i < storm.turns.Length; i++)
                {
                    int k = top - storm.turns.Length + i;
                    storm.turns[i].localPosition = new Vector3(0, storm.baseY + k * storm.pitch, 0);
                }
                RenderSettings.skybox = storm.starsSky; RenderSettings.fog = false;
                RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Flat; RenderSettings.ambientLight = new Color(0.3f, 0.26f, 0.45f);
                if (storm.booth != null)
                {
                    var b = storm.booth;
                    Render(cam, "19_phone_booth_stars", b.position + b.forward * 3.2f + Vector3.up * 1.7f - b.right * 0.6f, b.position + Vector3.up * 1.3f);
                    Render(cam, "20_top_of_the_stair", b.position + b.forward * 9f + Vector3.up * 5f, b.position);
                }
            }
            finally
            {
                Shader.SetGlobalFloat("_UdonStorm", 0f);
                RenderSettings.skybox = savedSky; RenderSettings.fog = savedFog; RenderSettings.ambientMode = savedAmb;
                storm.stair.SetActive(false);
                foreach (var g in storm.domeClosed ?? new GameObject[0]) if (g != null) g.SetActive(true);
                foreach (var g in storm.domeOpen ?? new GameObject[0]) if (g != null) g.SetActive(false);
                foreach (var g in storm.hideInStorm ?? new GameObject[0]) if (g != null) g.SetActive(true);
                if (storm.pole != null) storm.pole.localScale = new Vector3(1f, 0.001f, 1f);
            }
        }

        static void Render(Camera cam, string name, Vector3 eye, Vector3 look, int w = 1600, int h = 900, float fov = 62f)
        {
            cam.fieldOfView = fov;
            cam.transform.position = eye;
            var dir = look - eye;
            cam.transform.rotation = Quaternion.LookRotation(dir.sqrMagnitude > 1e-6f ? dir : Vector3.forward, Mathf.Abs(dir.normalized.y) > 0.99f ? Vector3.forward : Vector3.up);
            var rt = RenderTexture.GetTemporary(w, h, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB, 4);
            var prev = RenderTexture.active;
            try
            {
                cam.targetTexture = rt;
                cam.Render();
                RenderTexture.active = rt;
                var tex = new Texture2D(w, h, TextureFormat.RGB24, false);
                tex.ReadPixels(new Rect(0, 0, w, h), 0, 0); tex.Apply();
                File.WriteAllBytes($"{Dir}/Shots/{name}.jpg", tex.EncodeToJPG(88));
                Object.DestroyImmediate(tex);
            }
            finally
            {
                RenderTexture.active = prev; cam.targetTexture = null; RenderTexture.ReleaseTemporary(rt);
            }
        }
    }
}
