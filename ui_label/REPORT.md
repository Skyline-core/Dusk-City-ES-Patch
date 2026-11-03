# Language menu label — UI / locale report

**Game:** Dusk City v2.02 (Unity IL2CPP, Addressables 1.22.3)  
**Scope:** Read-only on `Dusk City_Data`; artifacts under `translation/ui_label/`  
**Date:** 2026-11-02

---

## Executive summary

| Question | Answer |
|----------|--------|
| Where do menu language names come from? | **`Locale` assets** in `localization-locales_assets_all.bundle` (`m_LocaleName` / `m_Name`). Not from `Translation_*` tables or TMP dropdown serialized options. |
| English slot label today | **`English (en)`** on locale `path_id` **`-1395074884649563235`**, code **`en`**. |
| Recommended patch for “Español” | Set **`m_LocaleName`** to **`Español`**; keep **`m_Identifier.m_Code`** = **`en`**. Prototype: `patch_language_label.py` → `out/localization-locales_assets_all.bundle`. |
| Language dropdown UI asset | Addressables bundle **`741042f98eeaab65c8941174724e3496.bundle`**, GameObject **`Dropdown`**, **`TMP_Dropdown`** `path_id` **`-7104408855834432269`** (placeholder options **Option A/B/C**, filled at runtime). |
| Sprites for labels? | **No** — text from locale names. |
| `es_source.json` | **No** entries for English / 日本語 / language menu strings. |

---

## 1. Scan coverage

| Location | Needles found |
|----------|----------------|
| **7838** `.bundle` files (+ DLC) + `globalgamemanagers*` / `resources.assets` / `sharedassets*` / `level0` | Only **`localization-locales_assets_all.bundle`** contains **`English`** / **`English (en)`**. No **`日本語`**, **`简体中文`**, or bare **`English`** in any other bundle binary scan. |
| `globalgamemanagers.assets` | Substrings **`Language`**, **`TMP_Dropdown`**, **`LocalizeManager`**, **`PlayerPrefLocaleSelector`**, **`Localization Settings`** (type names / built-in refs, not menu copy). |
| Visual Scripting | **98** bundles reference VS types; **none** in the language UI bundle contain **`LocaleName`** / **`LocalizeManager`** strings. |

Scripts: `scan_language_ui.py`, `binary_scan_extended.py`, `find_language_objects.py`, `scan_vs_locale.py`.

---

## 2. Language-selection UI (prefab / scene)

### Addressables

| Field | Value |
|-------|--------|
| **Bundle file** | `741042f98eeaab65c8941174724e3496.bundle` |
| **Catalog** | `internal_id` index **3578** → runtime path `…\StandaloneWindows64\741042f98eeaab65c8941174724e3496.bundle` |
| **AssetBundleRequestOptions** (catalog dump) | `m_BundleName` **`06b645db830c32436da005e3a88a1a66`**, **`m_Crc`** **404721431**, **`m_Hash`** **`456fb3e0b933f5545d3ef7f64149be26`** |

Large shared UI bundle (config/title/pause UI; LiberationSans-heavy per font research).

### Dropdown object

| Object | `path_id` | Type | Notes |
|--------|-----------|------|--------|
| **`Dropdown`** | **`-1538232607231808269`** | GameObject | Language UI control (name is generic; not resolution dropdown). |
| TMP dropdown | **`-7104408855834432269`** | MonoBehaviour (`TMPro.TMP_Dropdown`) | **`m_Options.m_Options[].m_Text`**: **`Option A`**, **`Option B`**, **`Option C`** (Unity template; **not** shipped language names). **`m_OnValueChanged`**: empty persistent calls (logic elsewhere, likely Visual Scripting / scene wiring). |
| Input helper | **`5402053862990179571`** | `StrayCatLab.Game.UISound` | SE on select. |
| Input helper | **`-8961996047486980877`** | `PauseMenuDropdownClicker` | Custom pause-menu pointer hit testing for dropdowns. |

**Resolution dropdowns** (unrelated): GameObject **`DropdownWindowSize`** in the same and duplicate config bundles (`57cd5f06…`, `79adeac0…`, etc.) with **`1920×1080`** options.

**Patchability:** Changing menu labels **via this TMP_Dropdown asset is wrong target** — runtime overwrites options from locales. Optional string patch of placeholders would **not** affect the live menu.

**Images:** No language icon sprites tied to the dropdown; caption uses TMP text populated at runtime.

---

## 3. Authoritative language **names** (patch target)

### Bundle: `localization-locales_assets_all.bundle`

| Catalog ABRO | `m_BundleName` **`4e9fbff37d7e4eef9b5131df960f6937`**, **`m_Crc`** **4043063053**, **`m_Hash`** **`25f81ff8884b1f4fcb45a11eaa1625f7`**, bucket **`localization-locales_assets_all_25f81ff8884b1f4fcb45a11eaa1625f7.bundle`**. |

| Locale | `path_id` | Type | `m_Identifier.m_Code` | Field | Current value |
|--------|-----------|------|------------------------|-------|----------------|
| Japanese | **`-8391707851027967870`** | `Locale` MonoBehaviour | **`ja`** | **`m_LocaleName`**, **`m_Name`** | **`Japanese (ja)`** |
| **English (hijack slot)** | **`-1395074884649563235`** | `Locale` MonoBehaviour | **`en`** | **`m_LocaleName`**, **`m_Name`** | **`English (en)`** → patch to **`Español`** |
| Chinese | **`3537767062343353821`** | `Locale` MonoBehaviour | **`zh-CN`** | **`m_LocaleName`**, **`m_Name`** | **`Chinese (Simplified) (zh-CN)`** |

Container paths (unchanged when only renaming display):

- `Assets/Localize/English (en).asset` → English locale object above  
- `Assets/Game/Localization/Locales/Japanese (ja).asset`  
- `Assets/Localize/Chinese (Simplified) (zh-CN).asset`

**Kind:** **Text** — patch via UnityPy typetree (`m_LocaleName`; optionally `m_Name` with `--rename-asset`).

**Unity Localization tables:** **`Translation_en` / `Translation_ja` / `Translation_zh-CN`** exist but **`es_source.json`** has **no** language-menu keys; menu names are **not** `LocalizeStringEvent` entries for this project.

**Catalog address keys:** Bucket **`English (en)`** still points at `Assets/Localize/English (en).asset` (see `catalog_tool/README.md`). Renaming only **`m_LocaleName`** keeps asset / address stability; renaming **`m_Name`** would need catalog updates.

---

## 4. Prototype patch (no game writes)

```powershell
& "C:\Users\ah_3m\AppData\Local\Programs\Python\Python312\python.exe" `
  "translation\ui_label\patch_language_label.py"
```

| Item | Value |
|------|--------|
| **Output** | `translation/ui_label/out/localization-locales_assets_all.bundle` |
| **Compression** | **LZ4** (`UnityFS`, same as `bundle_builder`) |
| **Verify** | Re-load bundle; **`m_LocaleName`** = **`Español`**, **`m_Code`** still **`en`**, **`m_Name`** still **`English (en)`** unless `--rename-asset` |
| **Result JSON** | `out/patch_language_label_result.json` (includes new **MD5** **`2974834d1d22c2ec21d5f1519c974ef4`** for patched locales bundle) |

### Catalog CRC / hash after bundle edit

Unity Addressables **`AssetBundleRequestOptions`** on the catalog location:

- **`m_Crc`**: if non-zero, Unity can **reject** a modified bundle whose bytes no longer match.
- **`m_Hash`**: content hash (MD5 of bundle bytes in this project’s tooling).

**If you deploy a patched locales bundle:**

1. Update catalog entry for **`localization-locales_assets_all_25f81ff8884b1f4fcb45a11eaa1625f7.bundle`**: set **`m_Hash`** to MD5 of new bytes (`abro_update_bundle` in `catalog_tool/serialization.py`), **or**
2. Set **`m_Crc`** to **`0`** and **`m_UseCrcForCachedBundles`** to **`false`** via **`abro_set_crc_zero()`** (supported in `catalog_tool`) so CRC checking does not block the edit.

Shipped locales row: **`m_Crc=4043063053`**, **`m_Hash=25f81ff8884b1f4fcb45a11eaa1625f7`** — editing without catalog update **will fail CRC check** when CRC verification is enabled.

---

## 5. Startup locale & consistency with `Languages` enum

| Mechanism | Detail |
|-----------|--------|
| **`Languages` enum** | **`JP=0`**, **`EN=1`**, **`SCH=2`** (`LocalizeManager.language`). No **`ES`**. |
| **Hijack `en` slot** | Player picks dropdown index **1** / locale code **`en`** → **`Languages.EN`** and **`SelectedLocale` code `en`** stay aligned; content comes from English-addressables replaced with Spanish. |
| **`LocalizeManager.Start`** (RVA **`0x39430`**) | Sets **`LocalizationSettings.SelectedLocale`** from **`AvailableLocales.Locales[1]`** (typically **English** if order is ja/en/zh-CN). Can override first-run before PlayerPrefs apply. |
| **`PlayerPrefLocaleSelector`** | Referenced in **`globalgamemanagers.assets`** binary (class name present); serialized **`Localization Settings`** asset not exposed via UnityPy typetree in this dump. Unity package default prefs key is usually **`SelectedLocale`** (store locale code **`en`**, **`ja`**, **`zh-CN`**). Registry: **`HKCU\Software\すてねこLAB.\Dusk City`**. |
| **`SystemLocaleSelector`** | Maps **`Application.systemLanguage`** at startup (RVA **`0x289AD00`**). |
| **`ConfigSave` / `ConfigPage`** | **No** language field (volume/display only). |

Replacing English **content** while keeping **`en`** code and patching **`m_LocaleName`** to **`Español`** preserves enum and localization API consistency for the hijack strategy.

---

## 6. Related artifacts

| File | Purpose |
|------|---------|
| `patch_language_label.py` | Patch + verify locales bundle |
| `out/localization-locales_assets_all.bundle` | Patched prototype |
| `dropdown_scripts.json` | Dropdown component script resolution |
| `inspect_bundles.json` | Locale + UI toolkit hits |
| `language_objects.json` | All locale/dropdown-related UnityPy hits |
| `scan_results.json` | Full-file binary needle summary |

---

## 7. Deployment checklist (when integrating with patch pipeline)

1. Replace shipped **`localization-locales_assets_all.bundle`** (or merge **`m_LocaleName`** change into your hijacked locales build).
2. Update **`catalog.json`** hash and/or zero CRC for that bundle entry.
3. Do **not** rely on editing **`741042…`** TMP **`m_Options`** — runtime fills from **`Locale.LocaleName`**.
