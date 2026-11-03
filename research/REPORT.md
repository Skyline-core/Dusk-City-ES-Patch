# Dusk City — Spanish (`es`) locale research report

**Game:** Dusk City v2.02 (Unity IL2CPP, Windows)  
**Research path:** `translation/research/` (read-only on game files)  
**Date:** 2026-11-02

---

## Tools and commands

| Step | Command / artifact |
|------|-------------------|
| IL2CPP dump | `Il2CppDumper.exe "<GameAssembly.dll>" "<global-metadata.dat>" "<translation/research/il2cpp_dump>"` (Il2CppDumper **v6.7.46**, metadata/IL2CPP **v31**) |
| Outputs | `il2cpp_dump/dump.cs`, `script.json`, `stringliteral.json`, `DummyDll/` |
| x64 disassembly | `python translation/research/disasm_localize.py` → `disasm_localize.txt` |
| PlayerPrefs selector | `python translation/research/disasm_playerpref.py` |
| Addressables / tables | UnityPy (`Python312`) — see `translation/_inspect2.py` pattern |
| Player settings | UnityPy on `Dusk City_Data/globalgamemanagers` |
| Fonts | UnityPy scan of `resources.assets`, `sharedassets*.assets`, `StreamingAssets/aa/StandaloneWindows64/*.bundle` |

Il2CppDumper succeeded on first try (no Il2CppInspector fallback needed).

---

## 1. Language selection — how it works

### Two parallel systems

**A. Unity Localization (official)** — package in `Unity.Localization.dll`

- Locales in Addressables: `ja`, `en`, `zh-CN` (`localization-locales_assets_all.bundle`).
- String tables: `Translation_<code>` (e.g. `Translation_en`).
- Asset tables: `Image_<code>` (e.g. `Image_en`).
- Runtime API: `LocalizationSettings.SelectedLocale` (get/set), `AvailableLocales`, `StringDatabase`, startup selectors (`PlayerPrefLocaleSelector`, `SystemLocaleSelector`, etc.).

**B. Custom wrapper (Assembly-CSharp)** — hard-coded **3** languages

```249405:249449:translation/research/il2cpp_dump/dump.cs
public enum Languages // TypeDefIndex: 1973
{
	public const Languages JP = 0;
	public const Languages EN = 1;
	public const Languages SCH = 2;
}

public static class DEFINE_DATA_LOCALIZE // TypeDefIndex: 1974
{
	public const string LOCALIZE_STRING_TABLE = "Translation";
	public const string LOCALIZE_ASSET_TABLE_SPRITE = "Image";
}

public class LocalizeManager : MonoSingleton<LocalizeManager> // TypeDefIndex: 1975
{
	public Languages language; // 0x20
	// GetLocalizeString, GetLocalizeAsset<T>, GetLocalizeNumber, Start
}
```

There is **no** `Languages.ES` and **no** C# reference that iterates `LocalizationSettings.AvailableLocales` for the options menu. The enum exists only on `LocalizeManager` and `OnLanguageUpdate(Languages)` on legacy UI helpers (`LocalizedTextTMPro`, `LocalizedImage`, `LocalizedSprite`, `LocalizedText`, `LocalizeTextFont`).

### UI / config screens (no dedicated “Language” C# page)

- Pause/title options: `StrayCatLab.Game.ConfigPage` — volume, fullscreen, resolution, message speed only (**no** language dropdown fields in `dump.cs`).
- `ConfigSave` (MemoryPack) stores audio/display settings only — **no language field** (`dump.cs` TypeDefIndex 1849).
- `MainGameSaveData` has no locale field (TypeDefIndex 3241).
- Language UI is almost certainly **Unity Visual Scripting** (AOT stubs exist for `LocalizeManager`, `Localized*`) and/or **TMP_Dropdown** in scene bundles (string `dropdown` found in bundle `7ff7bbb50d8963f8cfda64e43d946131.bundle`).

### Persistence and startup (evidence from disassembly)

| Mechanism | Class / method | RVA (GameAssembly) | Behavior |
|-----------|----------------|----------------------|----------|
| PlayerPrefs (Unity Localization) | `PlayerPrefLocaleSelector.GetStartupLocale` | `0x2897BF0` | `PlayerPrefs.HasKey` / `GetString` on `m_PlayerPreferenceKey`, then resolve locale via `ILocalesProvider` |
| PlayerPrefs write on change | `PlayerPrefLocaleSelector.PostInitialization` | `0x2897D10` | Subscribes to `LocalizationSettings`; writes prefs when locale changes |
| OS language | `SystemLocaleSelector.GetStartupLocale` | `0x289AD00` | Maps `Application.systemLanguage` → `LocaleIdentifier` → locale lookup |
| Custom bootstrap | `LocalizeManager.Start` | `0x39430` | Calls `LocalizationSettings.get_AvailableLocales`, then **`Locales[1]`** → `set_SelectedLocale` (index **1** = second locale in provider list, typically **English** if order is ja/en/zh-CN) |

**PlayerPrefs (Windows):** Unity stores under registry, normally:

`HKCU\Software\<companyName>\<productName>\`

From `PlayerSettings` (UnityPy on `globalgamemanagers`):

- **companyName:** `すてねこLAB.`
- **productName:** `Dusk City`

Locale value format: Unity Localization stores the **locale code string** (e.g. `en`, `ja`, `zh-CN`) under the selector’s key (serialized on the Localization Settings asset; constructor default is assigned at runtime — standard package default is **`SelectedLocale`**). Confirm after running the game with `reg query "HKCU\Software"` / Unity PlayerPrefs viewer.

**Config file save (not language):** `Config.Save` / `Config.Load` (RVA `0x33760` / `0x33310`) build a `ConfigSave` and call `Dieselmine.Utilities.SaveLoad.AdvancedSaveLoadUtilities.Save` with a `SavePathUtility` (paths are scene-serialized; typical Unity layout is `%USERPROFILE%\AppData\LocalLow\<company>\<product>\`).

### `GetLocalizeNumber` (misleading name)

RVA `0x391E0`: calls `LocalizationSettings.get_SelectedLocale`, returns **`ushort` at Locale+0x42** → `Locale.m_SortOrder` in `dump.cs`, **not** `Languages` enum. All shipped locales use **`m_SortOrder: 10000`** in data — not useful as a 0/1/2 index.

### Japanese “skip translation” rule

`LocalizeManager.GetLocalizeString` / `GetLocalizeAsset` (RVA `0x39200`, `0x4E0340`): if `LocalizeManager.language == 0` (**JP**), they **return early** (pass-through / no table lookup).  
`LocalizedImage.OnLanguageUpdate` (RVA `0x396B0`): if `_lang == 0`, clears sprite; else `GetLocalizeAsset<Sprite>("Image", …)`.

---

## 2. `*_EN` TextAssets, sprites, and locale `es`

### Not runtime `"_EN"` suffix from locale code

GameAssembly has almost **no** `_EN` / `Translation_` string literals (only 2× `_EN` hits in the DLL — not game logic). Suffixes live in **Addressables per locale**, not in C# string concat.

| Locale bundle | TextAsset naming (53 H-scene JSON scripts each) |
|---------------|--------------------------------------------------|
| English | `*_EN` (e.g. `Cafe_staff_dhs13_EN`) |
| Chinese | `*_CN` (e.g. `Majoko_dhl05_CN`) |
| Japanese | **No language suffix** (e.g. `Cafe_staff_dhs13`) |

Content is loaded from the **locale-specific** `localization-assets-*` bundle via Unity Localization / Addressables, **not** by appending `_ES` from code. Adding `es` means **new locale bundles** (and catalog entries), mirroring `en` or `zh-CN` naming convention (`_ES` or unsuffixed like `ja`).

### String / image tables

- `GetLocalizeString`: `TableReference` from table name + entry key → `LocalizedStringDatabase.GetLocalizedString` (Unity tables keyed by **entry id**, not `_EN` in code).
- `GetLocalizeAsset`: `LocalizedAssetDatabase.GetLocalizedAsset` with **`Image`** table + **sprite name** as entry reference (`LocalizedImage` passes `sprite.name` at offset `0xE0` in disasm).

**If only data added `es` tables/bundles but UI still sets `Languages` to 0/1/2:** Unity tables can work for `SelectedLocale = es`, but custom `OnLanguageUpdate(Languages)` and `LocalizeManager.language` must stay consistent (see §5).

---

## 3. Fonts (TMP)

Scan: TMP `MonoBehaviour` assets with `m_AtlasPopulationMode` / `m_CharacterTable` in built-in assets + Addressables bundles.

| Font | Atlas mode | Spanish test chars `áéíóúñü¿¡ÁÉÍÓÚÑ` |
|------|------------|----------------------------------------|
| **Honoka_Shin_Mincho_L SDF** (+ Variant) | **1 = Dynamic** | **None missing** (large CJK set; has fallback table entry) |
| **Roboto-Italic-VariableFont_wdth,wght SDF** | **0 = Static** | **None missing** |
| **LiberationSans SDF** (+ Fallback) | Static + dynamic fallback | **None missing** on main static set |
| **Corporate-Mincho-ver2 SDF** | **1 = Dynamic** | **All 15 Spanish chars missing** from baked table (dynamic may still render if atlas expands at runtime — verify in-game) |

**Per-language font switch:** `LocalizeTextFont.OnLanguageUpdate` (RVA `0x39580`) calls `GetLocalizeAsset<Font>("Image", originalFont)` — fonts are **Image asset table** entries per locale, not a separate code path per language.

**Minimal fix for Spanish UI:** Prefer **Roboto** / **LiberationSans** for Spanish text, or extend **Corporate-Mincho** glyph set / assign a **dynamic fallback** TMP font with Latin Extended-A in the `es` **Image** table (or shared fallback chain in TMP settings).

---

## 4. Other language-dependent behavior

| Area | Notes |
|------|--------|
| **Voice** | `Config` / `ConfigPage` expose **voice volume**; H-scenes use `HSceneController` + locale bundle **TextAsset** JSON (`voice` / `text` fields). Voice language follows **selected locale’s asset bundle**, not a separate code switch. |
| **Subtitles / dialogue** | Mix of Unity `Translation_*` tables + custom `LocalizedTextTMPro` + dialogue graph assets. |
| **Video** | No dedicated locale video class found in custom game code search. |
| **`Application.systemLanguage`** | Used by Unity `SystemLocaleSelector` at startup only (RVA `0x289AD00`). |
| **Fixed-width / legacy UI** | `LocalizedSprite.translated[]` — **3-element** sprite array indexed by `Languages` (hard-coded trio). |
| **Input / guides** | Bundles include `controller_guide` TMP-related assets (separate from Honoka/Corporate fonts). |

---

## 5. Making `es` selectable — options and recommendation

### (a) Data-only (Addressables + prefs)

**Requires:**

- New `Locale` asset `es`, `Translation_es`, `Image_es`, `localization-*-spanish(es)_*` bundles, catalog/hash updates.
- PlayerPrefs / `SelectedLocale` = `es` (manual or tool).

**Blockers without code/asset UI edits:**

- **`Languages` enum fixed at 3** — Visual Scripting / dropdown likely sets `LocalizeManager.language` ∈ {0,1,2} only.
- **No `es` menu label** unless scene/prefab dropdown options edited.
- **`LocalizeManager.Start`** may force `AvailableLocales[1]` on the manager’s scene load — test order vs. PlayerPrefs.
- Custom components need **`OnLanguageUpdate`** with a valid `Languages` value; `es` is not representable.

**Verdict:** Data-only is **insufficient** for a polished fourth menu language; OK for **dev testing** via forcing `SelectedLocale` + matching `language` field.

### (b) Hijack an existing locale (recommended simplest)

Replace **`en`** or **`zh-CN`** Addressables content with Spanish while keeping codes **`en`** / **`zh-CN`**.

| Pros | Cons |
|------|------|
| No GameAssembly patch | Menu still says English / Chinese |
| `Languages` enum and VS graphs unchanged | Must keep `_EN` or `_CN` asset naming conventions respectively |
| Unity + custom `LocalizeManager` stay aligned when user picks that slot | Player expects “English” but gets Spanish |

**Best balance:** Hijack **`en`** (English): custom code treats `EN=1` as “non-JP translation path”; English bundle already uses `_EN` TextAssets and `Image_en` — replace strings/sprites/audio JSON with Spanish under same keys/codes.

### (c) Code mod (MelonLoader / BepInEx IL2CPP / patched DLL)

Needed for a **real fourth option “Español (es)”**:

- Extend or replace `Languages` usage (4+ values) in UI graphs or hook dropdown → set `LocalizeManager.language` + `LocalizationSettings.SelectedLocale` for `es`.
- Patch or disable **`LocalizeManager.Start`** locale override if it fights PlayerPrefs.
- Optionally hook `PlayerPrefLocaleSelector` key or write `es` directly.

| Pros | Cons |
|------|------|
| Proper `es` code and UI label | Maintenance per game update |
| Clean UX | IL2CPP plugin toolchain required |

### Recommended plan (practical)

1. **Short term (ship patch):** **(b) Hijack `en`** — Spanish content in English Addressables + string tables; players choose **English** in menu. Verify fonts (Corporate-Mincho vs Roboto/Honoka) in UI.
2. **Medium term:** Build full **`es`** locale data anyway (clean authoring pipeline).
3. **Long term (optional):** **(c)** small IL2CPP plugin to add dropdown entry, map `es` ↔ `Languages` (e.g. reuse `EN=1` internally or extend enum) and sync `SelectedLocale` + `PlayerPrefs`.

---

## Key evidence summary

| Question | Answer |
|----------|--------|
| UI class | No `LanguageSettings` C# class; `ConfigPage` has no language; custom `Languages` enum + `LocalizeManager` + Unity `LocalizationSettings` |
| Hard-coded 3? | **Yes** — `Languages` {JP, EN, SCH}; legacy arrays (e.g. `LocalizedSprite.translated[3]`) |
| Enumerate `AvailableLocales`? | **Not in game C#** for menu; Unity APIs exist but menu is VS/scene-driven |
| Persistence | **PlayerPrefs** via `PlayerPrefLocaleSelector`; **`ConfigSave` does not store language** |
| `_EN` selection | **Per-locale Addressables bundle**, not `_{code}` in IL2CPP |
| `es` + `_ES` in code | **No** suffix logic in code; `_ES` would be a **content naming choice** in Spanish bundles only |

---

## Artifacts in `translation/research/`

- `il2cpp_dump/` — full Il2CppDumper output  
- `disasm_localize.txt`, `disasm_localize.py`, `disasm_playerpref.py`  
- `localization_settings.json`, `inspect_localization_settings.py`  
- `tools/Il2CppDumper/` — dumper binary  
- `REPORT.md` — this file  
