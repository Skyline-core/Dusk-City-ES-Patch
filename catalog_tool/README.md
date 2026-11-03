# Addressables catalog tool (Dusk City)

Python utilities to **decode**, **re-encode**, and **extend** the Unity Addressables `ContentCatalogData` in `catalog.json` (Addressables **1.22.x** JSON catalog format). Used for the Spanish (`es`) translation patch without modifying `Dusk City_Data`.

## Unity Localization key model (this project)

| Role | Typical addressable / bucket key | `internalId` (asset path) |
|------|----------------------------------|---------------------------|
| Locale identifier label | `Locale-en` (all assets tagged for English) | many `_EN` paths + `Translation_en` + `Image_en` |
| Locale list label | `Locale` | `Assets/Localize/English (en).asset`, `Japanese (ja)`, `Chinese (zh-CN)` |
| Locale by display name | `English (en)` | `Assets/Localize/English (en).asset` |
| Locale by GUID | `Hash128:c536477e…` | same locale asset |
| String table | `Translation_en` | `Assets/Localize/Translation_en.asset` |
| String table GUID | `Hash128:cfbb05c6…` | same |
| Asset table (localized sprites) | `Image_en` | `Assets/Localize/Image_en.asset` |
| Shared tables | `Translation Shared Data`, `Image Shared Data` | not locale-specific |
| Text JSON | `Cafe_staff_dhs13_EN` (asset **name**) | `Assets/Game/Json/.../Cafe_staff_dhs13_EN.json` |
| Localized textures | `Tips_1_EN` | `Assets/Game/Sprites/.../Tips_1_EN.png` (often 2 entries: Texture2D + Sprite) |
| English asset bundle | `localization-assets-english(en)_assets_all_2226d8d2….bundle` | runtime path to `.bundle` |
| String-table bundle | `localization-string-tables-english(en)_assets_all_8954925c….bundle` | runtime path |
| Asset-table bundle | `localization-asset-tables-english(en)_assets_all_9084a065….bundle` | runtime path |
| Locales bundle | `localization-locales_assets_all_25f81ff8….bundle` | runtime path |

**How Unity resolves content:** the runtime looks up a **bucket key** (address, label, locale code, or GUID). Each bucket points at one or more **resource locations**. Each location has a `primary_key` (usually the same string as the bucket key), an `internalId` (asset path or bundle path), optional `dependency_key` (parent bundle hash name), provider id, and optional `AssetBundleRequestOptions` in extra data (`m_Crc`, `m_Hash`, `m_BundleName`, …).

**`*_EN` TextAssets:** catalog entries use the **short asset name** as the bucket key (e.g. `Cafe_staff_dhs13_EN`), not the full `Assets/Game/Json/…` path. The full path is the location `internalId`. Provider is `BundledAssetProvider`; dependency is the English localization-assets bundle hash key.

## Exact English set mirrored for `es`

`clone-locale` duplicates every bucket selected by `collect_en_mirror_locations()`:

- **3** English localization **bundle** buckets (assets / string-tables / asset-tables).
- **1** `Locale-en` label bucket (**231** locations: 53 TextAssets + 88×2 Texture/Sprite pairs + table assets).
- **1** each: `English (en)`, `Translation_en`, `Image_en`.
- **2** GUID buckets for locale + string table assets.
- **~141** per-asset name buckets ending in `_EN` (TextAssets and sprites).
- **`Locale` bucket:** appends one new location for `Assets/Localize/Spanish (es).asset` (does not clone the whole bucket).

Spanish counterparts use `_ES` / `Translation_es` / `Image_es` / `Locale-es` / `Spanish (es)` and new bundle file names (defaults below). GUID buckets get **deterministic placeholder** `Hash128` values (`md5("es:" + enGuid)`) until bundle tooling assigns real GUIDs.

Run `list-en-mirror` or inspect `out/en_mirror_report.json` for the full per-location listing from your catalog.

## Commands

Use Python 3.12 at:

`C:\Users\ah_3m\AppData\Local\Programs\Python\Python312\python.exe`

From `translation\catalog_tool`:

```powershell
# Mandatory: unchanged catalog round-trip (returns identical base64 blobs)
python catalog_tool.py roundtrip

# Dump localization-related locations + *_EN asset key report
python catalog_tool.py dump

# List JSON report of en template locations
python catalog_tool.py list-en-mirror

# Build patched catalog under out\ (does NOT touch game folder)
python catalog_tool.py clone-locale --from en --to es

# Phase-1 en-slot hijack: zero CRC on 3 English localization bundles only
python catalog_tool.py patch-crc
# Writes translation\patch_en_slot\catalog.json and StandaloneWindows64\catalog_2026.06.23.02.23.07.hash
```

Optional JSON inputs:

- `--bundle-map path.json` — map `internalId` or bundle path → new runtime bundle path.
- `--bundle-hashes path.json` — map `m_BundleName` → new `m_Hash` in `AssetBundleRequestOptions`.
- `--keep-crc` — leave CRC checks enabled (default: **zero CRC** and disable cached-bundle CRC for localization bundles).

Default new bundle file names (override via `--bundle-map` / CLI flags):

| Purpose | Default file name |
|---------|-------------------|
| Locale asset | `localization-locales-es_assets_all.bundle` |
| String tables | `localization-string-tables-spanish(es)_assets_all.bundle` |
| Asset tables | `localization-asset-tables-spanish(es)_assets_all.bundle` |
| Localized assets | `localization-assets-spanish(es)_assets_all.bundle` |

## Module layout

| File | Purpose |
|------|---------|
| `serialization.py` | `SerializedObjectDecoder` v1 types (ASCII/UTF-16 strings, int, Hash128, JsonObject / AssetBundleRequestOptions) |
| `catalog_data.py` | `Catalog` decode/encode, `clone_locale`, mirror helpers |
| `catalog_tool.py` | CLI |
| `test_roundtrip.py` | Asserts byte-identical blobs on read-only catalog |

## Binary format (Addressables 1.22 JSON catalog)

After base64 decode:

1. **Bucket data** — `int32 count`; per bucket: `int32 keyOffset`, `int32 entryCount`, `entryCount × int32` location indices.
2. **Key data** — `int32 count` (= bucket count); at each bucket offset: type byte + serialized key object.
3. **Entry data** — `int32 count`; per entry **7× int32**: internalIdIndex, providerIndex, dependencyKeyIndex, depHash, dataIndex, primaryKeyIndex, resourceTypeIndex.
4. **Extra data** — per-entry blob at `dataIndex`; usually JSON `AssetBundleRequestOptions` for bundles.

**Round-trip:** if the catalog is not modified (`dirty=False`), encode returns the **original four base64 strings unchanged** (verified by `roundtrip` / `test_roundtrip.py`). Modified catalogs rebuild all four blobs.

## Deployment risks

- **Catalog hash:** `Dusk City_Data/StreamingAssets/aa/settings.json` points at `catalog_2026.06.23.02.23.07.hash`. If you replace `catalog.json` in the game, you must update or replace that **hash file** (and keep naming consistent with settings) or Addressables may keep using a cached catalog.
- **GUID keys:** Spanish locale/table GUID buckets use placeholders until bundles contain matching Unity GUIDs; align with your bundle build tool or pass real GUIDs via a future map file.
- **CRC / hash:** patched bundles must match `AssetBundleRequestOptions` or use CRC 0 + disabled cached CRC (default in `clone-locale`).
- **Encoder:** dirty re-encode requires every location `primary_key` and `dependency_key` to exist as a bucket key index; clone-locale adds buckets before writing.
