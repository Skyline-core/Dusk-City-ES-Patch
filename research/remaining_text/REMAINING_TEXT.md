# Remaining player-visible text (survey)

**Game path:** `G:\SteamLibrary\steamapps\common\Dusk City`  
**Generated:** 2026-11-03 07:39 UTC  
**Scanner:** `translation/research/remaining_text/scan_remaining_text.py`

## Exclusions (not listed as remaining work)

- Unity `Translation_en` / H-scene `*_EN` TextAssets / `Image_en` table entries (handled via `es_source.json`).
- GameScript `m_commandDatas` literals (handled via `es_source_scripts.json`).
- Dialogue graph MonoBehaviours (edges/nodes/labelNodes/…): **212 assets**, ~**11191** English prose strings counted inside (patched elsewhere).

## Summary counts

| Metric | Value |
|--------|------:|
| distinct_english_candidates | 150 |
| distinct_japanese_leaks | 806 |
| localized_image_instances | 348 |
| localized_image_unique_names | 89 |
| english_mono_behaviour | 100 |
| english_tmp_ui | 4 |
| english_ui_text | 2 |
| english_visual_scripting | 44 |

## Categories (storage + patch approach + priority)

### `mono_behaviour` — 100 distinct strings

- **Storage:** Serialized string fields on scene/prefab components (quest titles, labels, custom UI data).
- **Patch:** Typetree walk + patch per `path_id`; resolve class via `m_Script` → `MonoScript.m_ClassName`.
- **Player priority:** **High** for gameplay/UI components; filter out Visual Scripting port identifiers.

### `tmp_ui` — 4 distinct strings

- **Storage:** TMP `m_text` / `TMP_Dropdown.m_Options` on prefabs in Addressables or built-in scenes.
- **Patch:** UnityPy `read_typetree()` → edit string fields → `obj.save()` / rebundle; same CRC forge flow as other bundle patches.
- **Player priority:** **High** — menus, HUD, interaction prompts baked into prefabs.

### `ui_text` — 2 distinct strings

- **Storage:** Legacy `UnityEngine.UI.Text` (`m_Text`).
- **Patch:** Typetree string replace in bundle or sharedassets.
- **Player priority:** **High** where present (mostly legacy UI).

### `visual_scripting` — 44 distinct strings

- **Storage:** Unity Visual Scripting graphs (`ScriptGraphAsset`, `_data` / `jsonData` string literals).
- **Patch:** Typetree edit of literal strings inside graph JSON; avoid port keys.
- **Player priority:** **High** for language dropdown / flow UI wired in VS.

## Localized images (`*_EN` / `*_en`)

Distinct names: **89** (instances in files: 348).

Text-bearing candidates (filename hints: tutorial, guide, hint, text, title, menu, help, tip):
- `TipsR_1_EN` (0x0) — `StandaloneWindows64/localization-assets-english(en)_assets_all_71740f550b08ffbbaf27aee890fc02dd.bundle`
- `TipsR_1_EN` (1200x678) — `StandaloneWindows64/localization-assets-english(en)_assets_all_71740f550b08ffbbaf27aee890fc02dd.bundle`
- `TipsR_1_EN` (0x0) — `StandaloneWindows64/localization-assets-english(en)_assets_all_2226d8d2b0d3da2279c40b114f5b8f8c.bundle`
- `TipsR_1_EN` (1200x678) — `StandaloneWindows64/localization-assets-english(en)_assets_all_2226d8d2b0d3da2279c40b114f5b8f8c.bundle`
- `TipsR_2_EN` (0x0) — `StandaloneWindows64/localization-assets-english(en)_assets_all_71740f550b08ffbbaf27aee890fc02dd.bundle`
- `TipsR_2_EN` (1200x678) — `StandaloneWindows64/localization-assets-english(en)_assets_all_71740f550b08ffbbaf27aee890fc02dd.bundle`
- `TipsR_2_EN` (0x0) — `StandaloneWindows64/localization-assets-english(en)_assets_all_2226d8d2b0d3da2279c40b114f5b8f8c.bundle`
- `TipsR_2_EN` (1200x678) — `StandaloneWindows64/localization-assets-english(en)_assets_all_2226d8d2b0d3da2279c40b114f5b8f8c.bundle`
- `TipsR_3_EN` (0x0) — `StandaloneWindows64/localization-assets-english(en)_assets_all_71740f550b08ffbbaf27aee890fc02dd.bundle`
- `TipsR_3_EN` (1200x678) — `StandaloneWindows64/localization-assets-english(en)_assets_all_71740f550b08ffbbaf27aee890fc02dd.bundle`
- `TipsR_3_EN` (0x0) — `StandaloneWindows64/localization-assets-english(en)_assets_all_2226d8d2b0d3da2279c40b114f5b8f8c.bundle`
- `TipsR_3_EN` (1200x678) — `StandaloneWindows64/localization-assets-english(en)_assets_all_2226d8d2b0d3da2279c40b114f5b8f8c.bundle`
- `TipsR_4_EN` (0x0) — `StandaloneWindows64/localization-assets-english(en)_assets_all_71740f550b08ffbbaf27aee890fc02dd.bundle`
- `TipsR_4_EN` (1200x678) — `StandaloneWindows64/localization-assets-english(en)_assets_all_71740f550b08ffbbaf27aee890fc02dd.bundle`
- `TipsR_4_EN` (0x0) — `StandaloneWindows64/localization-assets-english(en)_assets_all_2226d8d2b0d3da2279c40b114f5b8f8c.bundle`
- `TipsR_4_EN` (1200x678) — `StandaloneWindows64/localization-assets-english(en)_assets_all_2226d8d2b0d3da2279c40b114f5b8f8c.bundle`
- `TipsS_1_EN` (1200x678) — `StandaloneWindows64/localization-assets-english(en)_assets_all_71740f550b08ffbbaf27aee890fc02dd.bundle`
- `TipsS_1_EN` (0x0) — `StandaloneWindows64/localization-assets-english(en)_assets_all_71740f550b08ffbbaf27aee890fc02dd.bundle`
- `TipsS_1_EN` (1200x678) — `StandaloneWindows64/localization-assets-english(en)_assets_all_2226d8d2b0d3da2279c40b114f5b8f8c.bundle`
- `TipsS_1_EN` (0x0) — `StandaloneWindows64/localization-assets-english(en)_assets_all_2226d8d2b0d3da2279c40b114f5b8f8c.bundle`
- `TipsS_2_EN` (0x0) — `StandaloneWindows64/localization-assets-english(en)_assets_all_71740f550b08ffbbaf27aee890fc02dd.bundle`
- `TipsS_2_EN` (1200x678) — `StandaloneWindows64/localization-assets-english(en)_assets_all_71740f550b08ffbbaf27aee890fc02dd.bundle`
- `TipsS_2_EN` (0x0) — `StandaloneWindows64/localization-assets-english(en)_assets_all_2226d8d2b0d3da2279c40b114f5b8f8c.bundle`
- `TipsS_2_EN` (1200x678) — `StandaloneWindows64/localization-assets-english(en)_assets_all_2226d8d2b0d3da2279c40b114f5b8f8c.bundle`
- `TipsS_3_EN` (1200x678) — `StandaloneWindows64/localization-assets-english(en)_assets_all_71740f550b08ffbbaf27aee890fc02dd.bundle`
- `TipsS_3_EN` (0x0) — `StandaloneWindows64/localization-assets-english(en)_assets_all_71740f550b08ffbbaf27aee890fc02dd.bundle`
- `TipsS_3_EN` (1200x678) — `StandaloneWindows64/localization-assets-english(en)_assets_all_2226d8d2b0d3da2279c40b114f5b8f8c.bundle`
- `TipsS_3_EN` (0x0) — `StandaloneWindows64/localization-assets-english(en)_assets_all_2226d8d2b0d3da2279c40b114f5b8f8c.bundle`
- `Tips_1_EN` (1200x678) — `StandaloneWindows64/localization-assets-english(en)_assets_all_71740f550b08ffbbaf27aee890fc02dd.bundle`
- `Tips_1_EN` (0x0) — `StandaloneWindows64/localization-assets-english(en)_assets_all_71740f550b08ffbbaf27aee890fc02dd.bundle`
- `Tips_1_EN` (1200x678) — `StandaloneWindows64/localization-assets-english(en)_assets_all_2226d8d2b0d3da2279c40b114f5b8f8c.bundle`
- `Tips_1_EN` (0x0) — `StandaloneWindows64/localization-assets-english(en)_assets_all_2226d8d2b0d3da2279c40b114f5b8f8c.bundle`
- `Tips_2_EN` (0x0) — `StandaloneWindows64/localization-assets-english(en)_assets_all_71740f550b08ffbbaf27aee890fc02dd.bundle`
- `Tips_2_EN` (1200x678) — `StandaloneWindows64/localization-assets-english(en)_assets_all_71740f550b08ffbbaf27aee890fc02dd.bundle`
- `Tips_2_EN` (0x0) — `StandaloneWindows64/localization-assets-english(en)_assets_all_2226d8d2b0d3da2279c40b114f5b8f8c.bundle`
- `Tips_2_EN` (1200x678) — `StandaloneWindows64/localization-assets-english(en)_assets_all_2226d8d2b0d3da2279c40b114f5b8f8c.bundle`
- `Tips_3_EN` (1200x678) — `StandaloneWindows64/localization-assets-english(en)_assets_all_71740f550b08ffbbaf27aee890fc02dd.bundle`
- `Tips_3_EN` (0x0) — `StandaloneWindows64/localization-assets-english(en)_assets_all_71740f550b08ffbbaf27aee890fc02dd.bundle`
- `Tips_3_EN` (1200x678) — `StandaloneWindows64/localization-assets-english(en)_assets_all_2226d8d2b0d3da2279c40b114f5b8f8c.bundle`
- `Tips_3_EN` (0x0) — `StandaloneWindows64/localization-assets-english(en)_assets_all_2226d8d2b0d3da2279c40b114f5b8f8c.bundle`
- … and 28 more (see `scan_stats.json`).

## Top component classes (English prose)

- **StrayCatLab.Game.Interactable** (mono_behaviour): 24 strings — fields {'text': 24}; e.g. ['Bucephalus ', 'Central residential area ', 'Eastern ruins ']
- **Unity.VisualScripting.ScriptMachine** (visual_scripting): 12 strings — fields {'_data': 23}; e.g. ['BookAuthorNaming', 'Building', 'Digital']
- **UnityEngine.UI.Text** (mono_behaviour): 19 strings — fields {'m_Text': 19}; e.g. ['CPU: Processor Model [# cores]', 'GPU: Graphics Card Name', 'Graphics API: Graphics API version [level ##]']
- **StrayCatLab.Game.ItemData** (mono_behaviour): 15 strings — fields {'description': 14, 'itemName': 1}; e.g. ['A beautiful light blue gemstone \nUnreadable characters engraved on it\r\n', 'Arm parts of junk creatures\r', 'Despite its age, it appears to be in good condition without any missing parts \nPerhaps someone would want this...']
- **Kanono1Status** (visual_scripting): 1 strings — fields {'_data': 14}; e.g. ['start']
- **TMPro.TextMeshProUGUI** (mono_behaviour): 11 strings — fields {'m_text': 11}; e.g. ['Continue', 'Fullscreen', 'Money']
- **Unity.VisualScripting.StateMachine** (visual_scripting): 6 strings — fields {'_data': 7}; e.g. ['ChipSetStart', 'bucephalas', 'gonta']
- **MonoBehaviour** (mono_behaviour): 6 strings — fields {'m_text': 6}; e.g. ['Button', 'Item description is here\nsecond line\nthird line\nfourth line\nfinal line', 'ItemNameaaaaaaaaaa']
- **UnityEngine.Localization.Locale** (mono_behaviour): 4 strings — fields {'m_LocaleName': 3, 'm_Identifier': 1}; e.g. ['Chinese (Simplified) (zh-CN)', 'English (en)', 'Japanese (ja)']
- **StrayCatLab.Utilities.Audio.BGMTrigger** (mono_behaviour): 3 strings — fields {'m_HorizontalAxis': 1, 'm_SubmitButton': 1, 'm_VerticalAxis': 1}; e.g. ['Horizontal', 'Submit', 'Vertical']
- **UnityEngine.EventSystems.StandaloneInputModule** (mono_behaviour): 3 strings — fields {'m_HorizontalAxis': 1, 'm_SubmitButton': 1, 'm_VerticalAxis': 1}; e.g. ['Horizontal', 'Submit', 'Vertical']
- **UnityEngine.Localization.Tables.SharedTableData** (mono_behaviour): 2 strings — fields {'m_TableCollectionName': 2}; e.g. ['Image', 'Translation']
- **UnityEventHolder** (mono_behaviour): 2 strings — fields {'_data': 2}; e.g. ['{"declarations":{"Kind":"Object","collection":{"$content":[],"$version":"A"},"$version":"A"}}', '{"declarations":{"Kind":"Scene","collection":{"$content":[],"$version":"A"},"$version":"A"}}']
- **MonoBehaviour** (tmp_ui): 2 strings — fields {'m_text': 2}; e.g. ['Button', 'Item description is here\nsecond line\nthird line\nfourth line\nfinal line']
- **UnityEngine.UI.Text** (ui_text): 2 strings — fields {'m_Text': 2}; e.g. ['Graphics API: Graphics API version [level ##]', 'OS: OS Version [Platform]']
- **BallHitChecer** (mono_behaviour): 1 strings — fields {'targetTagName': 1}; e.g. ['Ball']
- **Dieselmine.Utilities.GameVariable.IntVariableTable** (mono_behaviour): 1 strings — fields {'table[24]': 1}; e.g. ['0=on 1=off']
- **DronePawn** (mono_behaviour): 1 strings — fields {'name': 1}; e.g. ['Player']
- **ObjectSwitcher** (mono_behaviour): 1 strings — fields {'targetTag': 1}; e.g. ['Player']
- **StrayCatLab.Game.MovingPlatform** (mono_behaviour): 1 strings — fields {'animatorCloseFlag': 1}; e.g. ['Close']
- **StrayCatLab.Game.MovingPlatformController** (mono_behaviour): 1 strings — fields {'targetTagName': 1}; e.g. ['Ball']
- **StrayCatLab.Game.SPWeaponLaser** (mono_behaviour): 1 strings — fields {'collisionNormalPropertyName': 1}; e.g. ['Collision Normal']
- **StrayCatLab.Game.SnakeBoss** (mono_behaviour): 1 strings — fields {'bossDisplayName': 1}; e.g. ['Big Snake']
- **StrayCatLab.Game.TrainPusher** (mono_behaviour): 1 strings — fields {'targetTag': 1}; e.g. ['Player']
- **StrayCatLab.Game.WeaponUpgrade** (mono_behaviour): 1 strings — fields {'description': 1}; e.g. ['Range increase ']

## Japanese text in non-JP assets (possible EN-locale leaks)

- `mono_behaviour`: **500** distinct strings
- `visual_scripting`: **271** distinct strings
- `tmp_ui`: **35** distinct strings

  - [mono_behaviour] `ArtificialIslandの扉鍵`
  - [mono_behaviour] `CG回想解放チェック`
  - [mono_behaviour] `DLC1で新規追加したセリフを表示させるためのフラグ`
  - [mono_behaviour] `DLC1のチップスを表示したかどうか`
  - [mono_behaviour] `DLC1のチップスを表示後魔女子と話したかどうか`
  - [mono_behaviour] `Decoyと話したかどうか`
  - [mono_behaviour] `Decoyに[Hをお願いする]選択をしたかどうか`
  - [mono_behaviour] `VRDeviceを起動する(二度目)を選択したかどうか`
  - [mono_behaviour] `VRDeviceを起動するを選択したかどうか`
  - [mono_behaviour] `VRdevideを起動するかどうか`
  - [mono_behaviour] `VRデバイス`
  - [mono_behaviour] `cut015以降ベンチに魔女子さん居ない用`
  - [mono_behaviour] `「くノ一デート」クリアしたかどうか`
  - [mono_behaviour] `「エステのお姉さんデート」クリアしたかどうか`
  - [mono_behaviour] `「モグラデート」クリアしたかどうか`

## Player-impact ranking (recommended order)

0. **Dialogue graph nodes** (excluded here) — ~**11191** English strings in **212** graph assets; typetree patch on graph `references.RefIds[].data` (handled by dialogue graph pipeline).
1. **Component serialized UI copy** — ~100 distinct strings; Typetree per MonoBehaviour
2. **Visual Scripting UI literals** — ~44 distinct strings; Graph typetree string literals
3. **Prefab TMP / dropdown labels** — ~4 distinct strings; Typetree `m_text` / options in scene bundles
4. **Legacy UI Text** — ~2 distinct strings; Typetree `m_Text`
5. **Localized `_EN` images** — ~89 distinct strings; Replace sprites/textures; keep Addressables names

### High-confidence gameplay copy (subset)

- **Interactable.text (world prompts)**: 24 distinct strings
- **ItemData (names/descriptions)**: 15 distinct strings
- **Locale display names (en/zh/ja)**: 4 distinct strings
- **TMP in-scene (m_text)**: 12 distinct strings
