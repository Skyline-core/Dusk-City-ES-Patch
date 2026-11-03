# Dusk City — Spanish (es) font / glyph coverage report

**Scan date:** 2026-11-02  
**Scope:** Read-only analysis of `Dusk City_Data` (7834 Addressables bundles + static `resources.assets` / `sharedassets*.assets`).  
**Spanish test set:** `áéíóúüñÁÉÍÓÚÜÑ¿¡«»…—'"`

## Executive summary

Spanish dialogue/UI can be rendered with **no font patch** in the typical case:

| Priority font | UI usage (TMP `m_fontAsset` refs) | Pre-baked Spanish in TMP atlas? | Source TTF/OTF cmap |
|---------------|-----------------------------------|----------------------------------|---------------------|
| **Honoka_Shin_Mincho_L SDF** | **206** (primary) | **All test chars present** (Dynamic, 1953 glyphs) | Full Latin (`Honoka_Shin_Mincho_L.otf`) |
| **Corporate-Mincho-ver2 SDF** | **121** | **Not pre-baked** (Dynamic, 473 glyphs; only `…` and `'`) | **Full Latin** (`Corporate-Mincho-ver2.ttf`, 10 058 cmap entries) |
| **LiberationSans SDF** | **93** | **All test chars** (Static, 250 glyphs) | Full Latin |
| **Roboto-Italic-VariableFont_wdth,wght SDF** | **10** | **All test chars** (Static) | N/A (SDF only in bundle) |

**Language / locale:** Unity Localization locales (`en`, `ja`, `zh-CN`) have **empty** `references` tables — **no per-locale TMP font swap**. `LocalizedTextTMPro` only updates string text; fonts stay whatever is on the prefab. **All languages share the same TMP font assignments.**

**Recommendation:** **(a) Nothing required** before shipping Spanish strings. Optionally **verify in-game** one line using Corporate-Mincho UI (121 components) with `¿¡áéíóúüñ`. If any tofu appears (unlikely with Dynamic + in-bundle TTF), use **(c)** below on `Corporate-Mincho-ver2 SDF` only.

---

## Fonts discovered (unique gameplay-relevant)

### TMP_FontAsset (SDF)

| Asset name | Atlas mode | Glyphs | Bundle(s) | path_id (in primary bundle) | Fallbacks |
|------------|------------|--------|-----------|-------------------------------|-----------|
| Honoka_Shin_Mincho_L SDF | Dynamic | 1953 | `7d1fbb8bac9eb574f5f021e9c38ee832.bundle` | `8683220474330829292` | unset (`fileID:None`) |
| Honoka_Shin_Mincho_L SDF - Variant | Dynamic | 1600 | same | `6643940104961264058` | none |
| Corporate-Mincho-ver2 SDF | Dynamic | 473 | `ad133aaa6b7c43f15f99cf476d087942.bundle` (+ duplicates `121d3c6379ed30ebc6d9a254f9082f6e.bundle`, `1cb01258f20cc5754bb7ac20a2d0ffc3.bundle`) | `-3674763128401292280` | none |
| LiberationSans SDF | Static | 250 | `57cd5f06fa66144e14ab0ce0f58d3e01.bundle` (+ several duplicate TMP resource bundles) | `67` | unset |
| LiberationSans SDF - Fallback | Dynamic | 0 (empty atlas) | same as LiberationSans | `68` | none |
| Roboto-Italic-VariableFont_wdth,wght SDF | Static | 412 | `3a7b609e999f6d3fdc182498460fe62d.bundle` (+ 3 duplicate bundles) | `61` | none |

### Embedded TTF/OTF (`Font` objects)

| File name | Bundle | Spanish in cmap |
|-----------|--------|-----------------|
| Honoka_Shin_Mincho_L.otf | `85bf13179bb6b147134bc8a1540a9b1d.bundle` | Yes (all test chars) |
| Corporate-Mincho-ver2.ttf | `ad133aaa6b7c43f15f99cf476d087942.bundle` | Yes |
| LiberationSans.ttf | `resources.assets`, `ad133aaa…bundle` | Yes |
| NotInter-Regular, Roboto-Bold, Roboto-Regular | `7ff7bbb50d8963f8cfda64e43d946131.bundle` | Yes (not referenced by TMP UI scan) |
| PerfectDOSVGA437 | `resources.assets` | Yes (legacy/debug) |

Addressables catalog paths: `Assets/Game/Fonts/Honoka_Shin_Mincho_L SDF.asset`, `Corporate-Mincho-ver2 SDF.asset`, `Assets/TextMesh Pro/Fonts/LiberationSans.ttf`, etc. (see `translation/fonts/out/catalog_font_hits.json` from catalog tool pattern search).

---

## Spanish character coverage (TMP `m_CharacterTable`)

Legend: **Y** = glyph in atlas, **N** = not pre-baked (may still render if Dynamic + source font).

| Char | Honoka SDF | Corporate SDF | Liberation SDF | Roboto Italic SDF |
|------|------------|---------------|----------------|-------------------|
| á é í ó ú ü ñ | Y | N | Y | Y |
| Á É Í Ó Ú Ü Ñ | Y | N | Y | Y |
| ¿ ¡ « » | Y | N | Y | Y |
| … — ' " | Y | Y / N / Y / Y | Y | Y |

Corporate: only `…` and `'` are pre-baked; **all other Spanish letters rely on Dynamic atlas expansion** from `m_SourceFontFile` → `Corporate-Mincho-ver2` (`m_PathID` `6058918421160262509` in the same bundle).

Honoka **Variant** SDF: same as Honoka — **all test chars Y** (1600 glyphs).

---

## TMP Settings & global fallback

- Catalog registers **`TMP Settings`** and **`Fonts & Materials/LiberationSans SDF`** / **`LiberationSans SDF - Fallback`** via `LegacyResourcesProvider` (built-in TMP resource pipeline, not a normal Addressables asset path).
- **`LiberationSans SDF - Fallback`** (Dynamic) points at embedded LiberationSans TTF (`m_PathID` `2716190411336593533` in `57cd5f…bundle`) with `characterSetSelectionMode: 1` and sequence including **`160–255`** (Latin-1 supplement). **`¿` (U+00BF)** is *outside* that sequence but the **primary** `LiberationSans SDF` static atlas **includes ¿**.
- A full **`TMP_Settings`** MonoBehaviour blob was **not** located in typetrees (likely resolved at runtime from Unity’s internal Resources). Expect default TMP behavior: missing glyphs try asset fallbacks, then global fallback assets.

---

## Which fonts dialogue / UI use

From a full scan of **7834** containers counting serialized `TextMeshPro` `m_fontAsset` references (resolving font names within each bundle):

| Resolved font | Reference count | Role |
|---------------|-----------------|------|
| Honoka_Shin_Mincho_L SDF | 206 | Main Japanese-style UI / dialogue typography |
| Corporate-Mincho-ver2 SDF | 121 | Secondary mincho UI |
| LiberationSans SDF | 93 | Generic TMP (includes large shared UI bundle `741042f98eeaab65c8941174724e3496.bundle`) |
| Roboto-Italic-VariableFont_wdth,wght SDF | 10 | Minor UI |

No `LocalizedTmpFont` assets appear in the Addressables catalog; **`LocalizedTextTMPro`** (game code) does not change fonts on language switch.

---

## Recommended fix

### Primary: **(a) No font patch**

- **Honoka** (majority of text): Spanish already in the dynamic atlas.
- **Corporate**: Dynamic mode + **complete Latin source TTF in the same bundle** → TMP should generate missing glyphs on first use.
- **Liberation / Roboto**: static atlases already complete.

**Verify:** After Spanish string tables load, open any scene that uses Corporate mincho and display:  
`¿¡ÁáÉéÍíÓúÚÜüÑñ«»…—'`  
If all glyphs render, stop here.

### If Corporate shows tofu: **(c) Pre-bake or expand Corporate atlas** (not Honoka)

**Asset:** `Corporate-Mincho-ver2 SDF` in  
`Dusk City_Data\StreamingAssets\aa\StandaloneWindows64\ad133aaa6b7c43f15f99cf476d087942.bundle`  
(apply the same change to duplicate bundles `121d3c6379ed30ebc6d9a254f9082f6e.bundle` and `1cb01258f20cc5754bb7ac20a2d0ffc3.bundle` if your patcher replaces all variants.)

**UnityPy approach (outline):**

1. `env = UnityPy.load("ad133aaa….bundle")`
2. Find `MonoBehaviour` with typetree `m_Name == "Corporate-Mincho-ver2 SDF"`.
3. `tree = obj.read_typetree()` — append Spanish codepoints to `m_CharacterTable` / `m_GlyphTable` / atlas textures (same layout as existing entries), **or** regenerate the asset in Unity Editor from `Corporate-Mincho-ver2.ttf` with character set including Spanish, then export the bundle.
4. `obj.save_typetree(tree)`; `with open(out_bundle, "wb") as f: f.write(env.file.save())`
5. Deploy patched bundle via your translation patch pipeline (do **not** write into `Dusk City_Data` during research).

**Prototype metadata (no game files modified):**  
`translation/fonts/out/Corporate-Mincho-ver2_SDF.meta.json`

### Optional: **(b) Add TMP fallback**

Add `LiberationSans SDF` (or `- Fallback`) to `m_FallbackFontAssetTable` on Honoka/Corporate assets. Cross-bundle PPtr references are fragile; prefer baking Spanish into Corporate or relying on global TMP fallback.

---

## Tools & outputs (this folder)

| Script | Purpose |
|--------|---------|
| `bundle_quick_scan.py` | Parallel type scan → 17 containers with Font/TMP |
| `font_usage_scan.py` | Global TMP font reference counts |
| `full_report_data.py` | Detailed JSON for unique TMP/TTF |
| `char_matrix.py` | Per-character Y/N matrix |
| `scan_fonts.py` | Initial scanner (catalog import optional) |

| Output | Content |
|--------|---------|
| `out/full_report_data.json` | Machine-readable full results |
| `out/Corporate-Mincho-ver2_SDF.meta.json` | Patch target metadata sample |

Re-run coverage after game updates:

```powershell
& "C:\Users\ah_3m\AppData\Local\Programs\Python\Python312\python.exe" "translation\fonts\full_report_data.py"
& "C:\Users\ah_3m\AppData\Local\Programs\Python\Python312\python.exe" "translation\fonts\char_matrix.py"
```

---

## Bundle hash reference (catalog bucket `498191146`)

Font-related Addressables bundles grouped in catalog:

- `7d1fbb8bac9eb574f5f021e9c38ee832.bundle` — Honoka SDF (+ variant)
- `85bf13179bb6b147134bc8a1540a9b1d.bundle` — Honoka OTF
- `ad133aaa6b7c43f15f99cf476d087942.bundle` — Corporate SDF + TTF + LiberationSans TTF + TMP shaders
