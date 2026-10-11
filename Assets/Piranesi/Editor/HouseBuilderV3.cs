// v3 additions to Piranesi > Build House (the 7 x 7 Cross of the Four Winds):
//   the colour key (one neon material per road), the six roof floater tubes, the Climb vine, the Joining of the Three
//   Tides, the offering in the Alcove of the Dead, the Far Hall Quests (6 / 6), the five dead ends and the Stormscape:
//   Astra's Infinite Pole, the Infinite Spiral, the landing among the stars with Astra's phone booth, and the End Show
//   (meteors, the hyperspace dive back down into the Colossus' palm, the blackout, home to the spawn camp).
// The storm, stair, booth and stair materials are Astra's own (findastra/astras-infinite-pole, theatre branch):
// the turn and ramp meshes follow ClaudeWiderStairs.cs and the booth follows ClaudeRound3g.cs BuildBooth.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UdonSharpEditor;
using VRC.SDK3.Components;
using Object = UnityEngine.Object;

namespace Piranesi.EditorTools
{
    public static partial class HouseBuilder
    {
        // ------------------------------------------------------------------ layout (v3)
        [Serializable] class LPalette { public string name; public float[] color; }
        [Serializable] class LTeleport { public string name, text; public float[] p, size, target, near; public float targetR, nearR; }
        [Serializable] class LRide { public string name, text, family; public float[] path, exit, color; public float exitR; }
        [Serializable] class LDeadEnd { public string name; public float[] p, size, burst; }
        [Serializable] class LQuest { public int index; public string name, text, thread; public float[] p, size, candle; public bool offering; }
        [Serializable] class LFlood { public string name; public float low, high, period, rise, hold; public float[] sound; }
        [Serializable] class LOffering { public string name, text; public float[] p, size; public string[] lilies; }
        [Serializable] class LQuestUi { public string[] counts, shelf; public string thread, candle; }
        [Serializable] class LCalm { public string name; public float[] c, h; public float r, fall; }
        [Serializable] class LPlatform { public string name; public float[] p, size; public float r; }
        [Serializable] class LStorm
        {
            public float[] axis, pole, white, stars, blackout;
            public float @base, theta0, pitch, rise, inner, outer, grow, growDelay, meteors, diveTime;
            public int steps, turns, topTurns;
            public string rosette;
            public string[] tally, openDome, openMeshes, hideInStorm;
        }

        static readonly Dictionary<string, List<GameObject>> named = new Dictionary<string, List<GameObject>>();
        static readonly Dictionary<string, Material> neonMats = new Dictionary<string, Material>();
        static Layout v3data;

        static Layout V3Data()
        {
            if (v3data == null) v3data = JsonUtility.FromJson<Layout>(File.ReadAllText(Root + "/Data/HouseLayout.json"));
            return v3data;
        }

        static void Register(GameObject go)
        {
            if (!named.TryGetValue(go.name, out var l)) { l = new List<GameObject>(); named[go.name] = l; }
            l.Add(go);
        }
        static GameObject Named(string n) => !string.IsNullOrEmpty(n) && named.TryGetValue(n, out var l) && l.Count > 0 ? l[0] : null;
        static GameObject[] AllNamed(string n) => !string.IsNullOrEmpty(n) && named.TryGetValue(n, out var l) ? l.ToArray() : new GameObject[0];
        static AudioClip Clip(string n) => AssetDatabase.LoadAssetAtPath<AudioClip>($"{Root}/Audio/{n}.wav");
        static Vector3[] Pts(float[] flat)
        {
            var pts = new Vector3[flat.Length / 3];
            for (int i = 0; i < pts.Length; i++) pts[i] = new Vector3(flat[i * 3], flat[i * 3 + 1], flat[i * 3 + 2]);
            return pts;
        }
        static void Proxy(UdonSharp.UdonSharpBehaviour b) => UdonSharpEditorUtility.CopyProxyToUdon(b);

        // ------------------------------------------------------------------ materials (v3)
        static void BuildV3Materials(Dictionary<string, Material> d)
        {
            v3data = null;
            neonMats.Clear();
            var pal = V3Data().palette ?? new LPalette[0];
            foreach (var p in pal)
            {
                var c = Col(p.color);
                neonMats[p.name] = Mat("M_Neon_" + Safe(p.name), "Piranesi/Neon", m =>
                {
                    m.SetColor("_Color", c); m.SetFloat("_Glow", 2.2f); m.SetFloat("_Glitter", 2f); m.SetFloat("_Pulse", 0.2f); m.enableInstancing = true;
                });
            }
            d["Neon"] = neonMats.Values.FirstOrDefault() ?? d["Gold"];
            d["BoxRed"] = Mat("M_BoxRed", "Standard", m =>
            {
                m.SetColor("_Color", new Color(0.6f, 0.05f, 0.06f)); m.SetFloat("_Metallic", 0.55f); m.SetFloat("_Glossiness", 0.62f); m.enableInstancing = true;
            });
            d["AstraPole"] = Mat("M_AstraPole", "Piranesi/AstraPole", m => { m.enableInstancing = true; });
            d["Stair"] = Mat("M_AstraStair", "Astra/Prismatic Stair", m =>
            {
                m.SetColor("_Color", new Color(1f, 0.42f, 0.74f)); m.SetFloat("_Opacity", 0.3f); m.SetFloat("_Glitter", 2.5f); m.enableInstancing = true;
            });
            d["Landing"] = Mat("M_AstraLanding", "Astra/Glitter Cloud", m =>
            {
                m.SetColor("_Top", new Color(1f, 0.9f, 1f)); m.SetColor("_Bottom", new Color(0.95f, 0.7f, 0.9f)); m.SetColor("_Rim", new Color(1.6f, 1f, 1.5f));
                m.SetFloat("_Glitter", 2.4f); m.SetFloat("_Pastel", 0.25f); m.enableInstancing = true;
            });
            d["BoothBody"] = Glitter("M_BoothBody", new Color(1f, 0.3f, 0.47f), new Color(0.78f, 0.16f, 0.36f), new Color(1.8f, 0.5f, 1.1f), 0.8f);
            d["BoothSign"] = Glitter("M_BoothSign", new Color(2.6f, 1.0f, 2.2f), new Color(2.3f, 0.8f, 2.0f), new Color(1.5f, 0.8f, 1.4f), 0.3f);
            d["BoothPhone"] = Glitter("M_BoothPhone", new Color(0.34f, 0.3f, 0.4f), new Color(0.16f, 0.13f, 0.2f), new Color(1.2f, 0.6f, 1.1f), 0.5f);
            d["BoothGlass"] = Mat("M_BoothGlass", "Astra/Prismatic Stair", m =>
            {
                m.SetColor("_Color", new Color(1f, 0.55f, 0.75f)); m.SetFloat("_Opacity", 0.18f); m.SetFloat("_Glitter", 0.6f); m.SetFloat("_Rainbow", 0f); m.SetFloat("_Hue", 0f);
                m.enableInstancing = true;
            });
            d["StormSky"] = Mat("M_StormSky", "Astra/Storm Sky", m => { });
            d["StarsSky"] = Mat("M_StarsSky", "Piranesi/AstraSky", m => { });
            d["Rain"] = Mat("M_StormRain", "Astra/Storm Rain", m => { });
            d["Bolt"] = Mat("M_StormBolt", "Astra/Storm Bolt", m => { m.SetTexture("_MainTex", Tex("StormBolt")); });
            d["Warp"] = Mat("M_Warp", "Piranesi/Warp", m =>
            {
                for (int i = 0; i < 6 && i < pal.Length; i++) m.SetColor("_C" + i, Col(pal[i].color));
                m.SetFloat("_Amount", 0f); m.SetFloat("_Rush", 1f);
            });
            d["Blackout"] = Mat("M_Blackout", "Piranesi/Blackout", m => { m.SetFloat("_Alpha", 0f); });
            d["P_Glint"] = ParticleMat("M_P_Glint", 0, new Color(1f, 0.93f, 0.78f, 0.9f), true, 0f);
            d["P_Meteor"] = ParticleMat("M_P_Meteor", 0, new Color(0.85f, 0.92f, 1f, 1f), true, 0f);
            d["P_Cloud"] = ParticleMat("M_P_Cloud", 0, new Color(0.95f, 0.97f, 1f, 0.16f), false, 0.9f);

            // the sea: calm inside the whole House (its half size from the layout), and in the lee of every building out on
            // the water, so the swell doesn't come up through the floors of the far halls, the wings, the isle halls or the camp
            if (d.TryGetValue("Ocean", out var ocean))
            {
                var hb = V3Data().house_bounds;
                if (hb != null && hb.Length == 4) ocean.SetFloat("_HouseHalf", Mathf.Max(Mathf.Abs(hb[0]), Mathf.Abs(hb[1]), hb[2], hb[3]));
                var calm = V3Data().calm ?? new LCalm[0];
                for (int i = 0; i < 24; i++)
                {
                    if (i < calm.Length && calm[i].c != null && calm[i].h != null)
                    {
                        float a = calm[i].r * Mathf.Deg2Rad;
                        ocean.SetVector("_CalmA" + i, new Vector4(calm[i].c[0], calm[i].c[1], Mathf.Cos(a), Mathf.Sin(a)));
                        ocean.SetVector("_CalmB" + i, new Vector4(calm[i].h[0], calm[i].h[1], calm[i].fall > 0 ? calm[i].fall : 25f, 0f));
                    }
                    else { ocean.SetVector("_CalmA" + i, new Vector4(0, 0, 1, 0)); ocean.SetVector("_CalmB" + i, Vector4.zero); }
                }
                if (calm.Length > 24) Debug.LogWarning($"[Piranesi] {calm.Length} calm zones in the layout; the sea shader takes 24");
                EditorUtility.SetDirty(ocean);
            }
        }

        static Material Glitter(string name, Color top, Color bottom, Color rim, float glitter) => Mat(name, "Astra/Glitter Cloud", m =>
        {
            m.SetColor("_Top", top); m.SetColor("_Bottom", bottom); m.SetColor("_Rim", rim); m.SetFloat("_Glitter", glitter); m.SetFloat("_Pastel", 0f);
            m.enableInstancing = true;
        });

        // ------------------------------------------------------------------ meshes (v3): the spiral, the landings, the tunnel, the booth
        static void BuildV3Meshes(Dictionary<string, MeshEntry> dict)
        {
            v3data = null;
            var S = V3Data().storm;
            float inner = S != null && S.inner > 0 ? S.inner : 2.8f, outer = S != null && S.outer > 0 ? S.outer : 5.8f;
            int steps = S != null && S.steps > 0 ? S.steps : 40;
            float rise = S != null && S.rise > 0 ? S.rise : 0.16f, a0 = S != null ? S.theta0 : 0f;
            dict["__StairTurn"] = new MeshEntry { mesh = SaveMesh(MakeTurn(inner, outer, steps, rise, a0, false), "__StairTurn"), subs = new[] { "Stair" } };
            dict["__StairRamp"] = new MeshEntry { mesh = SaveMesh(MakeTurn(inner, outer, steps, rise, a0, true), "__StairRamp"), subs = new[] { "Stair" } };
            // the stair simply ends on one broad platform step (no landing ring): it carries on from the last tread, round
            // ~75 degrees of the spiral and a little wider than the treads, and Astra's phone booth stands on it
            dict["__Landing"] = new MeshEntry { mesh = SaveMesh(MakeSector(inner - 0.2f, outer + 0.8f, a0, a0 + 1.3f, 0.35f, 20), "__Landing"),
                                                subs = new[] { "Landing" } };
            dict["__Wedge"] = new MeshEntry { mesh = SaveMesh(MakeSector(1.4f, outer, a0 - 0.5f, a0 + 0.04f, 0.2f, 12), "__Wedge"), subs = new[] { "Landing" } };
            dict["__WarpTube"] = new MeshEntry { mesh = SaveMesh(MakeTube(6f, 90f, 48), "__WarpTube"), subs = new[] { "Warp" } };
            var booth = MakeBoothMeshes();
            for (int i = 0; i < booth.Length; i++) dict["__Booth" + i] = new MeshEntry { mesh = SaveMesh(booth[i], "__Booth" + i), subs = new[] { "Booth" } };
        }

        // one turn of Astra's Infinite Spiral (ClaudeWiderStairs.Rebuild): 'steps' treads of three sub-quads each, rising 'rise'
        // per tread, from radius inner to outer, starting at angle a0; ramp = the smooth walkable collider under them
        static Mesh MakeTurn(float inner, float outer, int steps, float rise, float a0, bool ramp)
        {
            var v = new List<Vector3>(); var t = new List<int>(); var uv = new List<Vector2>();
            void Quad(Vector3 a, Vector3 b, Vector3 c, Vector3 d)
            {
                int k = v.Count; v.Add(a); v.Add(b); v.Add(c); v.Add(d);
                uv.Add(new Vector2(0, 0)); uv.Add(new Vector2(0, 1)); uv.Add(new Vector2(1, 1)); uv.Add(new Vector2(1, 0));
                t.Add(k); t.Add(k + 1); t.Add(k + 2); t.Add(k); t.Add(k + 2); t.Add(k + 3);
            }
            Vector3 P(float r, float a, float y) => new Vector3(Mathf.Cos(a) * r, y, Mathf.Sin(a) * r);
            for (int step = 0; step < steps; step++)
                for (int j = 0; j < 3; j++)
                {
                    float a = a0 + (step + j / 3f) * Mathf.PI * 2f / steps, b = a0 + (step + (j + 1) / 3f) * Mathf.PI * 2f / steps;
                    float y = (step + 1) * rise, ya = ramp ? (step + j / 3f) * rise : y, yb = ramp ? (step + (j + 1) / 3f) * rise : y;
                    var ia = P(inner, a, ya); var ib = P(inner, b, yb); var ob = P(outer, b, yb); var oa = P(outer, a, ya);
                    Quad(ia, ib, ob, oa);
                    if (!ramp)
                    {
                        var down = Vector3.down * 0.065f;
                        Quad(oa + down, ob + down, ib + down, ia + down); Quad(ia + down, ib + down, ib, ia); Quad(oa, ob, ob + down, oa + down);
                        if (j == 0) Quad(ia, oa, oa + down, ia + down);
                        if (j == 2) Quad(ob, ib, ib + down, ob + down);
                    }
                }
            var m = new Mesh { indexFormat = IndexFormat.UInt32 };
            m.SetVertices(v); m.SetTriangles(t, 0); m.SetUVs(0, uv); m.RecalculateNormals(); m.RecalculateBounds();
            return m;
        }

        // a slab shaped like a ring sector (top at y = 0, 'thick' deep): the landing among the stars and the step off the palm
        static Mesh MakeSector(float r0, float r1, float a0, float a1, float thick, int seg)
        {
            var v = new List<Vector3>(); var t = new List<int>();
            void Tri(Vector3 a, Vector3 b, Vector3 c, Vector3 want)
            {
                if (Vector3.Dot(Vector3.Cross(b - a, c - a), want) < 0) { var x = b; b = c; c = x; }
                int k = v.Count; v.Add(a); v.Add(b); v.Add(c); t.Add(k); t.Add(k + 1); t.Add(k + 2);
            }
            Vector3 P(float r, float a, float y) => new Vector3(Mathf.Cos(a) * r, y, Mathf.Sin(a) * r);
            bool full = a1 - a0 >= Mathf.PI * 2f - 1e-4f;
            for (int i = 0; i < seg; i++)
            {
                float a = Mathf.Lerp(a0, a1, i / (float)seg), b = Mathf.Lerp(a0, a1, (i + 1) / (float)seg);
                Vector3 ia = P(r0, a, 0), ib = P(r0, b, 0), oa = P(r1, a, 0), ob = P(r1, b, 0), dn = Vector3.down * thick;
                Tri(ia, oa, ob, Vector3.up); Tri(ia, ob, ib, Vector3.up);
                Tri(ia + dn, oa + dn, ob + dn, Vector3.down); Tri(ia + dn, ob + dn, ib + dn, Vector3.down);
                var outN = P(1, (a + b) * 0.5f, 0);
                Tri(oa, oa + dn, ob + dn, outN); Tri(oa, ob + dn, ob, outN);
                Tri(ia, ia + dn, ib + dn, -outN); Tri(ia, ib + dn, ib, -outN);
            }
            if (!full)
            {
                foreach (var (a, sgn) in new[] { (a0, -1f), (a1, 1f) })
                {
                    Vector3 i0 = P(r0, a, 0), o0 = P(r1, a, 0), dn = Vector3.down * thick;
                    var n = new Vector3(-Mathf.Sin(a), 0, Mathf.Cos(a)) * sgn;
                    Tri(i0, o0, o0 + dn, n); Tri(i0, o0 + dn, i0 + dn, n);
                }
            }
            var m = new Mesh(); m.SetVertices(v); m.SetTriangles(t, 0); m.RecalculateNormals(); m.RecalculateBounds();
            return m;
        }

        static Mesh Combine(params Mesh[] parts)
        {
            var ci = parts.Select(p => new CombineInstance { mesh = p, transform = Matrix4x4.identity }).ToArray();
            var m = new Mesh { indexFormat = IndexFormat.UInt32 };
            m.CombineMeshes(ci, true, false);
            m.RecalculateBounds();
            foreach (var p in parts) Object.DestroyImmediate(p);
            return m;
        }

        // the hyperspace tunnel: an open tube round the falling player (uv.x round it, uv.y along it)
        static Mesh MakeTube(float r, float h, int seg)
        {
            var v = new List<Vector3>(); var uv = new List<Vector2>(); var t = new List<int>();
            for (int j = 0; j <= 1; j++)
                for (int i = 0; i <= seg; i++)
                {
                    float a = i * Mathf.PI * 2f / seg;
                    v.Add(new Vector3(Mathf.Cos(a) * r, (j - 0.5f) * h, Mathf.Sin(a) * r)); uv.Add(new Vector2(i / (float)seg, j));
                }
            for (int i = 0; i < seg; i++)
            {
                int a = i, b = i + 1, c = seg + 1 + i, d = seg + 2 + i;
                t.AddRange(new[] { a, c, b, b, c, d });
            }
            var m = new Mesh(); m.SetVertices(v); m.SetUVs(0, uv); m.SetTriangles(t, 0); m.RecalculateNormals();
            m.bounds = new Bounds(Vector3.zero, new Vector3(r * 2 + 2, h + 2, r * 2 + 2));
            return m;
        }

        // ---------- Astra's phone booth (ClaudeRound3g.BuildBooth): 4 meshes, one per material (body, sign glow, glass, payphone)
        class Parts { public List<Vector3> v = new List<Vector3>(); public List<Vector3> n = new List<Vector3>(); public List<int> t = new List<int>(); }
        static void Box(Parts p, Vector3 c, Vector3 size, Quaternion rot, Vector3 pivot)
        {
            var h = size / 2;
            Vector3[] dirs = { Vector3.right, Vector3.left, Vector3.up, Vector3.down, Vector3.forward, Vector3.back };
            foreach (var d in dirs)
            {
                Vector3 a = Mathf.Abs(d.y) > 0.5f ? Vector3.right : Vector3.up, b = Vector3.Cross(d, a);
                int k = p.v.Count;
                foreach (var (sa, sb) in new[] { (-1, -1), (-1, 1), (1, 1), (1, -1) })
                {
                    var local = Vector3.Scale(d + a * sa + b * sb, h);
                    p.v.Add(pivot + rot * (c - pivot + local)); p.n.Add(rot * d);
                }
                p.t.AddRange(new[] { k, k + 2, k + 1, k, k + 3, k + 2 });
            }
        }
        static void Box(Parts p, Vector3 c, Vector3 size) => Box(p, c, size, Quaternion.identity, Vector3.zero);
        static Vector3 AbsV(Vector3 v) => new Vector3(Mathf.Abs(v.x), Mathf.Abs(v.y), Mathf.Abs(v.z));
        static void Append(Parts into, Parts from, Quaternion rot, Vector3 offset)
        {
            int k = into.v.Count;
            foreach (var x in from.v) into.v.Add(rot * x + offset);
            foreach (var x in from.n) into.n.Add(rot * x);
            foreach (var i in from.t) into.t.Add(k + i);
        }
        static void Coil(Parts p, Vector3 top, float coilR, float wireR, float length, int turns)
        {
            int steps = turns * 12, sides = 5; int k0 = p.v.Count;
            for (int s = 0; s <= steps; s++)
            {
                float tt = s / (float)steps, a = tt * turns * Mathf.PI * 2;
                var c = top + new Vector3(Mathf.Cos(a) * coilR, -tt * length, Mathf.Sin(a) * coilR);
                var tangent = new Vector3(-Mathf.Sin(a) * coilR * turns * Mathf.PI * 2, -length, Mathf.Cos(a) * coilR * turns * Mathf.PI * 2).normalized;
                var nrm = Vector3.Cross(tangent, Vector3.up).normalized; var bin = Vector3.Cross(tangent, nrm);
                for (int j = 0; j < sides; j++) { float b = j * Mathf.PI * 2 / sides; var d = nrm * Mathf.Cos(b) + bin * Mathf.Sin(b); p.v.Add(c + d * wireR); p.n.Add(d); }
            }
            for (int s = 0; s < steps; s++)
                for (int j = 0; j < sides; j++)
                {
                    int a0 = k0 + s * sides + j, a1 = k0 + s * sides + (j + 1) % sides, b0 = a0 + sides, b1 = a1 + sides;
                    p.t.AddRange(new[] { a0, b0, a1, a1, b0, b1, a0, a1, b0, a1, b1, b0 });
                }
        }
        static Mesh[] MakeBoothMeshes()
        {
            Parts body = new Parts(), sign = new Parts(), glass = new Parts(), phone = new Parts();
            const float W = 1.3f, H = 2.55f, post = 0.12f, half = W / 2 - post / 2;
            foreach (var x in new[] { -half, half }) foreach (var z in new[] { -half, half }) Box(body, new Vector3(x, H / 2, z), new Vector3(post, H, post));
            Box(body, new Vector3(0, H + 0.06f, 0), new Vector3(W + 0.12f, 0.12f, W + 0.12f));
            Box(body, new Vector3(0, H + 0.16f, 0), new Vector3(W - 0.1f, 0.08f, W - 0.1f));
            for (int side = 0; side < 4; side++)
            {
                var rot = Quaternion.Euler(0, side * 90, 0);
                Box(body, rot * new Vector3(0, H - 0.12f, W / 2 - 0.03f), AbsV(rot * new Vector3(W, 0.2f, 0.06f)));
                foreach (var x in new[] { -0.28f, 0.28f }) Box(sign, rot * new Vector3(x, H - 0.12f, W / 2 + 0.005f), AbsV(rot * new Vector3(0.46f, 0.1f, 0.02f)));
            }
            float paneTop = H - 0.24f, paneBottom = 0.3f;
            void Wall(Parts bodyP, Parts glassP, Quaternion rot, Vector3 pivot, float width)
            {
                Box(glassP, new Vector3(0, (paneTop + paneBottom) / 2, 0), new Vector3(width, paneTop - paneBottom, 0.015f), rot, pivot);
                Box(bodyP, new Vector3(0, paneBottom / 2 + 0.02f, 0), new Vector3(width, paneBottom, 0.05f), rot, pivot);
                for (float y = paneBottom + 0.32f; y < paneTop - 0.1f; y += 0.32f) Box(bodyP, new Vector3(0, y, 0), new Vector3(width, 0.035f, 0.04f), rot, pivot);
                Box(bodyP, new Vector3(0, (paneTop + paneBottom) / 2, 0), new Vector3(0.035f, paneTop - paneBottom, 0.04f), rot, pivot);
            }
            float inner = W - 2 * post;
            foreach (var side in new[] { 90, 180, 270 })
            {
                var rot = Quaternion.Euler(0, side, 0);
                Parts b2 = new Parts(), g2 = new Parts(); Wall(b2, g2, Quaternion.identity, Vector3.zero, inner);
                Append(body, b2, rot, rot * new Vector3(0, 0, W / 2 - 0.03f)); Append(glass, g2, rot, rot * new Vector3(0, 0, W / 2 - 0.03f));
            }
            {
                Parts b2 = new Parts(), g2 = new Parts(); Wall(b2, g2, Quaternion.identity, Vector3.zero, inner);
                var hinge = new Vector3(-inner / 2, 0, 0);
                var swing = Quaternion.Euler(0, -105, 0);
                Parts b3 = new Parts(), g3 = new Parts();
                Append(b3, b2, Quaternion.identity, -hinge); Append(g3, g2, Quaternion.identity, -hinge);
                Append(body, b3, swing, new Vector3(-inner / 2, 0, W / 2 - 0.03f)); Append(glass, g3, swing, new Vector3(-inner / 2, 0, W / 2 - 0.03f));
            }
            var back = new Vector3(0, 0, -(W / 2 - 0.03f) + 0.1f);
            Box(phone, back + new Vector3(0.1f, 1.38f, 0), new Vector3(0.3f, 0.48f, 0.12f));
            Box(phone, back + new Vector3(0.1f, 1.72f, 0.01f), new Vector3(0.16f, 0.16f, 0.1f));
            Box(sign, back + new Vector3(0.12f, 1.4f, 0.065f), new Vector3(0.12f, 0.16f, 0.01f));
            Box(phone, back + new Vector3(-0.11f, 1.44f, 0.04f), new Vector3(0.06f, 0.28f, 0.07f));
            Coil(phone, back + new Vector3(-0.11f, 1.29f, 0.05f), 0.028f, 0.006f, 0.55f, 16);
            Box(body, new Vector3(0, 0.02f, 0), new Vector3(W, 0.04f, W));
            var parts = new[] { body, sign, glass, phone };
            var meshes = new Mesh[4];
            for (int i = 0; i < 4; i++)
            {
                var m = new Mesh(); m.SetVertices(parts[i].v); m.SetNormals(parts[i].n); m.SetTriangles(parts[i].t, 0); m.RecalculateBounds();
                meshes[i] = m;
            }
            return meshes;
        }
        static readonly string[] BoothNames = { "Booth body", "Booth sign glow", "Booth glass", "Booth payphone" };
        static readonly string[] BoothMats = { "BoothBody", "BoothSign", "BoothGlass", "BoothPhone" };

        // ------------------------------------------------------------------ particles (v3)
        static void MakeV3Emitter(Transform parent, string kind, Vector3 pos, Vector3 size, float fall, float rot, Dictionary<string, Material> mats)
        {
            switch (kind)
            {
                case "glint":          // a gentle glitter round a prize, the egg, the hive
                    MakeSparkle(parent, pos, size, mats["P_Sparkle"]);
                    break;
                case "clouds":         // the cloud drifting through the Upper Halls
                    MakeMist(parent, "Cloud drifting through the hall", pos, size, mats["P_Cloud"], 3f, 6f);
                    break;
                case "jar":            // the cloud in the jar
                    MakeMist(parent, "Cloud in the jar", pos, size, mats["P_Cloud"], 3f, 0.14f);
                    break;
                case "rainzone":       // rain falling from the vault into the basins
                {
                    var ps = MakeFall(parent, "Rain from the vault", pos, size, fall > 0 ? fall : 18f, mats["P_Drop"], 0.02f, 0.04f, 7f, Rate(size, 1.2f, 60f),
                                      new Color(0.8f, 0.9f, 1f, 0.8f), new Color(0.7f, 0.85f, 1f, 0.6f), false);
                    var main = ps.main; main.playOnAwake = true; main.prewarm = true;
                    ps.Play();
                    break;
                }
                default:
                    Debug.LogWarning("[Piranesi] Unknown emitter kind " + kind);
                    break;
            }
        }

        static ParticleSystem MakeGlitterBurst(Transform parent, Material mat)
        {
            var ps = NewSystem(parent, "Glitter burst", parent.position, mat, out var r);
            r.maxParticleSize = 0.2f;
            var main = ps.main;
            main.loop = false; main.playOnAwake = false; main.duration = 1.5f;
            main.startLifetime = new ParticleSystem.MinMaxCurve(1f, 2.6f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(0.4f, 2.2f);
            main.startSize = new ParticleSystem.MinMaxCurve(0.03f, 0.09f);
            main.startColor = new ParticleSystem.MinMaxGradient(new Color(1f, 0.95f, 0.8f, 1f), new Color(0.85f, 0.92f, 1f, 1f));
            main.gravityModifier = -0.05f;
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.maxParticles = 140;
            var em = ps.emission; em.rateOverTime = 0f; em.SetBursts(new[] { new ParticleSystem.Burst(0f, (short)110) });
            var sh = ps.shape; sh.enabled = true; sh.shapeType = ParticleSystemShapeType.Sphere; sh.radius = 0.6f;
            var col = ps.colorOverLifetime; col.enabled = true; col.color = new ParticleSystem.MinMaxGradient(FadeGradient());
            return ps;
        }

        static ParticleSystem MakeRain(Transform follower, Material mat)
        {
            var ps = NewSystem(follower, "Storm rain", follower.position, mat, out var r);
            ps.transform.localPosition = new Vector3(0f, 16f, 0f);
            r.renderMode = ParticleSystemRenderMode.Stretch; r.velocityScale = 0.035f; r.lengthScale = 1.5f; r.maxParticleSize = 1f;
            var main = ps.main;
            main.loop = true; main.playOnAwake = false; main.duration = 5f;
            main.startLifetime = new ParticleSystem.MinMaxCurve(1.4f, 1.8f);
            main.startSpeed = 0f;
            main.startSize = new ParticleSystem.MinMaxCurve(0.025f, 0.045f);
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.maxParticles = 6000;
            var em = ps.emission; em.rateOverTime = 2600f;
            var sh = ps.shape; sh.enabled = true; sh.shapeType = ParticleSystemShapeType.Box; sh.scale = new Vector3(50f, 1f, 50f);
            var vel = ps.velocityOverLifetime; vel.enabled = true; vel.space = ParticleSystemSimulationSpace.World;
            vel.x = new ParticleSystem.MinMaxCurve(1.2f, 2.2f); vel.y = new ParticleSystem.MinMaxCurve(-18f, -15f); vel.z = new ParticleSystem.MinMaxCurve(-0.4f, 0.4f);
            return ps;
        }

        static ParticleSystem MakeMeteors(Transform follower, Material mat)
        {
            var ps = NewSystem(follower, "Meteor shower", follower.position, mat, out var r);
            ps.transform.localPosition = new Vector3(0f, 110f, 0f);
            r.renderMode = ParticleSystemRenderMode.Stretch; r.velocityScale = 0.12f; r.lengthScale = 4f; r.maxParticleSize = 1f;
            var main = ps.main;
            main.loop = true; main.playOnAwake = false; main.duration = 5f;
            main.startLifetime = new ParticleSystem.MinMaxCurve(3f, 4.5f);
            main.startSpeed = 0f;
            main.startSize = new ParticleSystem.MinMaxCurve(0.5f, 1.4f);
            main.startColor = new ParticleSystem.MinMaxGradient(new Color(0.9f, 0.95f, 1f, 1f), new Color(1f, 0.9f, 0.75f, 1f));
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.maxParticles = 300;
            var em = ps.emission; em.rateOverTime = 24f;
            var sh = ps.shape; sh.enabled = true; sh.shapeType = ParticleSystemShapeType.Box; sh.scale = new Vector3(260f, 1f, 260f);
            var vel = ps.velocityOverLifetime; vel.enabled = true; vel.space = ParticleSystemSimulationSpace.World;
            vel.x = new ParticleSystem.MinMaxCurve(-40f, -25f); vel.y = new ParticleSystem.MinMaxCurve(-55f, -35f); vel.z = new ParticleSystem.MinMaxCurve(10f, 25f);
            var col = ps.colorOverLifetime; col.enabled = true; col.color = new ParticleSystem.MinMaxGradient(FadeGradient());
            return ps;
        }

        static AudioSource Make2D(Transform parent, string name, AudioClip clip, float vol, bool loop = false)
        {
            var g = Child(parent, name);
            var a = g.AddComponent<AudioSource>();
            a.clip = clip; a.playOnAwake = false; a.loop = loop; a.volume = vol; a.spatialBlend = 0f; a.dopplerLevel = 0f;
            var sp = g.AddComponent<VRCSpatialAudioSource>();
            sp.EnableSpatialization = false; sp.Gain = 0f; sp.UseAudioSourceVolumeCurve = true;
            return a;
        }

        static GameObject MeshChild(Transform parent, string name, Mesh mesh, Material mat, bool collider)
        {
            var g = Child(parent, name);
            g.AddComponent<MeshFilter>().sharedMesh = mesh;
            var r = g.AddComponent<MeshRenderer>(); r.sharedMaterial = mat;
            r.shadowCastingMode = ShadowCastingMode.Off; r.receiveShadows = false;
            if (collider) g.AddComponent<MeshCollider>().sharedMesh = mesh;
            return g;
        }

        // ------------------------------------------------------------------ systems (v3)
        static void BuildV3Systems(Layout L, Dictionary<string, MeshEntry> meshes, Dictionary<string, Material> mats, Transform root, Transform tSys,
                                   HouseClock clock, Transform spawnT, Func<string, string, Material> matFor)
        {
            var chimeClip = Clip("Chime_Found");
            var vehicle = VRC.SDKBase.VRCStation.Mobility.ImmobilizeForVehicle;

            // ---- invisible footholds: colliders with nothing to see (the climb up round the Colossus to her palm)
            if (L.platforms != null && L.platforms.Length > 0)
            {
                var tP = Child(root, "Invisible footholds (round the Colossus)").transform;
                foreach (var pl in L.platforms)
                {
                    if (pl == null || pl.p == null || pl.size == null) continue;
                    var g = Child(tP, string.IsNullOrEmpty(pl.name) ? "Foothold" : pl.name);
                    g.transform.SetPositionAndRotation(V(pl.p), Quaternion.Euler(0f, pl.r, 0f));
                    var bc = g.AddComponent<BoxCollider>(); bc.size = new Vector3(pl.size[0], pl.size[1], pl.size[2]);
                    g.layer = 0;
                    GameObjectUtility.SetStaticEditorFlags(g, StaticEditorFlags.BatchingStatic);
                }
            }

            // ---- the six river floater tubes in the castellum basin, neon in their road's colour
            if (L.rides != null && L.rides.Length > 0)
            {
                Progress("Floater tubes", 0.8f);
                var tR = Child(root, "Roof floater tubes (one per road)").transform;
                var splashClip = Clips("Step_Water_").FirstOrDefault();
                foreach (var rd in L.rides)
                {
                    if (rd == null || rd.path == null || rd.path.Length < 6) continue;
                    var pts = Pts(rd.path);
                    string fam = rd.family;
                    var go = Child(tR, "Floater tube - " + rd.name + (string.IsNullOrEmpty(fam) ? "" : " (" + fam + " road)"));
                    go.transform.position = pts[0];
                    var trig = go.AddComponent<BoxCollider>();
                    trig.isTrigger = true; trig.size = new Vector3(1.8f, 1.2f, 1.8f); trig.center = new Vector3(0f, 0.3f, 0f);
                    var sled = Child(go.transform, "Tube");
                    MakeMeshObject(sled.transform, "River floater tube", "RideTube", meshes, (sb, mv) => matFor(sb, fam), false);
                    var seatT = Child(sled.transform, "Seat"); seatT.transform.localPosition = new Vector3(0f, 0.15f, 0f);
                    var exitT = Child(tR, "Exit - " + rd.name).transform;
                    exitT.SetPositionAndRotation(V(rd.exit), Quaternion.Euler(0f, rd.exitR, 0f));
                    var st = seatT.AddComponent<VRCStation>();
                    st.PlayerMobility = vehicle; st.seated = true; st.canUseStationFromStation = false; st.disableStationExit = false;
                    st.stationEnterPlayerLocation = seatT.transform; st.stationExitPlayerLocation = exitT;
                    var ride = MakeOneShot(sled.transform, "Ride", Clip("Cascade_Loop"), 0.4f, 25f, true);
                    var endGo = Child(tR, "Splash - " + rd.name); endGo.transform.position = pts[pts.Length - 1];
                    var splash = MakeOneShot(endGo.transform, "Splash", splashClip, 1f, 30f);
                    var hs = AddUdon<HouseSlide>(go);
                    hs.station = st; hs.sled = sled.transform; hs.path = pts; hs.exitPoint = exitT;
                    hs.rideSound = ride; hs.splashSound = splash; hs.splashFx = MakeBurst(endGo.transform, mats["P_Drop"], 90);
                    hs.minSpeed = 7f; hs.maxSpeed = 16f;
                    Proxy(hs);
                    SetInteract(hs, string.IsNullOrEmpty(rd.text) ? "Ride" : rd.text, 3f);
                }
            }

            // ---- the Climb vine: its prompt only shows while you stand in the Colossus' hand
            foreach (var tp in L.teleports ?? new LTeleport[0])
            {
                if (tp == null || tp.p == null || tp.p.Length < 3) continue;
                var go = Child(tSys, tp.name);
                Register(go);
                go.transform.position = V(tp.p);
                var bc = go.AddComponent<BoxCollider>(); bc.isTrigger = true; bc.size = tp.size != null && tp.size.Length == 3 ? V(tp.size) : Vector3.one;
                var tgt = Child(go.transform, "Target").transform; tgt.SetPositionAndRotation(V(tp.target), Quaternion.Euler(0f, tp.targetR, 0f));
                var ht = AddUdon<HouseTeleport>(go);
                ht.target = tgt;
                if (tp.near != null && tp.near.Length == 3)
                {
                    var near = Child(go.transform, "Near (the palm)").transform; near.position = V(tp.near);
                    ht.near = near; ht.nearRadius = tp.nearR > 0 ? tp.nearR : 2.4f;
                }
                Proxy(ht);
                SetInteract(ht, string.IsNullOrEmpty(tp.text) ? "Climb" : tp.text, 3f);
            }

            // ---- the Joining of the Three Tides (the Ninth Vestibule)
            foreach (var fl in L.floods ?? new LFlood[0])
            {
                var w = Named(fl.name);
                if (w == null) { Debug.LogWarning("[Piranesi] Flood water not found: " + fl.name); continue; }
                var go = Child(tSys, "Flood clock - " + fl.name);
                var hf = AddUdon<HouseFlood>(go);
                hf.water = w.transform; hf.low = fl.low; hf.high = fl.high; hf.period = fl.period; hf.rise = fl.rise; hf.hold = fl.hold;
                if (fl.sound != null && fl.sound.Length == 3)
                {
                    var sg = Child(go.transform, "Roar"); sg.transform.position = V(fl.sound);
                    hf.roar = MakeOneShot(sg.transform, "Roar of the tides", Clip("Cascade_Loop"), 0.6f, 45f, true);
                }
                Proxy(hf);
            }

            // ---- the Far Hall Quests (6 / 6)
            HouseQuest quest = null;
            if (L.quests != null && L.quests.Length > 0)
            {
                var qgo = Child(tSys, "Far Hall Quests (6 of 6)");
                quest = AddUdon<HouseQuest>(qgo);
                var prizes = new GameObject[6]; var pickups = new GameObject[6]; var glints = new ParticleSystem[6];
                foreach (var q in L.quests)
                {
                    if (q == null || q.index < 0 || q.index > 5) continue;
                    var bg = Child(qgo.transform, "Glints - " + q.name); bg.transform.position = V(q.p);
                    glints[q.index] = MakeGlitterBurst(bg.transform, mats["P_Glint"]);
                    if (q.offering) continue;
                    prizes[q.index] = Named(q.name);
                    if (prizes[q.index] == null) Debug.LogWarning("[Piranesi] Quest prize not found: " + q.name);
                    var pk = Child(qgo.transform, "Take - " + q.name); pk.transform.position = V(q.p);
                    var bc = pk.AddComponent<BoxCollider>(); bc.isTrigger = true; bc.size = q.size != null && q.size.Length == 3 ? V(q.size) : Vector3.one;
                    var link = AddUdon<HouseQuestLink>(pk); link.quest = quest; link.index = q.index;
                    Proxy(link);
                    SetInteract(link, string.IsNullOrEmpty(q.text) ? "Take" : q.text, 2.5f);
                    pickups[q.index] = pk;
                }
                var ui = L.questUi;
                if (ui != null)
                {
                    prizes[5] = Named(ui.candle);
                    quest.shelf = (ui.shelf ?? new string[0]).Select(n => Named(n)).ToArray();
                    quest.counts = (ui.counts ?? new string[0]).Select(n => Named(n)).ToArray();
                    quest.thread = Named(ui.thread);
                    foreach (var g in quest.shelf) if (g != null) g.SetActive(false);
                    for (int i = 0; i < quest.counts.Length; i++) if (quest.counts[i] != null) quest.counts[i].SetActive(i == 0);
                    if (quest.thread != null) quest.thread.SetActive(false);
                    if (prizes[5] != null) prizes[5].SetActive(false);
                }
                quest.prizes = prizes; quest.pickups = pickups; quest.glints = glints;
                quest.chime = Make2D(qgo.transform, "Chime", chimeClip, 0.7f);
                Proxy(quest);
            }

            // ---- the offering in the Alcove of the Dead: a lily for the Dead, gathered for everyone; and a candle lit for you
            foreach (var of in L.offerings ?? new LOffering[0])
            {
                var go = Child(tSys, of.name + " (leave a lily)");
                go.transform.position = V(of.p);
                var bc = go.AddComponent<BoxCollider>(); bc.isTrigger = true; bc.size = of.size != null && of.size.Length == 3 ? V(of.size) : Vector3.one * 2f;
                var ho = AddUdon<HouseOffering>(go);
                ho.lilies = (of.lilies ?? new string[0]).Select(n => Named(n)).Where(g => g != null).ToArray();
                foreach (var g in ho.lilies) g.SetActive(false);
                ho.chime = MakeOneShot(go.transform, "Chime", chimeClip, 0.6f, 20f);
                ho.quest = quest; ho.questIndex = 5;
                Proxy(ho);
                SetInteract(ho, string.IsNullOrEmpty(of.text) ? "Leave a water lily" : of.text, 2.5f);
            }

            // ---- the Stormscape
            var S = L.storm;
            if (S == null) return;
            Progress("Stormscape", 0.82f);
            var sgo = Child(tSys, "Stormscape (dead ends, the storm, Astra's Infinite Pole, the End Show)");
            var storm = AddUdon<HouseStorm>(sgo);

            // the five dead ends: walking in counts it, the court figure glitters
            var bursts = new List<ParticleSystem>();
            int di = 0;
            foreach (var de in L.deadends ?? new LDeadEnd[0])
            {
                var g = Child(sgo.transform, "Dead end - " + de.name);
                g.transform.position = V(de.p);
                var bc = g.AddComponent<BoxCollider>(); bc.isTrigger = true; bc.size = V(de.size);
                var link = AddUdon<HouseStormLink>(g); link.storm = storm; link.mode = 0; link.index = di++;
                Proxy(link);
                var b = Child(g.transform, "Court figure glitter"); b.transform.position = V(de.burst);
                bursts.Add(MakeGlitterBurst(b.transform, mats["P_Glint"]));
            }
            storm.bursts = bursts.ToArray();
            storm.tally = (S.tally ?? new string[0]).Select(n => Named(n)).ToArray();
            for (int i = 0; i < storm.tally.Length; i++) if (storm.tally[i] != null) storm.tally[i].SetActive(i == 0);
            storm.chime = Make2D(sgo.transform, "Chime", chimeClip, 0.7f);
            storm.clock = clock;
            storm.stormSky = mats["StormSky"]; storm.starsSky = mats["StarsSky"];

            // what follows the player: rain, its sound, the meteor shower
            var fol = Child(sgo.transform, "Follows the player (rain, meteors)");
            storm.follower = fol.transform;
            storm.rain = MakeRain(fol.transform, mats["Rain"]);
            storm.rainSound = Make2D(fol.transform, "Rain", Clip("Rain_Loop"), 0.7f, true);
            storm.meteors = MakeMeteors(fol.transform, mats["P_Meteor"]);
            storm.meteorSound = Make2D(fol.transform, "Meteors", Clip("Meteor_Whoosh"), 0.8f, true);

            // lightning bolts in the sky round the House, and thunder
            var bolts = new List<GameObject>();
            for (int i = 0; i < 5; i++)
            {
                float a = i * 1.37f + 0.4f, dist = 300f + 70f * (i % 3);
                var bg = Child(sgo.transform, "Lightning bolt " + (i + 1));
                bg.layer = WaterLayer;
                var bp = new Vector3(Mathf.Cos(a) * dist, 150f, Mathf.Sin(a) * dist);
                bg.transform.position = bp;
                bg.transform.rotation = Quaternion.LookRotation(new Vector3(bp.x, 0f, bp.z).normalized);
                bg.transform.localScale = new Vector3(70f, 280f, 1f);
                bg.AddComponent<MeshFilter>().sharedMesh = meshes["__Quad"].mesh;
                var r = bg.AddComponent<MeshRenderer>(); r.sharedMaterial = mats["Bolt"];
                r.shadowCastingMode = ShadowCastingMode.Off; r.receiveShadows = false;
                bg.SetActive(false);
                bolts.Add(bg);
            }
            storm.bolts = bolts.ToArray();
            storm.thunder = Make2D(sgo.transform, "Thunder", null, 0.6f);
            storm.thunderClips = new[] { Clip("Thunder_0"), Clip("Thunder_1"), Clip("Thunder_2") }.Where(c => c != null).ToArray();

            // the dome opens to the sky; the Climb vine goes
            storm.domeClosed = (S.openDome ?? new string[0]).Select(n => Named(n)).Where(g => g != null).ToArray();
            var opens = new List<GameObject>();
            for (int i = 0; i < storm.domeClosed.Length && S.openMeshes != null && i < S.openMeshes.Length; i++)
            {
                var orig = storm.domeClosed[i];
                var og = MakeMeshObject(orig.transform.parent, orig.name + " (open to the sky)", S.openMeshes[i], meshes, matFor);
                og.transform.SetPositionAndRotation(orig.transform.position, orig.transform.rotation);
                og.transform.localScale = orig.transform.localScale;
                if (orig.GetComponent<MeshCollider>() != null && meshes.TryGetValue(S.openMeshes[i], out var om)) og.AddComponent<MeshCollider>().sharedMesh = om.mesh;
                og.SetActive(false);
                opens.Add(og);
            }
            storm.domeOpen = opens.ToArray();
            storm.hideInStorm = (S.hideInStorm ?? new string[0]).SelectMany(n => AllNamed(n)).ToArray();

            // Astra's Infinite Pole out of the palm, and the Infinite Spiral round it
            var stair = Child(sgo.transform, "Astra's Infinite Pole and the Infinite Spiral");
            var axis = S.axis != null && S.axis.Length == 3 ? V(S.axis) : Vector3.zero;
            stair.transform.position = new Vector3(axis.x, 0f, axis.z);
            storm.stair = stair;
            var poleGo = MakeMeshObject(stair.transform, "Astra's Infinite Pole", "AstraPole", meshes, matFor, false);
            poleGo.transform.position = V(S.pole);
            poleGo.transform.localScale = new Vector3(1f, 0.001f, 1f);
            storm.pole = poleGo.transform;
            int nT = S.turns > 0 ? S.turns : 11;
            var turnTs = new Transform[nT];
            for (int i = 0; i < nT; i++)
            {
                var tg = MeshChild(stair.transform, "Spiral turn " + (i + 1), meshes["__StairTurn"].mesh, mats["Stair"], false);
                tg.transform.localPosition = new Vector3(0f, S.@base + i * S.pitch, 0f);
                var ramp = Child(tg.transform, "Walkable ramp");
                ramp.AddComponent<MeshCollider>().sharedMesh = meshes["__StairRamp"].mesh;
                turnTs[i] = tg.transform;
            }
            storm.turns = turnTs;
            var wedge = MeshChild(stair.transform, "Step off the palm onto the stair", meshes["__Wedge"].mesh, mats["Landing"], true);
            wedge.transform.localPosition = new Vector3(0f, S.@base, 0f);
            float topY = S.@base + S.topTurns * S.pitch;
            var land = MeshChild(stair.transform, "Top step (platform among the stars)", meshes["__Landing"].mesh, mats["Landing"], true);
            land.transform.localPosition = new Vector3(0f, topY, 0f);

            // Astra's phone booth, a little way round from the top of the stair, its open door toward you
            float ab = S.theta0 + 0.62f, rb = (S.inner + S.outer) * 0.5f;
            var tangent = new Vector3(-Mathf.Sin(ab), 0f, Mathf.Cos(ab));
            var boothGo = Child(stair.transform, "Astra's phone booth");
            boothGo.transform.localPosition = new Vector3(Mathf.Cos(ab) * rb, topY, Mathf.Sin(ab) * rb);
            boothGo.transform.rotation = Quaternion.LookRotation(-tangent);
            for (int i = 0; i < 4; i++) MeshChild(boothGo.transform, BoothNames[i], meshes["__Booth" + i].mesh, mats[BoothMats[i]], false);
            foreach (var (c, s) in new[] { (new Vector3(0f, 1.3f, -0.62f), new Vector3(1.3f, 2.6f, 0.06f)), (new Vector3(-0.62f, 1.3f, 0f), new Vector3(0.06f, 2.6f, 1.3f)),
                                           (new Vector3(0.62f, 1.3f, 0f), new Vector3(0.06f, 2.6f, 1.3f)) })
            {
                var wc = Child(boothGo.transform, "Wall").AddComponent<BoxCollider>(); wc.center = c; wc.size = s;
            }
            var zone = Child(boothGo.transform, "Step inside (the End Show)");
            zone.transform.localPosition = new Vector3(0f, 1.15f, -0.1f);
            var zc = zone.AddComponent<BoxCollider>(); zc.isTrigger = true; zc.size = new Vector3(1.0f, 2.2f, 0.9f);
            var bl = AddUdon<HouseStormLink>(zone); bl.storm = storm; bl.mode = 2;
            Proxy(bl);
            storm.booth = boothGo.transform;

            // the End Show: the dive station, the tunnel, the blackout
            var seat = Child(sgo.transform, "Hyperspace dive (station)");
            seat.transform.position = boothGo.transform.position;
            var dst = seat.AddComponent<VRCStation>();
            dst.PlayerMobility = VRC.SDKBase.VRCStation.Mobility.Immobilize; dst.seated = false; dst.disableStationExit = true; dst.canUseStationFromStation = true;
            dst.stationEnterPlayerLocation = seat.transform; dst.stationExitPlayerLocation = seat.transform;
            storm.diveStation = dst; storm.diveSeat = seat.transform;
            var warp = MeshChild(sgo.transform, "Hyperspace tunnel", meshes["__WarpTube"].mesh, mats["Warp"], false);
            warp.layer = WaterLayer;
            warp.SetActive(false);
            storm.warp = warp.transform; storm.warpMat = mats["Warp"];
            storm.warpSound = Make2D(sgo.transform, "Hyperspace rush", Clip("Warp_Rush"), 0.9f, true);
            var bo = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            bo.name = "Blackout"; bo.transform.SetParent(sgo.transform, false);
            Object.DestroyImmediate(bo.GetComponent<Collider>());
            bo.transform.localScale = Vector3.one * 0.8f;
            var bor = bo.GetComponent<MeshRenderer>(); bor.sharedMaterial = mats["Blackout"]; bor.shadowCastingMode = ShadowCastingMode.Off; bor.receiveShadows = false;
            bo.SetActive(false);
            storm.blackout = bo.transform; storm.blackoutMat = mats["Blackout"];

            storm.baseY = S.@base; storm.pitch = S.pitch; storm.topTurns = S.topTurns; storm.grow = S.grow; storm.growDelay = S.growDelay;
            if (S.white != null && S.white.Length == 2) { storm.white0 = S.white[0]; storm.white1 = S.white[1]; }
            if (S.stars != null && S.stars.Length == 2) { storm.stars0 = S.stars[0]; storm.stars1 = S.stars[1]; }
            if (S.meteors > 0) storm.meteorSeconds = S.meteors;
            if (S.diveTime > 0) storm.diveSeconds = S.diveTime;
            if (S.blackout != null && S.blackout.Length == 3) { storm.fadeIn = S.blackout[0]; storm.hold = S.blackout[1]; storm.fadeOut = S.blackout[2]; }
            storm.palm = V(S.pole) + Vector3.up * 0.25f;
            storm.spawnPoint = spawnT;
            Proxy(storm);
            stair.SetActive(false);

            // the secret rosette under the Colossus' foot
            var ros = Named(S.rosette);
            if (ros != null)
            {
                var mf = ros.GetComponent<MeshFilter>();
                var rc = ros.GetComponent<BoxCollider>();
                if (rc == null) rc = ros.AddComponent<BoxCollider>();
                if (mf != null && mf.sharedMesh != null) { rc.center = mf.sharedMesh.bounds.center; rc.size = mf.sharedMesh.bounds.size + Vector3.one * 0.15f; }
                var rl = AddUdon<HouseStormLink>(ros); rl.storm = storm; rl.mode = 1;
                Proxy(rl);
                SetInteract(rl, "Press the rosette", 2f);
            }
            else Debug.LogWarning("[Piranesi] Secret rosette not found: " + S.rosette);
        }
    }
}
