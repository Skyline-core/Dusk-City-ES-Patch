# GameScript text extraction (Dusk City)

Story/CG/event dialogue lives in **GameScript** `MonoBehaviour` assets (`m_commandDatas` token lists) inside Addressables bundles. This folder produces the translator source and patch references consumed by `translation/script_injector/inject_scripts.py`.

## Outputs

| File | Purpose |
|------|---------|
| `../es_source_scripts.json` | Deduplicated strings (`en` → fill `es`; optional `ja` hint) |
| `../research/script_refs.json` | Per-id bundle locations + `_bundles` CRC metadata |
| `extract_script_texts.py` | Regenerate both files (read-only on game data) |
| `other_text_scan.json` | Sample scan of non–GameScript English strings (report only) |

## Regenerate

```powershell
$env:DUSK_GAME_PATH = "E:\Users\ah_3m\Documents\gits\Dusk City"
& "C:\Users\ah_3m\AppData\Local\Programs\Python\Python312\python.exe" `
  "translation\script_texts\extract_script_texts.py"
```

Only bundles listed in `Dusk City_Data/StreamingAssets/aa/catalog.json` are included (453 GameScript bundles with catalog CRC; 209 survey bundles are stale leftovers on disk).

## Numbers (active catalog)

| Metric | Value |
|--------|------:|
| Unique texts (`es_source_scripts.json`) | 3818 |
| Total literal uses | 5095 |
| Bundles referenced | 433 |
| `say` | 3640 unique / 4191 uses |
| `speaker` (`add_speaker` + `set_speaker`) | 62 / 667 |
| `choice` | 56 / 111 |
| `item` | 60 / 126 |
| `ja` hints filled | 49 (JP-only literals + H-scene table matches) |

## Command classification

Token layout is usually `cmdName(arg1, arg2, …)`. Type **46** tokens are string literals. Character tags (`mog`, `sic`, `non`, `tip`, …) are a **separate command line** with the tag name repeated at **tok 2** — not player text.

| Command | Tok | Translatable? | Notes / examples | Literal count (active) |
|---------|-----|---------------|------------------|------------------------:|
| `say` | 2, 9, … | **Yes** | Dialogue; includes `<sprite>`, `<wait>`, `「」`. Multiple string tokens when the line uses concatenation (`say("part1" + … + "part2", voice)`). | 4188 + 1 @ tok 9 |
| `say` | 4 (typical) | **No** | Voice id (`est0066`, `his0001`, `DLC1_synthesis0001`) | 2863 |
| `add_speaker` | 4 | **Yes** | Display name (`The mayor`, `<color=#00aeff>TIPS!`) | 657 |
| `add_speaker` | 6 | **No** | Internal puppet id (`pa_maj`, `pa_kun`) | 269 |
| `set_speaker` | 2 | **Yes** | Single display name (`Mechanical voice`) | 10 |
| `add_choice_option` | 2 | **Yes** | Choice label (`Yes`, `4F`, long puzzle answers) | 111 |
| `itemName` | 2 | **Yes** | Obtained-item name shown in message | 126 |
| `mog`, `sic`, `non`, `tip`, `dec`, `mjk`, … | 2 | **No** | Character/scene command tag (same string as command) | 276–77 each |
| `play_timeline_section` | 4 | **No** | Section id (`sec004`) | 79 |
| `set_puppet_emo` | 4 | **No** | Emotion clip id (`kun_clo_egao_all`) | 547 |
| `screen_flash` | 4 | **No** | Color (`#FFFFFF`) | 165 |
| `fadein_world` / `fadeout_world` | 6 | **No** | Color (`#000000FA`) | 36 each |
| `set_game_flag_*`, `set_gamemode_variable_*`, `set_reminiscence_flag` | 2 | **No** | Flag / variable names | 23–32 |
| `set_h_scene_clip`, `play_se`, `refuseFlag` | 2 / 4 | **No** | Internal clip / SE ids | 1–14 |
| `if`, `switch`, `elseif`, `osakanaCount`, … | 4 | **No** | Script variable names | 1–18 |

Full per-command listing: run `extract_script_texts.py` and inspect `extraction_stats.json`, or re-run the survey analyzer in `research/scan_gamescripts.py`.

## Where `TIPS!` comes from

Not Unity Localization and not a TMP prefab string in this project path. Tutorial scripts call `tip` (command tag at tok 2), then **`add_speaker` with display text `<color=#00aeff>TIPS!` at tok 4** (e.g. script `cut000_op0_Tutorial`, bundle `StandaloneWindows64/57634e2f30475130f36204fc43fd488a.bundle`, path_id `117`, line `4`, tok `4` — text id **415** in `es_source_scripts.json`, 20 uses across tutorial scenes).

## Not handled yet

- **Unity Localization tables** — already covered by `es_source.json` / table patch bundles.
- **H-scene `HSceneTexts` assets** — covered by `es_source.json` `scripts` section (2385 lines), not GameScript tokens.
- **TMP `m_text` / UI prefab strings** in scene bundles — not extracted (injector only patches GameScript `m_commandDatas` Type 46 literals). Sample scan of 80 GameScript bundles found ~1.7k incidental English strings in Visual Scripting graphs (`controlInput`, etc.), not player-facing copy.
- **Stale bundles** — 209 `gamescripts_survey.json` entries have no catalog location; ignored.
- **Injector note:** Addressables loads pull dependency CABs; **`path_id` is only unique per serialized file**. Patching must resolve the `MonoBehaviour` that actually owns `m_commandDatas` (see `find_gamescript_tree` in `extract_script_texts.py`).

## Validation

After filling `es`:

```powershell
& "C:\Users\ah_3m\AppData\Local\Programs\Python\Python312\python.exe" `
  "translation\validate_scripts_translation.py" "translation\es_source_scripts.json"
```

Checks: same ids, `en`/`ja` unchanged, non-empty `es`, markup/`\\n`/`\\u3000`/`「」` preserved (same rules as `validate_translation.py`).
