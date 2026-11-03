# Dialogue graph survey (Dusk City)

Game root: `G:\SteamLibrary\steamapps\common\Dusk City`
Bundles scanned: **7839** under `StreamingAssets/aa` (incl. DLC1/DLC2).

## Summary

| Metric | Count |
|--------|------:|
| Dialogue graph `MonoBehaviour` assets | 212 |
| Distinct graph `m_Name` values | 113 |
| Bundles containing ≥1 graph | 114 |
| Translatable string field uses (RefIds `data`) | 864 |
| Other `MonoBehaviour` with `references.RefIds` (not full graph) | 1590 |
| Bundles with **both** GameScript + dialogue graph | 75 |

### Translatable uses by kind

- **choice**: 854
- **message**: 10

## Dialogue graph asset shape

MonoBehaviours with typetree keys:
`m_GameObject`, `m_Enabled`, `m_Script`, `m_Name`, `edges`, `nodes`, `labelNodes`, `labels`, `groups`, `references`.

Node payloads live in `references.RefIds[i].data` with `references.RefIds[i].type.class` naming the node type
(namespaces `StrayCatLab.DialogueGraph`, `StrayCatLab.Game`, etc.).

Graph-level `labels[].labelName` (e.g. `Start`, `NewLabel`) is **editor-only** — not extracted.

## Node classes (instance counts)

| Class | Instances |
|-------|----------:|
| `ExecuteGameScriptNode` | 1176 |
| `ChoiseOptionNode` | 839 |
| `ChoiseConditionByFlag` | 722 |
| `IfDialogueNode` | 385 |
| `SetGameVariableBoolDialogueNode` | 383 |
| `LabelEventNode` | 302 |
| `ChoiseOptionConditionByLogical` | 265 |
| `ChoiseNode` | 238 |
| `?` | 155 |
| `ChoiseConditionByInt` | 151 |
| `LabelJumpNode` | 140 |
| `LaunchHScene` | 138 |
| `CheckWalletNode` | 114 |
| `DecreaseWalletNode` | 114 |
| `ChoiseConditionByCheckItem` | 110 |
| `AddItemNode` | 87 |
| `IsDLC1InstalledCondition` | 83 |
| `ChoiseConditionByCheckEjaculatable` | 80 |
| `RemoveItemNode` | 75 |
| `CheckInventoryItemMax` | 66 |
| `SetGameVariableIntDialogueNode` | 56 |
| `CompareGameVariables` | 49 |
| `RandomDialogueNode` | 34 |
| `SPWeaponUpgradeNode` | 24 |
| `DecrementGameVariableIntDialogueNode` | 22 |
| `ChoiseConditionByCheckEjaculate` | 21 |
| `DialogueBenchChoiseOption` | 15 |
| `SendGlobalEventDialogueNode` | 10 |
| `IncreaseWalletNode` | 9 |
| `SEDialogueNode` | 5 |
| `ShopSellNothingCheckNode` | 4 |
| `ShopBuyNode` | 4 |
| `ShopSellNode` | 4 |
| `BenchNakedCondition` | 3 |
| `AddWeaponUpgradeNode` | 3 |
| `DialogueBenchChoise` | 2 |
| `ExecuteSubgraph` | 2 |
| `IntCaseDialogueNode` | 2 |
| `SaveLoadDialogueNode` | 2 |
| `ChoiseOptionConditionInvert` | 2 |
| … | 5 more classes |

## String fields under `data` by class

### `AddItemNode`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `guid` | 87 | No (internal id / flag / key) | — |

### `AddWeaponUpgradeNode`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `guid` | 3 | No (internal id / flag / key) | — |

### `BenchCastOffDialogueNode`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `guid` | 1 | No (internal id / flag / key) | — |

### `BenchHugDialogueNode`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `guid` | 1 | No (internal id / flag / key) | — |

### `CheckInventoryItemMax`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `guid` | 66 | No (internal id / flag / key) | — |

### `CheckWalletNode`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `guid` | 114 | No (internal id / flag / key) | — |

### `ChoiseConditionByFlag`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `flagName` | 722 | No (internal id / flag / key) | — |

### `ChoiseConditionByInt`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `flagName` | 151 | No (internal id / flag / key) | — |

### `ChoiseNode`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `guid` | 238 | No (internal id / flag / key) | — |
| `interactableKey` | 238 | No (internal id / flag / key) | — |

### `ChoiseOptionNode`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `guid` | 839 | No (internal id / flag / key) | — |
| `text` | 839 | **Yes** | `Have a conversation`; `I have no business here`; `Do nothing` |

### `CompareGameVariables`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `lhs` | 49 | No | `count_iwashi`; `count_aji`; `count_aji` |
| `rhs` | 49 | No | `give_Iwashi`; `give_Aji`; `give_Aji` |

### `DecreaseWalletNode`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `guid` | 114 | No (internal id / flag / key) | — |

### `DecrementGameVariableIntDialogueNode`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `guid` | 22 | No (internal id / flag / key) | — |
| `entries[0].key` | 22 | No (game variable key) | — |

### `DialogueBenchChoise`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `guid` | 2 | No (internal id / flag / key) | — |

### `DialogueBenchChoiseOption`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `guid` | 15 | No (internal id / flag / key) | — |
| `text` | 15 | **Yes** | `Receive a hug`; `Physical examination`; `Get transferred` |

### `ExecuteGameScriptNode`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `guid` | 1176 | No (internal id / flag / key) | — |
| `scriptReference.m_AssetGUID` | 1176 | No (asset reference) | — |
| `scriptReference.m_SubObjectName` | 1176 | No (asset reference) | — |
| `scriptReference.m_SubObjectType` | 1176 | No (asset reference) | — |

### `ExecuteSubgraph`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `guid` | 2 | No (internal id / flag / key) | — |
| `startlabel` | 2 | No (internal id / flag / key) | — |

### `IfDialogueNode`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `guid` | 385 | No (internal id / flag / key) | — |

### `IncreaseWalletNode`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `guid` | 9 | No (internal id / flag / key) | — |

### `IntCaseDialogueNode`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `guid` | 2 | No (internal id / flag / key) | — |

### `LabelEventNode`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `guid` | 302 | No (internal id / flag / key) | — |
| `labelReference.guid` | 302 | No | — |

### `LabelJumpNode`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `guid` | 140 | No (internal id / flag / key) | — |
| `labelReference.guid` | 140 | No | — |

### `LaunchHScene`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `guid` | 138 | No (internal id / flag / key) | — |
| `positionKey` | 138 | No | — |
| `hideObjectKey` | 138 | No | — |
| `prefabReference.m_AssetGUID` | 138 | No (asset reference) | — |
| `prefabReference.m_SubObjectName` | 138 | No (asset reference) | — |
| `prefabReference.m_SubObjectType` | 138 | No (asset reference) | — |

### `RandomDialogueNode`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `guid` | 34 | No (internal id / flag / key) | — |

### `RemoveItemNode`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `guid` | 75 | No (internal id / flag / key) | — |

### `SEDialogueNode`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `guid` | 5 | No (internal id / flag / key) | — |

### `SPWeaponUpgradeNode`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `guid` | 24 | No (internal id / flag / key) | — |

### `SaveLoadDialogueNode`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `guid` | 2 | No (internal id / flag / key) | — |

### `SendGlobalEventDialogueNode`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `guid` | 10 | No (internal id / flag / key) | — |
| `message` | 10 | **Yes** | `Start_mjk`; `Draw_mog`; `Start_sic` |

### `SetGameVariableBoolDialogueNode`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `guid` | 383 | No (internal id / flag / key) | — |
| `entries[0].key` | 383 | No (game variable key) | — |
| `entries[1].key` | 19 | No (game variable key) | — |
| `entries[2].key` | 3 | No (game variable key) | — |
| `entries[3].key` | 3 | No (game variable key) | — |
| `entries[4].key` | 3 | No (game variable key) | — |
| `entries[5].key` | 1 | No (game variable key) | — |
| `entries[6].key` | 1 | No (game variable key) | — |
| `entries[7].key` | 1 | No (game variable key) | — |
| `entries[8].key` | 1 | No (game variable key) | — |
| `entries[9].key` | 1 | No (game variable key) | — |
| `entries[10].key` | 1 | No (game variable key) | — |
| `entries[11].key` | 1 | No (game variable key) | — |
| `entries[12].key` | 1 | No (game variable key) | — |
| `entries[13].key` | 1 | No (game variable key) | — |
| `entries[14].key` | 1 | No (game variable key) | — |
| `entries[15].key` | 1 | No (game variable key) | — |
| `entries[16].key` | 1 | No (game variable key) | — |
| `entries[17].key` | 1 | No (game variable key) | — |
| `entries[18].key` | 1 | No (game variable key) | — |
| `entries[19].key` | 1 | No (game variable key) | — |
| `entries[20].key` | 1 | No (game variable key) | — |
| `entries[21].key` | 1 | No (game variable key) | — |
| `entries[22].key` | 1 | No (game variable key) | — |

### `SetGameVariableIntDialogueNode`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `guid` | 56 | No (internal id / flag / key) | — |
| `entries[0].key` | 56 | No (game variable key) | — |
| `entries[1].key` | 3 | No (game variable key) | — |
| `entries[2].key` | 3 | No (game variable key) | — |
| `entries[3].key` | 3 | No (game variable key) | — |
| `entries[4].key` | 3 | No (game variable key) | — |
| `entries[5].key` | 3 | No (game variable key) | — |
| `entries[6].key` | 3 | No (game variable key) | — |
| `entries[7].key` | 3 | No (game variable key) | — |
| `entries[8].key` | 3 | No (game variable key) | — |
| `entries[9].key` | 3 | No (game variable key) | — |
| `entries[10].key` | 3 | No (game variable key) | — |
| `entries[11].key` | 3 | No (game variable key) | — |

### `ShopBuyNode`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `guid` | 4 | No (internal id / flag / key) | — |

### `ShopSellNode`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `guid` | 4 | No (internal id / flag / key) | — |

### `ShopSellNothingCheckNode`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `guid` | 4 | No (internal id / flag / key) | — |

### `SwitchDialogueNode`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `guid` | 1 | No (internal id / flag / key) | — |

### `SwitchExpressionByGameVariable`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `flagName` | 1 | No (internal id / flag / key) | — |

### `WarpDialogueNode`

| Field | Occurrences | Translatable? | Examples |
|-------|------------:|:-------------:|----------|
| `guid` | 1 | No (internal id / flag / key) | — |

## Top graph names

- `DLC1_Tips`: 10
- `dg_sicho`: 3
- `dg_kunoichi_hang`: 3
- `DLC1_Crowdfunding_01`: 3
- `dg_kunoichi`: 3
- `dg_kunoichi_utubuse`: 3
- `dg_omusubi`: 3
- `obj_VendingMachine_Blue_Kicked`: 3
- `obj_VendingMachine_Red`: 3
- `dg_dog`: 3
- `mogura_dialogue`: 3
- `dg_mogura_ane`: 3
- `cut008_5_dialogue`: 3
- `dg_majoko_chara`: 3
- `dg_release`: 3
- `dg_gakkiya_staff`: 3
- `dg_izakaya_staff`: 3
- `dg_cat`: 3
- `dg_kodaijinA`: 3
- `dg_cafe_staff`: 3
- `dg_kodaijinB`: 3
- `dg_toilet`: 3
- `dg_dog2_kemosuke`: 3
- `dg_dog2`: 3
- `dg_dog2_gonta`: 3

## GameScript overlap bundles

These bundles contain both `m_commandDatas` GameScripts and dialogue graphs.
When patching, load an already-patched bundle from the output dir if present (chain).

- `StandaloneWindows64/02a984badd780f113151ef9aae8e8686.bundle`
- `StandaloneWindows64/03844110bb386de951b94bef79fad877.bundle`
- `StandaloneWindows64/05d5e36222041c18cb75f416cb18966f.bundle`
- `StandaloneWindows64/0956870fce2a4b9dc0c7d3c7451e982e.bundle`
- `StandaloneWindows64/0c6de7e783949ae33b146a1554b34ac4.bundle`
- `StandaloneWindows64/0dcc6b8fe229c7b90726387ea3b4faca.bundle`
- `StandaloneWindows64/12633607fe421c357fbf7735401d6883.bundle`
- `StandaloneWindows64/195c7a30eab977d278cc6638417c5523.bundle`
- `StandaloneWindows64/1c6bf328cb0f3be896e9824b2e83a201.bundle`
- `StandaloneWindows64/1ce86caf27442b8aacf6c77625a9b4a7.bundle`
- `StandaloneWindows64/2369d7d122eb7d9b7bc796c031348482.bundle`
- `StandaloneWindows64/2ce082245f4bf6f40b193a264be33a47.bundle`
- `StandaloneWindows64/2efbf0848df62ff51a8b1a1c3c01606e.bundle`
- `StandaloneWindows64/36673ac07f421e2efa314d22610d1b01.bundle`
- `StandaloneWindows64/3d134973f1875e0c8a00cacf79f40318.bundle`
- `StandaloneWindows64/467f6774586398de539f7de92b4b65c1.bundle`
- `StandaloneWindows64/4b66e60e8d2ceefca930c77c8ade7428.bundle`
- `StandaloneWindows64/4dcc224562e95a7bcf58faf5a463369a.bundle`
- `StandaloneWindows64/4e3c4127acee8a8eedcbae25260802ee.bundle`
- `StandaloneWindows64/5c0cd8d25a42420c24865b6f4fb2c902.bundle`
- `StandaloneWindows64/60011e3d7e0732f818c985d10ff07a0b.bundle`
- `StandaloneWindows64/601d100c5998c7dd1b223cb2232a4452.bundle`
- `StandaloneWindows64/604f382e56797a349d4cd582613e55cf.bundle`
- `StandaloneWindows64/65635751a582287b21a2c3503313b8f4.bundle`
- `StandaloneWindows64/66cec86d6a1d11ce30774035ae4a6f24.bundle`
- `StandaloneWindows64/68cfb66b8993cc6c014cea0e243c78a6.bundle`
- `StandaloneWindows64/6904382035578ab1df2339908edff9b9.bundle`
- `StandaloneWindows64/6b76e912e0d788efc9d6cc5403046b8d.bundle`
- `StandaloneWindows64/6da8e2dc748b2623b90dfbafa71a1016.bundle`
- `StandaloneWindows64/6f91f484a9a02653d402f42a9378135a.bundle`
- … and 45 more

## Trailing-space note

Some choice strings differ only by trailing spaces (e.g. `'About the artifact '` vs `'About the artifact'`).
Extraction treats exact strings as distinct ids.

Machine-readable stats: `research/dialogue_graph_survey_stats.json`
