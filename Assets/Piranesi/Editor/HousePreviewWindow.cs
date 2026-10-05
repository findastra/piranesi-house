// Piranesi > Time, Season & Tide Preview: scrub the House's clock in the editor.
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace Piranesi.EditorTools
{
    [InitializeOnLoad]
    public class HousePreviewWindow : EditorWindow
    {
        public static float Day = 0.3f, Season = 1.3f, Tide = 0.25f;
        static readonly string[] SeasonNames = { "Spring", "Summer", "Autumn", "Winter" };

        static HousePreviewWindow()
        {
            EditorApplication.delayCall += () => ApplyState(Day, Season, Tide, false);
            EditorSceneManager.sceneOpened += (s, m) => ApplyState(Day, Season, Tide, false);
        }

        [MenuItem("Piranesi/Time, Season & Tide Preview", priority = 10)]
        static void Open() => GetWindow<HousePreviewWindow>("House Preview");

        void OnGUI()
        {
            EditorGUILayout.LabelField("The House - editor preview", EditorStyles.boldLabel);
            EditorGUILayout.HelpBox("In VRChat these advance on their own from server time, identical for everyone in the instance.", MessageType.Info);
            EditorGUI.BeginChangeCheck();
            Day = EditorGUILayout.Slider("Time of day", Day, 0f, 1f);
            Season = EditorGUILayout.Slider("Season (" + SeasonNames[(int)Mathf.Repeat(Season, 4f) % 4] + ")", Season, 0f, 3.999f);
            Tide = EditorGUILayout.Slider("Tide height (m)", Tide, -0.45f, 0.85f);
            if (EditorGUI.EndChangeCheck()) ApplyState(Day, Season, Tide, true);
            GUILayout.Space(6);
            GUILayout.BeginHorizontal();
            if (GUILayout.Button("Dawn")) Set(0.02f);
            if (GUILayout.Button("Noon")) Set(0.32f);
            if (GUILayout.Button("Sunset")) Set(0.61f);
            if (GUILayout.Button("Moonlit night")) Set(0.82f);
            GUILayout.EndHorizontal();
        }

        void Set(float d) { Day = d; ApplyState(Day, Season, Tide, true); Repaint(); }

        public static void ApplyState(float day, float season, float tide, bool particles)
        {
            var clock = Object.FindObjectOfType<HouseClock>();
            if (clock == null || clock.skyTop == null || clock.skyTop.Length < 4) return;
            clock.InitIds();
            float snow = clock.WinterWeight(season);
            clock.ApplyState(day, season, tide, snow, tide + 0.05f, particles);
            SceneView.RepaintAll();
        }
    }
}
