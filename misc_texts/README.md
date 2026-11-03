# Misc text pipeline

Player-visible strings outside dialogue graphs, GameScripts, and `Translation_en` tables: interactables, item data, TMP labels, debug UI templates, locale display names.

## Extract (read-only game)

```powershell
$env:DUSK_GAME_PATH = "G:\SteamLibrary\steamapps\common\Dusk City"
python translation\misc_texts\extract_misc_texts.py
```

Outputs:

- `translation/es_source_misc.json` — fill `es` (IDs from 200000)
- `translation/es_source_misc.original_vacio.json` — pristine copy
- `translation/research/misc_refs.json` — bundle locations + catalog CRCs

Uses `translation/research/remaining_text/candidates.json` locations (no full-game rescan).

## Inject

Runs after `inject_scripts.py` / `inject_dialogues.py`; reads chained bundles from `translation/patch_en_slot/files/` when present.

```powershell
python translation\misc_texts\inject_misc_texts.py
```

Test (temp output dir, prefix `ES: `, CRC self-test):

```powershell
python translation\misc_texts\inject_misc_texts.py --use-test-source --limit 5 --self-test --out translation\misc_texts\_test_out
```

Forges each bundle to its original catalog `m_Crc` via `bundle_builder/crc_forge.py`.
