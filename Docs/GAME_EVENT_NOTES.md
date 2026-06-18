# GAME_EVENT_NOTES

## Scope

This note summarizes the current reverse-engineering conclusions for limited-time event related resources under:

- `E:\Games\Emulator\ACI\TSS`
- `E:\Games\Emulator\ACI\TSS\Unpack`

The current focus is on:

- `ACEText` resources: `.act`
- `ACETable` resources: `.lvst`

The goal is to understand how live event text, challenge tables, ranking text, and related runtime configuration are organized.

## Confirmed Ranking-Rule Hash Findings

The remaining unresolved `10.lvst` ranking menu hashes in the small complete branch are now identified by hash-name reversal, even though they do not currently resolve to plaintext event-title strings in the exported ACT text sets.

Confirmed mappings:

- `0x184A15D3` = `DebugRegulationName_cw1`
- `0x1509330A` = `DebugRegulationName_cw2`
- `0x55BE208C` = `DebugRegulationName_tc1`

These names were recovered from:

- `E:\Games\Emulator\ACI-Reverse-Engineering\ACI-FileSystem-Research\Tools\Ulysses\Ulysses\Names\ACT.name`

using the same hash routine used by `Ulysses.Struct.IdRegistry.Hash(...)`:

- UTF-8 bytes
- `CRC32/BZip2`

Sanity check:

- `MenuItem_Main_034` hashes to `0x15DBCF32`
- `MenuItem_Main_035` hashes to `0x111AD285`
- `MenuItem_Main_037` hashes to `0x1898E9EB`

So the three unresolved values are not alternate hashes for `MenuItem_Main_034/035/037`. They are a different naming family, and currently look like debug / regulation identifiers rather than normal end-user menu labels.

Current best semantic reading from nearby `10.lvst` rows:

- `DebugRegulationName_cw1`
  - paired with `MissionId_RankEvent1500`
- `DebugRegulationName_cw2`
  - paired with `DebugMsnId_micw2`
- `DebugRegulationName_tc1`
  - paired with `DebugMsnId_mitc2`, and later also reused with `MissionId_RankEvent2500`

This strengthens the current interpretation that `10.lvst` acts as a ranking-rule / regulation table, and that some rows use internal rule-name ids instead of ordinary localized menu-title ids.

## TSS Container Layer

### Raw `.tss` is a DPL-family container

The raw files under:

- `E:\Games\Emulator\ACI\TSS`

are not arbitrary archives. Their payload layer is a `DPL` container, and their merge model matches the same high-level behavior used by PAC-style resource layering:

- each package contains a table of top-level FHM resources
- higher-priority packages can replace lower-priority resources by hash
- unpacked folder roots under `Unpack\NPWR04428_00-*` correspond to top-level FHM hashes

This is also consistent with `Ulysses` resource logic:

- a DPL package exposes an `FHMTable`
- effective resources are selected by hash from the highest-priority mounted package

### One special wrapper: `NPWR04428_00-0.tss`

`NPWR04428_00-0.tss` is not a plain DPL file starting at offset `0`.

Its first bytes are:

- `GST444444\r\n`

and the embedded `DPL` header begins at offset:

- `0x0B`

So `-0.tss` is currently best treated as a wrapped DPL variant, not a plain top-level DPL blob.

After stripping the `0x0B`-byte `GST444444\r\n` wrapper, the inner payload parses as a valid `3`-entry DPL:

- `0x2b788994` = unknown small resource
- `0x921b52bb` = unknown small resource
- `0xd100550b` = `DPL_TSS_PRODUCT_BOOT`

Important current observations:

- these hashes do not appear in the normal `-1` complete branch top-level set
- `DPL_TSS_PRODUCT_BOOT` strongly suggests a startup / boot / product-front resource role
- the two companion resources are tiny metadata-like items

So `-0.tss` currently looks like a standalone boot/front wrapper layer, not part of the regular event-content branch family.

### Raw package inventory

Current raw package sizes:

- `NPWR04428_00-0.tss` = `6155`
- `NPWR04428_00-1.tss` = `3174400`
- `NPWR04428_00-2.tss` = `36864`
- `NPWR04428_00-3.tss` = `3051520`
- `NPWR04428_00-4.tss` = `120832`
- `NPWR04428_00-5.tss` = `3153920`
- `NPWR04428_00-6.tss` = `36864`
- `NPWR04428_00-7.tss` = `3051520`
- `NPWR04428_00-8.tss` = `120832`
- `NPWR04428_00-9.tss` = `3174400`
- `NPWR04428_00-10.tss` = `36864`
- `NPWR04428_00-11.tss` = `3051520`
- `NPWR04428_00-12.tss` = `120832`
- `NPWR04428_00-13.tss` = `368640`
- `NPWR04428_00-14.tss` = `765952`

### Top-level FHM counts

All plain DPL-like `.tss` files parsed successfully as top-level resource tables.

Observed top-level FHM counts:

- `-1`, `-5`, `-9` = `48`
- `-3`, `-7`, `-11` = `47`
- `-2`, `-4`, `-6`, `-8`, `-10`, `-12` = `2`
- `-13` = `10`
- `-14` = `4`

This exactly matches the root resource directory counts previously observed in `Unpack` for the six odd-numbered branches:

- `NPWR04428_00-1`, `-5`, `-9` each unpack to `48` root resource hashes
- `NPWR04428_00-3`, `-7`, `-11` each unpack to `47` root resource hashes

So the odd-numbered unpacked trees are already complete top-level DPL views, not merely partial products waiting to be merged with the adjacent even-numbered packages.

## TSS Package Families

### Large complete branch: `-1 / -5 / -9`

These three raw packages are hash-identical at the top-level FHM resource set:

- `NPWR04428_00-1.tss`
- `NPWR04428_00-5.tss`
- `NPWR04428_00-9.tss`

They each contain the same `48` top-level resource hashes.

This aligns with the previously observed text behavior:

- `0x58cf00c0/0/0.act` in these branches has `1512` entries
- `0x3f20632f/5.lvst` uses the `21xx/22xx` challenge family

### Small complete branch: `-3 / -7 / -11`

These three raw packages are also hash-identical at top level:

- `NPWR04428_00-3.tss`
- `NPWR04428_00-7.tss`
- `NPWR04428_00-11.tss`

They each contain the same `47` top-level resource hashes.

This also aligns with the previously observed text behavior:

- `0x58cf00c0/0/0.act` in these branches has `799` entries
- `0x3f20632f/5.lvst` uses the separate `15xx..20xx` challenge family

### Relationship between the two complete branches

The `48`-resource branch and the `47`-resource branch are not simple revisions of one another.

Top-level comparison shows:

- common resources: `11`
- `-1`-family only: `37`
- `-3`-family only: `36`

The `11` shared hashes are:

- `0x05d2c897` = `DPL_TSS_LUAPATCH`
- `0x102ecb8e` = `DPL_TSS_SALES_LIST`
- `0x32903a97` = unknown
- `0x3f20632f` = `DPL_TSS_INFO`
- `0x54b7f2d4` = `DPL_TSS_ITEM`
- `0x58cf00c0` = `DPL_UI_TSS_COMMON`
- `0x6463c61c` = `DPL_DEVELOPMENT`
- `0x761b5e0d` = `DPL_TSS_DROP_ITEM`
- `0x96da4f0c` = unknown tiny metadata item
- `0xe82647a1` = `DPL_INFORMATION`
- `0xf4be88bd` = `DPL_TSS_MISC`

This shared set looks like the stable live-service core:

- common text
- challenge / info tables
- item / drop definitions
- sales / information / misc support data
- lua patch support

The large number of non-shared hashes strongly suggests the two complete branches represent two distinct event-content families rather than a single linear patch chain.

## Small Overlay Packages

### Repeating 2-resource overlay family: `-2 / -4 / -6 / -8 / -10 / -12`

All six of these packages expose the same two top-level hashes:

- `0x6976b3b3` = `DPL_UI_TSS_MENU`
- `0x9b9969d5` = unknown tiny metadata item

So this family is best modeled as a repeated menu/UI overlay layer, not as a complete event bundle.

At minimum, it can replace:

- TSS menu UI resources
- one tiny companion metadata/control resource

### 10-resource overlay: `-13`

`NPWR04428_00-13.tss` contains these `10` top-level resources:

- `0x102ecb8e` = `DPL_TSS_SALES_LIST`
- `0x32903a97` = unknown
- `0x3f20632f` = `DPL_TSS_INFO`
- `0x54b7f2d4` = `DPL_TSS_ITEM`
- `0x58cf00c0` = `DPL_UI_TSS_COMMON`
- `0x6463c61c` = `DPL_DEVELOPMENT`
- `0x761b5e0d` = `DPL_TSS_DROP_ITEM`
- `0x96da4f0c` = unknown tiny metadata item
- `0xe82647a1` = `DPL_INFORMATION`
- `0xf4be88bd` = `DPL_TSS_MISC`

This is exactly a subset of the shared 11-resource live-service core, except that:

- `DPL_TSS_LUAPATCH (0x05d2c897)` is absent

So `-13` currently looks like a focused event-data overlay that updates the central text/info/item/development/information resources without carrying the full branch-specific outer shell.

It is important that `-13` is not a byte-for-byte extraction of the shared core from `-1` or `-3`.

For several key shared resources, the `-13` versions are much smaller:

- `0x3f20632f DPL_TSS_INFO`
  - `-1`: `0x83fd / 0x2e868`
  - `-3`: `0x4c46 / 0x17bac`
  - `-13`: `0x0fc0 / 0x03efc`
- `0x58cf00c0 DPL_UI_TSS_COMMON`
  - `-1`: `0x12c018 / 0x2bdd01`
  - `-3`: `0x0e0d6b / 0x204346`
  - `-13`: `0x03fabc / 0x0e80d8`
- `0xe82647a1 DPL_INFORMATION`
  - `-1`: `0x0a2fdf / 0x22545c`
  - `-3`: `0x09c3ff / 0x20f3a8`
  - `-13`: `0x013964 / 0x05ccec`

This strongly suggests `-13` is a reduced hot-update core layer rather than a full shared-core clone.

### 4-resource overlay: `-14`

`NPWR04428_00-14.tss` contains:

- `0x62bbe64d` = unknown 2D image package
- `0x6976b3b3` = `DPL_UI_TSS_MENU`
- `0x6ff8c094` = unknown 2D image package
- `0x9b9969d5` = unknown tiny metadata item

So `-14` looks like a UI-focused overlay, probably:

- TSS menu UI
- two large image resources
- one tiny metadata/control resource

This makes it a good candidate for banner/menu/notice presentation updates rather than challenge-table or main text-content updates.

## Current Best Layering Model

This section is still a working model, but the current top-level hash relationships are already strong enough to outline a likely runtime layering pattern.

### Core observations that drive the model

1. `-1/-5/-9` and `-3/-7/-11` are each internally stable complete branches.
2. `-13` is a strict subset of both complete branches at the top-level hash layer.
3. `-13` replaces shared-core resources with smaller hot-update variants rather than cloning one full branch.
4. `-2/-4/-6/-8/-10/-12` contain only:
   - `DPL_UI_TSS_MENU (0x6976b3b3)`
   - `0x9b9969d5`
5. `-14` contains:
   - the same `2` resources as the small menu family
   - plus two additional large image resources
6. Neither the `-2` family nor `-14` shares those UI hashes with the `-1` or `-3` complete branches.

### Practical implication

This means the current best model is not:

- one complete branch that already contains all UI/menu resources

but rather:

- one complete event-content branch
- plus additional UI/menu/image DPL layers mounted alongside it

### Best current candidate chain

At a high level, the runtime content set likely behaves like:

1. select one complete base branch
   - either `-1/-5/-9` family
   - or `-3/-7/-11` family
2. apply shared hot-update core layer
   - `-13`
3. apply TSS menu/UI layer
   - either one of the minimal `-2/-4/-6/-8/-10/-12` packages
   - or the richer `-14` package
4. optionally keep `-0` as a separate boot/front layer
   - because its resources do not belong to either complete branch

### Strong pair pattern in numbering

The numbering pattern strongly suggests that the even-numbered small menu packages are paired companions of the preceding odd-numbered complete branches:

- `1 + 2`
- `3 + 4`
- `5 + 6`
- `7 + 8`
- `9 + 10`
- `11 + 12`

Evidence:

- every odd package in this set is a complete branch package
- every even package in this set contains the exact same `2` hashes:
  - `0x6976b3b3 = DPL_UI_TSS_MENU`
  - `0x9b9969d5 = unknown tiny metadata item`
- this pattern is perfectly stable across all six odd/even pairs

So the current best interpretation is:

- odd-numbered package = main event-content branch
- following even-numbered package = fixed companion menu/UI layer for that branch slot

This does not yet prove the runtime loader literally mounts them as numbered pairs, but it is now the strongest structural hypothesis.

### Why `-14` looks higher than the `-2` family

At the top-level hash set:

- `-2` family = `{0x6976b3b3, 0x9b9969d5}`
- `-14` = `{0x62bbe64d, 0x6976b3b3, 0x6ff8c094, 0x9b9969d5}`

So:

- every `-2`-family hash is contained in `-14`
- `-14` adds two extra large image resources

This makes `-14` look like a superset UI presentation package, while the `-2` family looks like a minimal menu-only refresh.

### What is still not proven

The current analysis still does not prove the exact mount order used by the retail client.

What is proven is only the resource-relationship side:

- which packages are complete branches
- which packages can only act as overlays
- which overlay families supersede smaller overlay families by hash coverage

The next useful step is therefore to correlate these package families with startup / script selection logic, rather than continue only comparing table payloads.

## Parsing Basis

The current conclusions are based on the existing local parsers:

- `Tools/ACI-Text-Tools/aci_text_tools/ace_text_parser.py`
- `Tools/ACI-Text-Tools/aci_text_tools/ace_table_parser.py`

These conclusions should be treated as structural and relational notes. Some decoded text payloads still appear garbled, but label names and cross-file references are already useful enough for semantic analysis.

## High-Level Findings

### `.act` files in `TSS\Unpack`

There are only `6` `.act` files in the whole TSS dump.

All six are located at:

- `...\NPWR04428_00-1\0x58cf00c0\0\0.act`
- `...\NPWR04428_00-3\0x58cf00c0\0\0.act`
- `...\NPWR04428_00-5\0x58cf00c0\0\0.act`
- `...\NPWR04428_00-7\0x58cf00c0\0\0.act`
- `...\NPWR04428_00-9\0x58cf00c0\0\0.act`
- `...\NPWR04428_00-11\0x58cf00c0\0\0.act`

They parse as `ACEText` and expose the languages:

- `JP`
- `US`
- `FR`
- `IT`
- `GE`
- `SP`
- `RU`

Two major text-set variants were observed:

- large set: `1512` entries in `-1`, `-5`, `-9`
- small set: `799` entries in `-3`, `-7`, `-11`

These variants differ substantially, so they are not just trivial revisions of the same text bundle.

### `.act` labels strongly indicate event/live content

Representative labels found in `0x58cf00c0/0/0.act` include:

- `ShortName_RankEvent1061`
- `LongName_RankEvent1099`
- `InfoMsg_RankEvent01`
- `InfoMsg_RankEvent02`
- `Reward_RankEvent1049`
- `MenuDesc_RankEventCmn_Before`
- `LoadingMsg_Event_94`
- `LoadingMsg_Event_95`
- `LoadingMsg_Event_96`
- `DlgMsg_LoginBonus_043`
- `Challenge_Title_Sp_*`
- `Challenge_Msg_Sp_*`

This is strong evidence that `0x58cf00c0/0/0.act` is a central live-event text bundle.

## Important `.lvst` Groups

### Strong event group

- `0x3f20632f`

This group appears to contain the main event/challenge/ranking tables.

### Event loading / activity related

- `0x58cf00c0/1.lvst`

This file is closely related to event loading screens or event notice presentation.

### Likely small lookup / config group

- `0x6463c61c`

This group has not yet been fully classified, but it currently looks more like generic live configuration than primary event content.

### Non-event tuning / equipment group

- `0xe82647a1`

This group contains readable names such as:

- `AccelUpS`
- `AccelUpM`
- `AccelUpL`
- `AccelUpLL`
- `AccelUpRS`
- `BasicSet`
- `DmgUp`
- `LockRangeUp`
- `HomingUp`
- `HighGRotUp`

This group should currently be treated as equipment / part / performance tuning data, not as primary event text data.

## Confirmed `.lvst` -> `.act` Linkage

### `0x3f20632f/5.lvst`

Directly references challenge text inside `0x58cf00c0/0/0.act`:

- column `0x26B6DAC0` -> `Challenge_Title_Sp_*`
- column `0xF67C9878` -> `Challenge_Msg_Sp_*`

### `0x58cf00c0/1.lvst`

Directly references event loading text:

- `0xC87D8BD1` -> `LoadingTitle_Event_93`
- `0xC53EAD08` -> `LoadingMsg_Event_93`

### `0x3f20632f/7.lvst`

Directly references ranking-related UI text:

- `MenuDesc_RankEventCmn_Before`
- `MenuDesc_TDM_RankEventCmn_Before`
- `MenuDesc_RankEventCmn_Current`
- `MenuDesc_RankEventCmn_Reward`
- `DlgMsg_RankEventCmn_Before`

### `0x3f20632f/0.lvst`

Directly references event/ranking mail text:

- `Mail_Title_*`
- `Mail_Text_*`
- `Mail_Text_Ranking_*`

## Detailed Notes: `0x3f20632f/5.lvst`

File:

- `E:\Games\Emulator\ACI\TSS\Unpack\NPWR04428_00-1\0x3f20632f\5.lvst`

Observed structure:

- `207` rows
- `38` columns

Current best interpretation: this is a challenge activity node table or task tree table.

### Best current guesses for important columns

- `0x56CB07C4`
  - unique per row
  - observed range roughly `100..2111`
  - likely `node_id` or `task_id`

- `0xE4FF913B`
  - values like `-1`, `100`, `101`, `102`
  - likely `parent_id` or prerequisite node id
  - first-row `-1` strongly suggests root/no-parent

- `0x72B5C53E` + `0xC3649538`
  - likely start `Date` + start `Time`

- `0xEC64C9A0` + `0x5DB599A6`
  - likely end `Date` + end `Time`

- `0x26B6DAC0`
  - challenge title hash
  - confirmed link to `Challenge_Title_Sp_*`

- `0xF67C9878`
  - challenge description hash
  - confirmed link to `Challenge_Msg_Sp_*`

- `0xE5B9FE19`
  - constant `0xF09AF8CC`
  - likely fixed family/type/resource tag

- `0xF7740E1D`
  - many values around `1000..1125`
  - likely challenge template/type/script id

- `0xDE439831`
  - only a few values observed: `1054`, `1105`, `1106`, `1107`, `1108`, `1109`
  - likely season/group/batch/activity-group id

- `0xD4FF61C1`
  - values such as `1`, `1000`, `2000`, `3000`, `5000`, `10000`, `10000000`
  - likely reward/threshold/target field

- `0xD9BC4718`
  - values such as `1`, `40`, `100`, `3000`, `10000`, `1000000`
  - likely another reward/threshold field

### Low-cardinality fields worth further study

- `0xABC16DF2` in `{0,1,2}`
- `0x298D0A45` in `{1,2,3}`
- `0x75CA4FC9` in `{1,2,3}`
- `0x04E9E5B9` in `{0,1}`

These likely encode compact enums or boolean-like flags.

### Row pattern evidence

Observed parent chain examples:

- `100 -> parent -1`
- `101 -> parent 100`
- `102 -> parent 101`
- `103 -> parent 102`
- `104 -> parent 103`
- `105 -> parent 104`
- `106 -> parent 103`
- `117 -> parent 116`
- `118 -> parent 116`
- `119 -> parent 116`

This strongly supports the interpretation that `5.lvst` stores a progression tree / dependency tree for challenge nodes.

## Other `.lvst` Summaries

### `0x3f20632f/0.lvst`

Likely event mail / ranking reward mail configuration table.

Observed behavior:

- contains date/time windows
- links to `Mail_Title_*`
- links to `Mail_Text_*`
- links to `Mail_Text_Ranking_*`

### `0x3f20632f/7.lvst`

Likely a ranking UI text mapping table.

Its current role appears to be mapping ranking states or ranking UI contexts to text labels in the event `ACEText`.

### `0x58cf00c0/1.lvst`

Likely event loading-screen / event notice configuration.

Readable string-like values such as:

- `f22a`
- `f15c`
- `f14d`
- `f16c`

These may be layout/template/image identifiers.

### `0xe82647a1/4.lvst` and `0xe82647a1/5.lvst`

These look unrelated to live event text flow.

Current best interpretation:

- aircraft part / equipment tuning tables
- performance modifier lookup tables

## Current Working Model

The most likely event resource flow currently looks like this:

1. `0x58cf00c0/0/0.act`
   - central text bundle for event names, challenge titles, challenge descriptions, loading messages, ranking descriptions, login bonus text, and event mail text

2. `0x3f20632f/*.lvst`
   - event logic/config tables
   - challenge tree
   - mail/ranking metadata
   - ranking UI text mappings

3. `0x58cf00c0/1.lvst`
   - event loading or presentation-side configuration linked to event text

This is currently a stronger and more productive line than trying to infer event meaning from unrelated tuning tables.

## Open Questions

### `5.lvst` and `6.lvst` relationship

This is the best next research target.

Current hypothesis:

- `5.lvst` = challenge node master table
- `6.lvst` = reward, condition, or detail table referenced by `5.lvst`

The next step is to compare shared identifiers and packed fields between:

- `0x56CB07C4`
- `0xF7740E1D`
- `0xDE439831`
- `0x37E12563`
- `0x3AA203BA`

and the major columns inside `6.lvst`.

### Packed/composite fields in `5.lvst`

The following values look like bit-packed or composite ids:

- `0x37E12563`
- `0x3AA203BA`

Example values include:

- `65597`
- `65547`
- `4194600`
- `33554737`
- `134217997`

These should be examined in hexadecimal and by bit layout to see whether they encode category/subtype/state data.

### Cross-version comparison

It may be useful to compare the `0x3f20632f` tables across different `NPWR04428_00-*` folders to determine whether table changes align with the `1512` vs `799` text-set variants.

## Update: Late-Era `5.lvst` Model

### Late `5.lvst` is stable across `-1 / -5 / -9`

The late-era files:

- `NPWR04428_00-1\0x3f20632f\5.lvst`
- `NPWR04428_00-5\0x3f20632f\5.lvst`
- `NPWR04428_00-9\0x3f20632f\5.lvst`

currently appear to be structurally and semantically identical for practical reverse-engineering purposes.

This means they can be treated as one late challenge master table.

### Late roots directly reference late `Challenge_Title_Sp_*`

Late root nodes in `5.lvst` directly resolve into late text labels in `0x58cf00c0/0/0.act`, especially:

- `Challenge_Title_Sp_2152` through `Challenge_Title_Sp_2259`
- matching `Challenge_Msg_Sp_*`

This strongly supports the idea that the final live-service era used `5.lvst` itself as the primary surviving challenge-definition surface.

### Late `5.lvst` is not just an index

Several late roots already contain complete progression-chain structure inside `5.lvst`:

- `2056 -> 2058`
- `2059 -> 2061`
- `2074 -> 2094`
- `2095 -> 2097`
- `2098 -> 2100`
- `2101 -> 2111`

These chains already encode:

- date window
- node ordering
- text linkage
- target/reward progression
- compact template parameters

This means late `5.lvst` is not merely pointing at an external challenge list. It already stores a large amount of challenge-chain composition logic.

## Update: Late `type` Signatures

Late-era `type` rows show very stable compact signatures.

The fields:

- `a`
- `c`
- `e`
- `f`
- `g`
- `h`

are usually constant within a single late `type`, while the main changing fields are:

- `b`
- `d`
- `target`
- `reward`
- `small`
- `small2`

Current best interpretation:

- `type + (a,c,e,f,g,h)` behaves like a challenge template signature
- `b` and/or `d` carry concrete condition-instance identifiers or template-local parameters
- `target` is usually the completion threshold
- `reward` is usually the payout or final-stage completion payload

### Important late `type` patterns

#### `type=1062`

Signature:

- `a=17`
- `c=9`
- `e=2`
- `f=2`
- `g=3`
- `h=1`

Late behavior:

- `target=1`
- `reward=10000` or `20000`
- `b` usually `-1`
- `d` varies across a dense small-value set

Current best guess:

- fixed challenge family
- concrete condition choice mainly carried by `d`

#### `type=1056`

Signature:

- `a=17`
- `c=9`
- `e=2`
- `f=2`
- `g=3`
- `h=1`

Late behavior:

- same broad family as `1062`
- but more mixed `b/d/target/reward` usage
- includes staircase chains like `2056 -> 2058`

Current best guess:

- adjacent family to `1062`
- often used for cumulative or staged completion chains

#### `type=1086`

Signature:

- `a=17`
- `c=10`
- `e=2`
- `g=3`
- `h=1`

Late behavior:

- `d` in values like `200`, `210`, `440`, `470`, `500`, `503`, `509`, `516`
- includes staged chain `2000 -> 2003`

Current best guess:

- fixed family under `c=10`
- `d` behaves like concrete condition code

#### `type=1114`

Signature:

- `a=10`
- `c=3`
- `e=2`
- `f=2`
- `g=2`
- `h=1`

Late behavior:

- `b=103..108`
- forms two 3-step chains:
  - `2095 -> 2097`
  - `2098 -> 2100`

Current best guess:

- `b` is the main concrete condition identifier

#### `type=1120`

Signature:

- `a=3`
- `c=10`
- `e=2`
- `f=2`
- `g=3`
- `h=1`

Late behavior:

- `b=10000` constant
- `d=600/601/602/603/604/605/630/631/632/660/661`
- forms long chain `2101 -> 2111`

Current best guess:

- `b` is template-family constant
- `d` is the real concrete instance selector

#### `type=1053`

Signature:

- `a=10`
- `c=15`
- `d=5`
- `e=2`
- `f=2`
- `g=3`
- `h=1`

Late behavior:

- long chain `2074 -> 2094`
- `small=65597`
- `small2=0`
- only `b` changes along the chain

Current best guess:

- `b` is the concrete condition-instance selector
- `d=5` is a template constant

#### `type=1122`

Signature:

- `a=3`
- `c=10`
- `e=2`
- `g=3`
- `h=1`

Late behavior:

- `b=1500` constant
- `d` changes across the chain
- same label sequence reused twice:
  - `2004 -> 2015`
  - `2062 -> 2073`

Current best guess:

- `b=1500` is family or template constant
- `d` is the real concrete condition-instance selector

## Update: Refined `5.lvst` <-> `6.lvst` Model

### Late `5.lvst` does not map cleanly onto `6.lvst stage 2` families

Earlier analysis showed that `6.lvst stage 2` packed ids behave like:

- family bucket
- plus family-local variant payload

Examples:

- `1202`
- `1203`
- `1502`
- `1503`
- `6105`

Late `5.lvst` does not appear to reference this layer directly as its primary control surface.

Instead, late `5.lvst` matches much more strongly against lower-layer concrete instance ids from:

- `stage 3`
- `stage 4`
- `stage 5`

### Best current model

The best current model is:

1. `5.lvst`
   - selects a late challenge template by `type + compact signature`
   - chooses concrete condition instances using `b` and/or `d`
   - applies date window, title, message, target, reward, and chain ordering

2. `6.lvst`
   - serves as an older reusable condition-instance library
   - especially its lower layers:
     - `stage 3`
     - `stage 4`
     - `stage 5`

Late live-service content therefore looks more like:

- challenge-chain composition in `5.lvst`
- reusing old condition-instance inventory from `6.lvst`

rather than:

- defining an entirely new late challenge master in `6.lvst`

## Update: `x2` Prefix Clusters in `6.lvst`

One useful way to classify `6.lvst` instances is by decimal prefix patterns in the `x2` field.

These prefixes are not yet fully decoded semantically, but they already cluster very strongly by stage and metrics.

### Prefix `3045`

Observed behavior:

- almost entirely `646 stage 3`
- `metric1=100`
- broad set of `a/b_low` values
- strong concentration in groups:
  - `710014`
  - `710015`
  - `710017`
  - `710018`
  - `710019`
  - `710020`
  - `710021`
  - `710022`
  - `710023`

This currently looks like a large `stage 3` condition-instance family.

### Prefix `3040`

Observed behavior:

- `646 stage 3`
- `metric1=100`
- more limited and earlier-looking subgroup than `3045`

This currently looks like another `stage 3` family adjacent to `3045`, but smaller and more localized.

### Prefix `5042`

Observed behavior:

- `646 stage 5`
- `metric1=100`
- many contiguous `b_low` sequences

This looks like a `stage 5` family closely related to lower-layer `stage 3` condition instances.

### Prefix `13032`

Observed behavior:

- `462 stage 3`
- `metric1=200`
- tightly grouped around a few ids such as:
  - `604`
  - `599`
  - `596`
  - `210`

This looks like a specific `462 stage 3` family with a stable threshold class.

### Prefix `13041`

Observed behavior:

- `462 stage 3`
- `metric1=100`

This is another `462 stage 3` family, apparently parallel to `13032` but with a different `metric1` class.

### Prefix `13080`

Observed behavior:

- `462 stage 3`
- `metric1=20`

This appears to be another `462 stage 3` family with smaller threshold semantics.

### Prefix `13151`

Observed behavior:

- `462 stage 3`
- only observed on id `470`
- `metric1=1`

This currently looks like a very narrow special-case family.

### Prefix `14045`

Observed behavior:

- `462 stage 4`
- `metric1=100`
- repeated around ids such as:
  - `250`
  - `280`
  - `290`
  - `322`
  - `347`
  - `505`
  - `507`
  - `522`

This looks like a `stage 4` instance family with mid-range threshold class.

### Prefix `14145`

Observed behavior:

- `462 stage 4`
- `metric1=2`
- repeated around ids such as:
  - `320`
  - `350`
  - many other stage-4 instance ids

This looks like another `stage 4` family, distinct from `14045`.

### Prefix `14016`

Observed behavior:

- `462 stage 4`
- `metric1=1000`
- many groups across the late library

This currently looks like a high-threshold `stage 4` family.

## Update: Stronger `x2`-Family Rules

### Many instance rows duplicate the id in both `a` and packed-low `b`

For many of the useful `stage 3` / `stage 4` / `stage 5` rows involved in late challenge reuse, the following is true:

- `a == low(id_b)`

This is especially common in the cleaner `stage 3` families and many `stage 4` families.

This suggests that, for these rows, the table is effectively storing the same concrete instance id twice:

- once as a direct integer field
- once as the low part of the packed field

This makes it much more likely that these rows are concrete condition-instance definitions rather than abstract family declarations.

### `x2` prefix currently behaves like an instance-family identifier

Across the useful late-era clusters, the strongest practical grouping key is now:

- `stage`
- `metric1`
- decimal prefix of `x2`

In other words, `x2` prefix currently behaves much more like an instance-family identifier than like a random payload.

### Current best family grid

#### `646 stage 3`

- prefix `3045`
  - `metric1=100`
  - large dense family
  - strongly reused by late challenge chains

- prefix `3040`
  - `metric1=100`
  - smaller adjacent family

#### `646 stage 5`

- prefix `5042`
  - `metric1=100`
  - looks like a derived or wrapper family around concrete condition instances

#### `462 stage 3`

- prefix `13032`
  - `metric1=200`

- prefix `13041`
  - `metric1=100`

- prefix `13080`
  - `metric1=20`

- prefix `13151`
  - `metric1=1`
  - very narrow special case

#### `462 stage 4`

- prefix `14045`
  - `metric1=100`

- prefix `14145`
  - `metric1=2`

- prefix `14016`
  - `metric1=1000`

This is currently the cleanest practical classification scheme for reverse-engineering the late challenge-condition inventory.

## Update: Additional Pattern Notes

### `3045` family

Observed structure:

- almost all rows are `646 stage 3`
- `metric1=100`
- row ids cover broad numeric ranges
- `x2` values are densely patterned

This currently looks like a large, reusable mid-threshold family of concrete condition instances.

### `5042` family

Observed structure:

- almost all rows are `646 stage 5`
- `metric1=100`
- many rows form contiguous `b_low` ranges
- rows often look like sequential wrappers over neighboring ids

This currently looks less like a semantic family by itself and more like a structured higher-layer wrapper family over concrete instance ids.

### `13032 / 13041 / 13080 / 13151`

Observed structure:

- all are `462 stage 3`
- they separate cleanly by `metric1`
  - `200`
  - `100`
  - `20`
  - `1`

This strongly suggests that `metric1` is not random metadata. It likely represents a meaningful threshold class or count scale inside the family.

### `14045 / 14145 / 14016`

Observed structure:

- all are `462 stage 4`
- they separate cleanly by `metric1`
  - `100`
  - `2`
  - `1000`

This again suggests that:

- `x2` prefix identifies the family
- `metric1` identifies the threshold scale or quantitative tier inside that family

## Current Best Synthesis

The late system now looks like this:

- `5.lvst` stores late challenge chains directly
- `type + compact signature` chooses a template family
- `b` and/or `d` select concrete old condition instances
- those instances resolve most naturally into clustered `6.lvst` families identified by:
  - stage
  - metric1
  - `x2` decimal prefix

This is now a stronger working model than the older idea that late `5.lvst` merely references one clean, synchronized late `6.lvst` master.

## Update: `5.lvst` Challenge Text Comes From Two Different `ACT` Sources

Direct hash resolution now shows that `0x3f20632f/5.lvst` does **not** source all challenge text from the TSS live bundle alone.

### Source A: TSS live-event text bundle

- `E:\Games\Emulator\ACI\TSS\Unpack\NPWR04428_00-1\0x58cf00c0\0\0.act`

This file resolves the late-era `Challenge_Title_Sp_*` / `Challenge_Msg_Sp_*` labels used heavily by the surviving 2017-2018 challenge chains.

Examples:

- `0x2FC3EFE6` -> `Challenge_Msg_Sp_2152`
- `0x00493930` -> `Challenge_Msg_Sp_2158`
- `0x1A656415` -> `Challenge_Msg_Sp_2222`
- `0x0AD82EAE` -> `Challenge_Title_Sp_2249`
- `0x06E1D10E` -> `Challenge_Msg_Sp_2259`

### Source B: full-game base challenge text bundle

- `E:\Games\Emulator\ACI-Reverse-Engineering\ACI-FileSystem-Research\Tools\ACI-File-Tools\output\FullGame\0x375ba2dc\0\160.act`

All `156` challenge-text hashes that were missing from every TSS `0x58cf00c0/0/0.act` variant resolve cleanly in this base-game file.

Examples:

- `0x065D4FB1` -> `Challenge_Title_1000`
- `0x029C5206` -> `Challenge_Title_1001`
- `0x0FDF74DF` -> `Challenge_Title_1002`
- `0x0B1E6968` -> `Challenge_Title_1003`
- `0x0D397587` -> `Challenge_Msg_1003_001`
- `0x1F208312` -> `Challenge_Msg_1028`
- `0x07652BBE` -> `Challenge_Msg_1052`
- `0x03A43609` -> `Challenge_Msg_1053`

### Stronger interpretation

The challenge-text layer is therefore split:

- older / base challenge templates are stored in the main game text resource
- late live-service additions are stored in the TSS live-event text resource

This explains why:

- many 2014-window or older-template rows in `5.lvst` did not resolve inside the TSS dump
- late `2017-12` to `2018-03` challenge chains often resolve into `Challenge_*_Sp_*`
- the TSS dump should be treated as an overlay on top of a larger base-game challenge text inventory, not as a complete standalone challenge-text set

### Practical consequence

For challenge-text reverse engineering, `5.lvst` should currently be interpreted against **both** of these text sources:

1. `TSS\Unpack\...\0x58cf00c0\0\0.act`
2. `FullGame\0x375ba2dc\0\160.act`

This dual-source model is now much stronger than the earlier single-source assumption.

## Update: TSS `0x58cf00c0/0/0.act` Uses a Distinct Tokenized Text Encoding

Further raw comparison shows that the TSS event text files are not simply ordinary UTF-16BE text bundles.

### Strong structural behavior

For `NPWR04428_00-1` and `NPWR04428_00-9`:

- every parsed language string begins with the code-unit prefix:
  - `0xE020 0x0001`
- this is true for all `1512` entries in each file

By contrast, the base-game challenge text file:

- `FullGame\0x375ba2dc\0\160.act`

uses ordinary UTF-16BE text directly and does **not** use the `0xE020 0x0001` prefix at all.

### Important implication

When the same `Challenge_*_Sp_*` label and the same `hash_value` exist in both:

- `FullGame\0x375ba2dc\0\160.act`
- `TSS\Unpack\...\0x58cf00c0\0\0.act`

the underlying text payload bytes are still different from the very first code units onward.

So this is **not** just a parser bug reading the same UTF-16BE bytes in two different ways.

Instead, the TSS file is using a distinct encoded/tokenized text representation.

### What the tokenized form currently looks like

Observed properties:

- universal leading prefix:
  - `0xE020 0x0001`
- the remaining payload behaves like a reusable token stream
- repeated challenge-message families share identical tokenized prefixes very aggressively
- there is no evidence yet for a simple fixed XOR, fixed offset, or one-to-one character substitution

Current best interpretation:

- the TSS event text is stored in a higher-level tokenized or dictionary-coded form
- the existing parser can still preserve the raw code units, but cannot yet decode this token stream into plain text

### Why this matters

This explains why many TSS entries currently appear as:

- `\uE020\x01...`

instead of readable localized text, even though the base-game equivalents are readable.

It also means:

- base-game `ACT` files can still serve as readable semantic references for overlapping challenge text
- but TSS `ACT` decoding will require a separate token-decoder model, not just better UTF-16BE handling

## Update: `NPWR04428_00-5` Is a Mixed / Unreliable Intermediate Variant

The `NPWR04428_00-5\0x58cf00c0\0\0.act` variant is materially different from `-1` and `-9` and should not currently be treated as a clean canonical event-text sample.

### Encoding split inside `-5`

Observed challenge-text distribution:

- `Challenge_Msg_Sp_*`
  - still tokenized with `0xE020 0x0001`
  - `299` entries

- `Challenge_Title_Sp_*`
  - mostly plain UTF-16BE
  - `232` plain entries
  - only `34` tokenized entries

### More importantly: label reuse with different meanings

In `-5`, many `Challenge_Title_Sp_*` labels do **not** carry challenge titles at all.

Examples:

- `Challenge_Title_Sp_2190` -> `Disband Clan`
- `Challenge_Title_Sp_2194` -> `Create Clan`
- `Challenge_Title_Sp_2255` -> `Set whether the clan is recruiting.`

These also use different `hash_value`s from the late challenge-title hashes used by `5.lvst`.

### Consequence for `5.lvst` linkage

If we resolve `5.lvst` text hashes against `NPWR04428_00-5`:

- many message hashes still hit
- many late title hashes do **not** hit at all

So `NPWR04428_00-5` should currently be treated as a mixed or repurposed intermediate text bundle, not as a stable reference for reconstructing the late challenge-title layer.

## Update: `NPWR04428_00-3 / -7 / -11` Form a Separate Stable Small Challenge Branch

The three small TSS text variants:

- `NPWR04428_00-3\0x58cf00c0\0\0.act`
- `NPWR04428_00-7\0x58cf00c0\0\0.act`
- `NPWR04428_00-11\0x58cf00c0\0\0.act`

are not random leftovers.

They are structurally identical `799`-entry bundles and each contains:

- `58` `Challenge_Title_Sp_*`
- `75` `Challenge_Msg_Sp_*`

All of these challenge entries are still tokenized with the `0xE020 0x0001` prefix.

### Their challenge-number coverage

Observed title range:

- `1652..2016`

Observed message range:

- `1516..2016`

Representative numbers include:

- `1516`
- `1616`
- `1652`
- `1661..1666`
- `1680`
- `1685..1689`
- `1710`
- `1741..1743`
- `1755..1772`
- `1996..2016`

### Important linkage result

These challenge hashes are **not** referenced by the late large-branch `5.lvst` from:

- `NPWR04428_00-1\0x3f20632f\5.lvst`

But they are referenced directly by the small-branch tables:

- `NPWR04428_00-3\0x3f20632f\5.lvst`
- `NPWR04428_00-7\0x3f20632f\5.lvst`
- `NPWR04428_00-11\0x3f20632f\5.lvst`

Each of those small-branch `5.lvst` files resolves:

- `57` title hashes
- `74` message hashes

against this same small-branch challenge text set.

### Stronger interpretation

The TSS event system therefore appears to have at least two stable challenge-text/table branches:

- large branch:
  - `NPWR04428_00-1 / -9`
  - `1512`-entry text bundle
  - late `2017-12` to `2018-03` challenge set including `21xx` and `22xx`

- small branch:
  - `NPWR04428_00-3 / -7 / -11`
  - `799`-entry text bundle
  - separate challenge family concentrated around `15xx..20xx`

`NPWR04428_00-5` currently sits outside this clean split and still looks like a mixed/intermediate variant.

## Key Reference Files

### Main event text

- `E:\Games\Emulator\ACI\TSS\Unpack\NPWR04428_00-1\0x58cf00c0\0\0.act`

### Base challenge text

- `E:\Games\Emulator\ACI-Reverse-Engineering\ACI-FileSystem-Research\Tools\ACI-File-Tools\output\FullGame\0x375ba2dc\0\160.act`

### Event loading / notice table

- `E:\Games\Emulator\ACI\TSS\Unpack\NPWR04428_00-1\0x58cf00c0\1.lvst`

### Main event/challenge tables

- `E:\Games\Emulator\ACI\TSS\Unpack\NPWR04428_00-1\0x3f20632f\0.lvst`
- `E:\Games\Emulator\ACI\TSS\Unpack\NPWR04428_00-1\0x3f20632f\5.lvst`
- `E:\Games\Emulator\ACI\TSS\Unpack\NPWR04428_00-1\0x3f20632f\6.lvst`
- `E:\Games\Emulator\ACI\TSS\Unpack\NPWR04428_00-1\0x3f20632f\7.lvst`

### Non-event tuning tables

- `E:\Games\Emulator\ACI\TSS\Unpack\NPWR04428_00-9\0xe82647a1\4.lvst`
- `E:\Games\Emulator\ACI\TSS\Unpack\NPWR04428_00-9\0xe82647a1\5.lvst`

## Status

Current confidence is high for:

- identifying `0x58cf00c0/0/0.act` as a live event text bundle
- identifying `0x3f20632f` as a primary live event table group
- proving several direct hash-based links from `.lvst` fields to `.act` labels

Current confidence is moderate for:

- the exact meaning of many numeric columns in `5.lvst`
- the role of `6.lvst`
- the exact interpretation of several low-cardinality flags and packed integer fields

## Schedule Reconstruction Notes

This section summarizes the current best understanding for reviving old events by editing only the TSS event tables.

### Practical high-level conclusion

If the goal is:

- re-enable an already-existing event
- keep its original text/image/hash references
- only move its active time window

then the first place to edit is very likely:

- `0x3f20632f/0.lvst`

and not `FullGame`.

`FullGame` only becomes relevant again if the revived event needs:

- text that no longer exists in the active TSS branch
- images/resources not present in the currently mounted TSS package set
- hashes that point into older base-game-only content

### `0.lvst` currently looks like the main event schedule table

File:

- `E:\Games\Emulator\ACI\TSS\Unpack\NPWR04428_00-1\0x3f20632f\0.lvst`

Observed properties:

- `31` rows
- `41` columns
- contains multiple date/time column pairs
- row ids in the later half clearly form a chronological event chain

The strongest schedule-window columns are:

- `0xEF1CBE0F` = primary start date
- `0x87B328C6` = primary start time
- `0xE25F98D6` = primary end date
- `0x8AF00E1F` = primary end time

There is also a second window pair that often tracks the same activation span:

- `0x72B5C53E` = secondary start date
- `0xC3649538` = secondary start time
- `0xEC64C9A0` = secondary end date
- `0x5DB599A6` = secondary end time

### Important refinement: `0.lvst` does not currently look like the direct `RankEvent` title table

Further direct hash-resolution against:

- `NPWR04428_00-1\0x58cf00c0\0\0.act`

shows that the obvious `Hash` columns in `0.lvst` are not primarily pointing at:

- `ShortName_RankEvent*`
- `LongName_RankEvent*`
- `LoadingMsg_Event_*`
- `LoadingTitle_Event_*`

Instead, the strongest direct matches are currently:

- `0x3078C361` -> `Mail_Title_*`
- `0x67D3BFDF` -> `Mail_Text_*`
- `0x2FDC3474` -> `Mail_Text_Ranking_*`

This is important because it means `0.lvst` is not simply:

- one row per visible event title card

but more likely a mixed schedule / mail / ranking-delivery coordination table.

It still clearly contains major activity windows, but its direct text references currently look much closer to:

- mail title text
- mail body text
- ranking-result mail text

than to top-level `RankEvent` display-title text.

### `0.lvst` row ids are not `RankEvent####` ids

The main row-id-like field:

- `0x3A930195`

contains values such as:

- `10`
- `20`
- `1173`
- `1285`
- `3005`
- `3015`
- `3025`
- `3160`
- `3230`
- `3400`
- `3410`
- `3420`
- `3430`
- `3440`
- `3450`
- `3460`
- `3470`
- `3480`
- `3490`
- `3500`
- `3510`
- `3520`
- `3530`
- `3540`
- `3550`
- `3560`
- `3570`
- `3575`
- `3580`
- `3590`
- `3600`

These do **not** intersect with the numeric range currently observed in:

- `ShortName_RankEvent####`
- `LongName_RankEvent####`

which, in the large branch, is centered around:

- `1033..1124`

So the current best interpretation is:

- `0x3A930195` is an internal schedule/activity row id
- not a direct `RankEvent####` id

### Strong evidence from late rows

Late rows in `0.lvst` include a very clear late-service monthly / weekly schedule pattern:

- row id `3450`
  - `2017-12-01` -> `2018-01-31`
- row id `3460`
  - `2018-01-01` -> `2018-02-28`
- row id `3470`
  - `2018-02-01` -> `2018-03-30`
- row id `3480`
  - `2018-03-01` -> `2018-04-30`
- row id `3490`
  - `2017-10-11` -> `2017-10-18`
- row id `3500`
  - `2017-10-25` -> `2017-11-01`
- row id `3510`
  - `2017-11-08` -> `2017-11-15`
- row id `3520`
  - `2017-11-22` -> `2017-11-29`
- row id `3530`
  - `2017-12-13` -> `2018-01-09`
- row ids `3540`, `3550`, `3560`, `3575`, `3580`, `3590`, `3600`
  - several use `9999-12-31` style open-ended tails

This is currently the strongest evidence that `0.lvst` is the main schedule / activation table for visible live-event rotation.

### `5.lvst` currently looks like challenge-node activation, not just top-level scheduling

File:

- `E:\Games\Emulator\ACI\TSS\Unpack\NPWR04428_00-1\0x3f20632f\5.lvst`

Confirmed date/time columns:

- `0x72B5C53E` = start date
- `0xC3649538` = start time
- `0xEC64C9A0` = end date
- `0x5DB599A6` = end time

Late rows are strongly clustered in:

- `2017-11-30 -> 2017-12-31`
- `2017-12-31 -> 2018-01-31`
- `2018-01-31 -> 2018-02-28`
- `2018-02-28 -> 2018-03-31`
- `2018-03-15 -> 2018-03-31`

Representative late node ids include:

- `1736..1745`
- `1937..2111`

These rows look like challenge-tree / node activation windows that sit under the broader schedule shell exposed by `0.lvst`.

### Current best minimal-revival strategy

For a first revival experiment:

1. choose an event window that already exists in the late `-1/-9` branch
2. edit only `0x3f20632f/0.lvst`
3. move the chosen row's active time window into the present
4. do not change text hashes, event ids, or challenge ids

If that revives the visible event shell but not the underlying challenge content:

5. also edit the matching late rows in `0x3f20632f/5.lvst`

### Best current interpretation

At the moment the cleanest model is:

- `0.lvst` = top-level event schedule / activation table
- `5.lvst` = challenge node / activity tree activation windows

So:

- reviving the event entry/UI may only require `0.lvst`
- reviving the full challenge/task behavior may additionally require `5.lvst`

### Why `FullGame` is probably not needed for a schedule-only recreation

If the revived event stays within:

- existing ids
- existing hash references
- existing TSS branch resources

then editing the schedule tables should be sufficient in principle.

`FullGame` is more likely to matter only when:

- an event references older base-only text
- an event points at missing title/message resources
- an event expects base assets no longer present in the active TSS overlay set

### Updated text-source interpretation after full TSS export

After rescanning the newly exported full:

- `E:\Games\Emulator\ACI\TSS\Unpack`

the earlier "maybe missing from TSS" assumption needs to be tightened.

#### TSS event text coverage is broader than previously assumed

The following TSS files now provide direct evidence that event-shell text is already present inside TSS itself:

- `NPWR04428_00-1\0x58cf00c0\0\0.act`
- `NPWR04428_00-3\0x58cf00c0\0\0.act`
- `NPWR04428_00-5\0x58cf00c0\0\0.act`
- `NPWR04428_00-7\0x58cf00c0\0\0.act`
- `NPWR04428_00-9\0x58cf00c0\0\0.act`
- `NPWR04428_00-11\0x58cf00c0\0\0.act`
- `NPWR04428_00-13\0x58cf00c0\0\0.act`

For the large branch `-1/-5/-9`, `0.act` directly contains large numbers of:

- `ShortName_RankEvent*`
- `LongName_RankEvent*`
- `InfoMsg_RankEvent*`
- `Reward_RankEvent*`
- `LoadingMsg_Event_*`
- `LoadingTitle_Event_*`
- `Mail_Title_*`
- `Mail_Text_*`
- `Challenge_Title_*`
- `Challenge_Msg_*`

So the primary live event shell text is clearly present in TSS.

#### Large-branch text coverage

For `NPWR04428_00-1\0x58cf00c0\0\0.act`:

- `1512` entries total
- `92` `ShortName_RankEvent*`
- `92` `LongName_RankEvent*`
- `2` `InfoMsg_RankEvent*`
- `80` `Reward_RankEvent*`
- `54` `LoadingMsg_Event_*`
- `54` `LoadingTitle_Event_*`
- `79` `Mail_Title_*`
- `105` `Mail_Text_*`
- `266` `Challenge_Title_*`
- `300` `Challenge_Msg_*`

The `-5` and `-9` large-branch variants have the same top-level counts for these event-text families, though `-5` remains semantically unreliable for some challenge-title labels.

#### Small-branch text coverage

For `NPWR04428_00-3/-7/-11\0x58cf00c0\0\0.act`:

- `799` entries total
- `40` `ShortName_RankEvent*`
- `40` `LongName_RankEvent*`
- `2` `InfoMsg_RankEvent*`
- `28` `Reward_RankEvent*`
- `54` `LoadingMsg_Event_*`
- `54` `LoadingTitle_Event_*`
- `90` `Mail_Title_*`
- `114` `Mail_Text_*`
- `58` `Challenge_Title_*`
- `75` `Challenge_Msg_*`

So even the small branch still contains a substantial event-shell text set.

#### `-13` reduced event-text shard

The newly exported:

- `NPWR04428_00-13\0x58cf00c0\0\0.act`

contains a small `180`-entry event-text shard.

Observed coverage:

- `5` `ShortName_RankEvent*`
- `5` `LongName_RankEvent*`
- `2` `InfoMsg_RankEvent*`
- `10` `Reward_RankEvent*`
- `2` `LoadingMsg_Event_*`
- `2` `LoadingTitle_Event_*`
- `27` `Mail_Title_*`
- `27` `Mail_Text_*`
- `5` `Challenge_Msg_*`
- `0` `Challenge_Title_*`

Representative labels include:

- `ShortName_RankEvent5..9`
- `LoadingMsg_Event_1`
- `LoadingMsg_Event_2`
- `Mail_Title_Ranking_*`
- `Mail_Title_Drop_*`

This strongly supports the view that `-13` is a reduced hot-update event-text core rather than a full branch clone.

### Current `FullGame` text-source interpretation

Targeted scanning in:

- `E:\Games\Emulator\ACI-Reverse-Engineering\ACI-FileSystem-Research\Tools\ACI-File-Tools\output\FullGame`

currently supports a narrower role for `FullGame` than a full event-shell dependency.

#### `0x375ba2dc\0\160.act`

This remains the strongest base challenge-text warehouse.

Observed properties:

- `6902` text entries
- very large coverage of:
  - `Challenge_Title_*`
  - `Challenge_Msg_*`
  - `Challenge_Title_Sp_*`
  - `Challenge_Msg_Sp_*`

But after the full TSS export, this now matters less for event-shell reconstruction because those label families are already directly confirmed inside TSS.

So the current best interpretation is now:

- `160.act` is a challenge/base activity text warehouse
- TSS `0x58cf00c0\0\0.act` is the main live event shell text source
- `160.act` remains useful mainly as a challenge/base-text fallback

#### Other `FullGame` ACT hits

Targeted scanning also found several small `FullGame` ACT files containing:

- `Mail_Title_*`
- `Mail_Text_*`

but still no obvious `RankEvent` / `LoadingMsg_Event` style bundles.

Current representative hits include:

- `0x0ac159b1\0\0.act`
- `0x42c1402c\0\0.act`
- `0x4c604a8d\0\0.act`
- `0x6b2e70be\0\0.act`
- `0x871dea9b\0\0.act`
- `0xaa54d953\0\0.act`
- `0xcc2f0024\0\0.act`
- `0xfcc2ac23\0\0.act`

These look more like base mail/support text shards than the primary schedule-shell text source for TSS events.

#### Practical consequence

For schedule-only event revival, the current evidence now very strongly favors:

- `TSS` tables first
- `TSS` event text second
- `FullGame` only as challenge/base-text fallback

### Most useful next table correlation

The next best practical step is to build a direct mapping between:

- `0.lvst` row ids and windows
- the corresponding late `5.lvst` node groups

That would produce the first concrete "event shell -> challenge tree" reconstruction map.

## Direct LVST -> Event Text Linkage Update

Direct hash-resolution against:

- `NPWR04428_00-1\0x58cf00c0\0\0.act`

now supports a more granular split of responsibilities across the TSS tables.

### `0x3f20632f/0.lvst`

Directly resolves mainly into mail-related text:

- `0x3078C361` -> `Mail_Title_*`
- `0x67D3BFDF` -> `Mail_Text_*`
- `0x2FDC3474` -> `Mail_Text_Ranking_*`

So `0.lvst` is currently best treated as:

- schedule / timing coordination
- mail/ranking-delivery text linkage

and not as the direct `RankEvent` display-title table.

### `0x3f20632f/7.lvst`

Currently confirmed direct text hit:

- `0xC793B314` -> `InfoMsg_RankEvent01`

This is consistent with the earlier interpretation that `7.lvst` is closer to ranking/event UI state text mapping than to challenge-tree scheduling.

### `0x58cf00c0/1.lvst`

Currently confirmed direct text hits:

- `0xC87D8BD1` -> `LoadingTitle_Event_93`
- `0xC53EAD08` -> `LoadingMsg_Event_93`

This strongly reinforces the current interpretation that `0x58cf00c0/1.lvst` is the event loading-screen / notice mapping table.

### Current unresolved point

Despite broad TSS text coverage, no direct table has yet been confirmed that simply stores:

- `ShortName_RankEvent####`
- `LongName_RankEvent####`

as plain text-hash fields in the same obvious way that:

- `0.lvst` stores mail text hashes
- `1.lvst` stores loading text hashes

So the current best working hypothesis is:

- `ShortName_RankEvent####` / `LongName_RankEvent####` are likely reached indirectly through one or more numeric ids or intermediate lookup tables
- not through the obvious direct hash columns already identified

## Cross-Table Correlation Update

This section narrows the practical role of the most important `0x3f20632f` tables.

### `3.lvst` is currently the best direct `RankEvent####` schedule table

File:

- `NPWR04428_00-1\0x3f20632f\3.lvst`

Observed structure:

- `202` rows
- `8` columns

Most important current hit:

- `0x59FEC50B`
  - integer ids
  - overlaps `34` late-era `RankEvent` numbers from the large-branch text set
  - confirmed examples include:
    - `1058`
    - `1060`
    - `1062`
    - `1064`
    - `1065`
    - `1066`
    - `1067`
    - `1068`
    - `1069`
    - `1070`
    - `1071`
    - `1072`
    - `1073`
    - `1074`
    - `1075`
    - `1076`
    - `1077`
    - `1078`
    - `1079`
    - `1080`
    - `1081`
    - `1082`
    - `1083`
    - `1084`
    - `1085`
    - `1086`
    - `1087`
    - `1088`
    - `1089`
    - `1090`
    - `1091`
    - `1092`
    - `1093`
    - `1094`

The surrounding row pattern is highly schedule-like:

- `0xC9593D6F` = start date
- `0xDF8C1FB7` = start time
- `0x8CA04356` = end date
- `0x38A4B1DD` = end time

Representative rows:

- `1058` -> `2015-05-22` to `2015-06-01`
- `1068` -> `2015-08-07` to `2015-08-17`
- `1074` -> `2015-10-16` to `2015-10-19`
- `1088` -> `2016-01-27` to `2016-02-01`
- `1094` -> `2016-03-30` to `3000-01-01`

Important direct text linkage:

- `0x67D3BFDF` is constant across the late `RankEvent` rows and resolves to:
  - `0xCEBCD43F`
  - `PresenceStr_19` in `FullGame\0x375ba2dc\0\160.act`

So `3.lvst` currently looks like:

- a direct late-era `RankEvent####` timeline table
- but not yet a direct short-name / long-name text-hash table

### `3.lvst` schedule text hash is not a reliable event-title field

Further correlation work now strongly indicates that:

- `0x67D3BFDF` in `3.lvst` is not the actual visible event-title source
- the late-era ranking-event rows reuse the same hash repeatedly
- the most common reused value is:
  - `0xCEBCD43F`
  - resolved in `FullGame\0x375ba2dc\0\160.act` as `PresenceStr_19`
  - English text: `Team Death Match: Tuning aircraft to sortie`

Representative late-era rows that all reuse `0xCEBCD43F` include:

- `1003`
- `1004`
- `1005`
- `1058`
- `2015072201`
- `2015081701`
- `2015100901`
- `2015120401`

This means `3.lvst` should currently be treated as:

- a timing / activation table
- not a direct event-title table
- and not a safe source for the display name shown by the game UI

## Ranking Event Runtime Name Model Update

The current strongest model is that visible ranking-event names are resolved indirectly at runtime rather than being read directly from `3.lvst`.

### `10.lvst` is currently the best ranking-event display/rule mapping table

File:

- `NPWR04428_00-11\0x3f20632f\10.lvst`

This table can now be joined directly back to `3.lvst`.

Confirmed join:

- `10.lvst` column `0x5CBA6059`
- matches `3.lvst` column `0x59FEC50B` (`event_id`)

This join holds for all currently inspected ranking-event rows in the small branch, including:

- `2015072201`
- `2015081701`
- `2015081702`
- `2015081703`
- `2015081704`
- `2015100201`
- `2015100202`
- `2015100901`
- `2015100902`
- `2015120401`
- `2015120402`
- `2015120403`
- `2015120404`
- `2016022201`

So `10.lvst` is currently best treated as:

- a ranking-event rule/config table
- a display-category mapping table
- the missing layer between `3.lvst` schedule rows and runtime-visible event naming

### Best current column meanings for `10.lvst`

The following column interpretations are now the strongest working model:

- `0x5CBA6059`
  - schedule/event id
  - joins directly to `3.lvst.event_id`

- `0xD89CE092`
  - mission/rule-family text hash
  - examples:
    - `MissionId_RankEvent1500`
    - `MissionId_RankEvent2000`
    - `MissionId_RankEvent2500`
    - `MissionId_RankEvent3000`
    - `MissionId_RankEvent3500`

- `0x469A8F16`
  - menu title/category text hash
  - examples:
    - `MenuItem_Main_001`
    - `MenuItem_Main_024`
    - `MenuItem_Main_033`
    - `MenuItem_Main_036`
    - `MenuItem_Main_039`

- `0x94D96AA2`
  - menu description / event-mode explanation hash
  - examples:
    - `MenuDesc_Main_001`
    - `MenuDesc_Main_024`
    - `MenuDesc_Main_033`
    - `MenuDesc_Main_040`
    - `MenuDesc_Main_043`
    - `MenuDesc_Main_999`

- `0xE3CB71BA`
  - aircraft restriction / allowed-aircraft set hash
  - examples:
    - `AircraftId_RankEvent1000`
    - `AircraftId_RankEvent1069`
    - debug-style aircraft restriction lists such as `Debug_AcIdF14`

### Representative `10.lvst` mappings

Observed examples:

- `2015100901`
  - `mission = MissionId_RankEvent2000`
  - menu title family = `MenuItem_Main_024`
  - menu description family = `MenuDesc_Main_024`
  - interpretation: standard limited-time Team Deathmatch family

- `2015120401`
  - `mission = MissionId_RankEvent3000`
  - menu title family = `MenuItem_Main_024`
  - menu description family = `MenuDesc_Main_024`
  - interpretation: Ring Battle variant under the TDM ranking-event presentation family

- `2016022201`
  - `mission = MissionId_RankEvent2500`
  - menu title family = `MenuItem_Main_024`
  - menu description family = `MenuDesc_Main_999`
  - interpretation: Naval Fleet Assault variant under the TDM ranking-event presentation family

- `2015100201`
  - `mission = MissionId_RankEvent1500`
  - menu title family = `MenuItem_Main_036`
  - menu description family = `MenuDesc_Main_040`
  - interpretation: limited-time cost-restricted co-op ranking-event family

- `2015073102`
  - `mission = MissionId_RankEvent1500`
  - menu title family = `MenuItem_Main_033`
  - menu description family = `MenuDesc_Main_033`
  - interpretation: limited-time piston-aircraft event family

### Lua runtime confirms an indirect `RankingEventInfo` name path

Relevant Lua/script strings found in both TSS and FullGame ranking-event UI scripts include:

- `GetRankingEventInfoNum`
- `GetRankingEventInfo`
- `GetRankingEventInfoByEventId`
- `GetRankingEventNoticeInfo`
- `NoticeRankingEvent`
- `_evSNameTxtId`
- `_rankTypeTxtId`
- `_missionTxtId`
- `_rewardTxtId`

This strongly suggests the game UI does not simply read `3.lvst.text_hash` and show it as the title.

Current best runtime chain:

1. `3.lvst` provides the schedule / activation row
2. `10.lvst` provides the ranking-event rule/display family mapping
3. runtime code queries `RankingEventInfo`
4. returned runtime fields include:
   - short-name text id
   - rank-type text id
   - mission text id
   - reward text id
5. UI renders those runtime-provided ids rather than the shared `3.lvst` text hash

### Practical implication

For ranking events, the safest current display-name model is:

- do not trust `3.lvst.0x67D3BFDF` as the event title
- treat `10.lvst + runtime RankingEventInfo` as the real naming path
- use `10.lvst` mission/menu/description families as the best current proxy for reconstructing visible event identity

### `8.lvst` is the clearest compact `RankEvent` pairing / bundle table

File:

- `NPWR04428_00-1\0x3f20632f\8.lvst`

Observed structure:

- `33` rows
- `28` columns

Most important current hits:

- `0x1F11A4B3`
- `0xA8415CAD`

Both columns heavily overlap the late `RankEvent` number range.

Representative row pattern:

- row `0`: `1056 / 1056`
- row `1`: `1057 / 1058`
- row `2`: `1059 / 1060`
- row `3`: `1061 / 1062`
- row `4`: `1063 / 1064`
- many later rows become `N / N`

This table is much more compact and uniform than `3.lvst`.

Important observations:

- many rows pair adjacent event ids
- `0x9B1CC9CB` carries compact numeric values such as:
  - `2015081804`
  - `2015082101`
- several control-like columns are nearly constant:
  - `0x287224C7 = 1`
  - `0xC87CA5B6 = 4`
  - `0x2C51C016 = 4`
  - `0xE642F3D3 = 1`
  - `0x5828DCA5 = 1`
  - `0x0803D2B6 = 1`

Current best interpretation:

- `8.lvst` is a compact late-era event-bundle lookup
- it likely groups or pairs closely related `RankEvent` ids
- it still does not directly resolve to `ShortName_RankEvent####` / `LongName_RankEvent####`

### `5.lvst` is still best modeled as challenge-node composition, not as the primary `RankEvent` title table

File:

- `NPWR04428_00-1\0x3f20632f\5.lvst`

Important numeric overlap update:

- `0xF7740E1D`
  - overlaps `26` `RankEvent`-like ids
- `0xDE439831`
  - overlaps only `6` ids:
    - `1054`
    - `1105`
    - `1106`
    - `1107`
    - `1108`
    - `1109`

This is still weaker and less timeline-like than `3.lvst`.

The strongest confirmed role of `5.lvst` remains:

- challenge progression tree
- challenge title / message binding
- node chain composition

Important direct text columns remain:

- `0x26B6DAC0` -> `Challenge_Title_Sp_*`
- `0xF67C9878` -> `Challenge_Msg_Sp_*`

So `0xF7740E1D` is currently best treated as:

- a challenge-side event-family / template / linkage id
- not yet as proof that `5.lvst` is the master `RankEvent` display table

### `6.lvst` looks like a dense challenge-detail / reward-condition matrix with partial `RankEvent`-range overlap

File:

- `NPWR04428_00-1\0x3f20632f\6.lvst`

Observed structure:

- `646` rows
- `60` columns

Important overlap columns:

- `0xC3B1A215`
  - overlaps `44` `RankEvent`-range values
- `0xD0575984`
  - overlaps `20` `RankEvent`-range values

However, row structure here is much denser and looks more like:

- internal challenge/detail rows
- reward / target / parameter rows
- per-step or per-condition configuration

Some rows clearly mix `RankEvent`-range values with unrelated challenge-range values such as:

- `1012`
- `1032`
- `1046`
- `163`
- `172`
- `174`
- `2071`
- `2121`
- `2178`
- `2235`

Current best interpretation:

- `6.lvst` is not the clean front-door event schedule table
- it is more likely a subordinate detail/config matrix used by challenge/activity systems

### `0x58cf00c0/1.lvst` is now better understood as event loading-card configuration

File:

- `NPWR04428_00-1\0x58cf00c0\1.lvst`

Observed structure:

- `201` rows
- `15` columns

Already confirmed:

- `0xC87D8BD1` -> `LoadingTitle_Event_93`
- `0xC53EAD08` -> `LoadingMsg_Event_93`

New clarification from `FullGame` ACT lookup:

- `0x157828D3` in `FullGame` resolves to:
  - `AcName_f22a`
- `0xB343B1B2` in `FullGame` resolves to:
  - `AcShortDesc_f22a`

This matches the first-row `1.lvst` payload:

- `0x46C566D8 = "f22a"`
- `0xC87D8BD1 = LoadingTitle_Event_93`
- `0xC53EAD08 = LoadingMsg_Event_93`

So `1.lvst` currently looks like it binds together:

- event loading title text
- event loading message text
- a compact asset/card identifier such as `f22a`
- likely one or more external presentation resources not stored as ACEText labels in the TSS `0.act`

## Current Best Practical Model

For actual event revival work, the most productive current split is:

1. `0x3f20632f\0.lvst`
   - top-level schedule / mail / ranking-delivery coordination

2. `0x3f20632f\3.lvst`
   - late-era `RankEvent####` schedule timeline

3. `0x3f20632f\5.lvst`
   - challenge node tree and `Challenge_Title_Sp_*` / `Challenge_Msg_Sp_*` linkage

4. `0x3f20632f\6.lvst`
   - dense challenge detail / reward-condition matrix

5. `0x3f20632f\8.lvst`
   - compact late-era `RankEvent` bundle / pair lookup

6. `0x58cf00c0\1.lvst`
   - loading-card / event notice presentation mapping

The most useful next reconstruction target is now:

- build a row-level linkage between `3.lvst` event ids and the relevant subsets in `5.lvst` / `6.lvst` / `8.lvst`
- instead of continuing broad scans across unrelated top-level groups

## Sample Single-Event Chains

The following two samples are useful because they show two different linkage shapes:

- `1068`
  - present in `3.lvst`
  - present in `8.lvst`
  - present in `6.lvst`
  - not directly hit in `5.lvst`
- `1074`
  - present in `3.lvst`
  - present in `8.lvst`
  - directly present in `5.lvst`
  - not directly hit in `6.lvst`

This strongly suggests that the event system is not driven by a single uniform linkage table.

### Sample: `RankEvent1068`

Direct TSS text labels confirmed:

- `ShortName_RankEvent1068`
- `LongName_RankEvent1068`
- `Reward_RankEvent1068`
- `Mail_Text_Ranking_1068`

#### `3.lvst`

Direct row:

- `0x59FEC50B = 1068`
- start:
  - `2015-08-07 22:13:20`
- end:
  - `2015-08-17 22:13:20`
- shared text-like side link:
  - `0x67D3BFDF -> PresenceStr_19` in `FullGame\0x375ba2dc\0\160.act`

So `3.lvst` clearly treats `1068` as a timed event id.

#### `8.lvst`

Direct row:

- `0x1F11A4B3 = 1068`
- `0xA8415CAD = 1068`
- `0x9B1CC9CB = 2015082101`

The `1068 / 1068` self-pair is notable because some nearby rows use paired adjacent ids instead.

Current implication:

- `8.lvst` likely stores a compact event-bundle or presentation-side lookup for `1068`
- but it still does not expose direct `ShortName_RankEvent1068` / `LongName_RankEvent1068` hashes

#### `6.lvst`

Direct row:

- `0xC3B1A215 = 1068`
- `0x233E40C9 = 2016061603`
- `0xDD3BA8C2 = 710008`
- `0x2169275B = 2040520`
- `0x49D0C120 = 16090108`
- `0xA52E91FE = 710013`
- `0x4BDA5325 = 13082250`
- `0x73076217 = 3`
- `0xD0575984 = 163`
- `0xE3BE8242 = 20`

Resolved text/resource labels in the same row:

- `0x0772A233 -> AcColorName_f15e_006`
- `0x02546AE7 -> AcColorDesc_f15e_006`
- `0x65F376FC -> EmblemName_163`
- `0x60D5BE28 -> EmblemDesc_163`

Current implication:

- `6.lvst` can carry rows keyed by a `RankEvent` id
- but those rows look like subordinate reward/config/detail rows, not the top-level event title mapping

#### Current best chain for `1068`

- `3.lvst` gives the timed event-id window
- `8.lvst` gives a compact event-bundle record
- `6.lvst` gives a subordinate reward/config row
- no direct `5.lvst` hit was observed for `1068`

So `1068` currently looks like a case where:

- `3 + 8 + 6`

is the strongest visible linkage surface.

### Sample: `RankEvent1074`

Direct TSS text labels confirmed:

- `ShortName_RankEvent1074`
- `LongName_RankEvent1074`
- `Reward_RankEvent1074`
- `Mail_Text_Ranking_1074`

#### `3.lvst`

Direct row:

- `0x59FEC50B = 1074`
- start:
  - `2015-10-16 22:13:20`
- end:
  - `2015-10-19 22:13:20`
- shared side link:
  - `0x67D3BFDF -> PresenceStr_19`

#### `8.lvst`

Direct row:

- `0x1F11A4B3 = 1074`
- `0xA8415CAD = 1074`
- `0x9B1CC9CB = 2015082101`

This is structurally similar to the `1068` compact-bundle row.

#### `5.lvst`

Direct challenge-tree row:

- row id:
  - `0x56CB07C4 = 1993`
- window:
  - `2017-12-26 22:13:20`
  - through `2018-01-15 21:05:59`
- direct event-family hit:
  - `0xF7740E1D = 1074`
- challenge text:
  - `0x26B6DAC0 -> Challenge_Title_Sp_2155`
  - `0xF67C9878 -> Challenge_Msg_Sp_2155`
- notable compact parameters:
  - `0x0D6BDED7 = 1`
  - `0x7A3A1AD3 = 15`
  - `0x75CA4FC9 = 3`
  - `0x37E12563 = 33555800`
  - `0xD4FF61C1 = 1`
  - `0x3AA203BA = 65597`
  - `0xD9BC4718 = 10000`
  - `0xDE439831 = 1054`

This is currently the cleanest direct example of:

- a `RankEvent####` id in `5.lvst`
- tied straight to a concrete `Challenge_Title_Sp_*` / `Challenge_Msg_Sp_*` row

#### `0.lvst`

`Mail_Text_Ranking_1074` is referenced directly by multiple rows in `0.lvst`, including:

- row id `3025`
  - `Mail_Title_Basic_084`
  - `Mail_Text_Basic_084`
  - date window `2016-06-28` to `2016-07-20`
  - `0x2FDC3474 -> Mail_Text_Ranking_1074`
- row id `3470`
  - `Mail_Title_Drop_085`
  - `Mail_Text_Drop_085`
  - date window `2018-02-01` to `2018-03-30`
  - `0x2FDC3474 -> Mail_Text_Ranking_1074`
- row id `3570`
  - `Mail_Title_Basic_095`
  - `Mail_Text_Basic_095`
  - date window `2018-01-01` to `2018-03-01`
  - gift-name side references also appear
  - `0x2FDC3474 -> Mail_Text_Ranking_1074`

Important implication:

- `0.lvst` mail/ranking-delivery rows can reuse the same ranking-mail text across multiple schedule rows
- so `0.lvst` row ids should not be treated as one-to-one with `RankEvent####`

#### Current best chain for `1074`

- `3.lvst` gives the event-id schedule row
- `8.lvst` gives the compact event-bundle row
- `5.lvst` gives a direct challenge-tree row with `Challenge_Title_Sp_2155`
- `0.lvst` gives ranking-mail delivery rows for `Mail_Text_Ranking_1074`

So `1074` currently looks like the clearest practical reconstruction sample for:

- `event id -> challenge node -> ranking mail`

## Practical Interpretation of the Two Samples

The contrast between `1068` and `1074` suggests:

- `3.lvst` is the most stable direct timed-event-id surface
- `8.lvst` is a compact companion lookup that often mirrors those ids
- `5.lvst` only exposes some `RankEvent####` ids directly
- `6.lvst` can also expose some `RankEvent####` ids, but in a more subordinate reward/config role
- `0.lvst` is mail/ranking-delivery oriented and can reuse one ranking-mail text across multiple schedule rows

This means the safest next reverse-engineering direction is not:

- assume one universal one-row-per-event master table

but instead:

- treat each `RankEvent####` as potentially spanning:
  - one timing row in `3.lvst`
  - one compact lookup row in `8.lvst`
  - zero or more challenge/config rows in `5.lvst` and `6.lvst`
  - zero or more mail/ranking-delivery rows in `0.lvst`

## `-13` / `-14` Coverage Update

This section matters for deciding the smallest realistic TSS patch set for event revival.

### `-14` remains UI-only

`NPWR04428_00-14` still contains only:

- `0x62bbe64d`
- `0x6976b3b3`
- `0x6ff8c094`
- `0x9b9969d5`

It does not contain:

- `0x3f20632f`
- `0x58cf00c0`

So `-14` currently looks irrelevant for:

- event schedule rows
- event text tables
- challenge-node logic tables

and relevant only for:

- menu / banner / presentation-side UI assets

### `-13` is a reduced early-only hot-update core, not a late-event override

`NPWR04428_00-13` does contain:

- `0x3f20632f`
- `0x58cf00c0`

but the payload is heavily reduced relative to `-1`.

Observed table shrinkage:

- `0.lvst`
  - `31` rows in `-1`
  - `16` rows in `-13`
- `3.lvst`
  - `202` rows in `-1`
  - `13` rows in `-13`
- `5.lvst`
  - `207` rows in `-1`
  - `65` rows in `-13`
- `7.lvst`
  - `21` rows in `-1`
  - `7` rows in `-13`
- `8.lvst`
  - `33` rows in `-1`
  - `20` rows in `-13`

The text side is also clearly early-only:

- `ShortName_RankEvent5..9`
- `LongName_RankEvent5..9`
- `Reward_RankEvent5..15`
- `Mail_Text_Ranking_001..132`
- `LoadingTitle_Event_1`
- `LoadingTitle_Event_2`
- `LoadingMsg_Event_1`
- `LoadingMsg_Event_2`

### `1074` is absent from `-13`

Targeted checks for `1074` found:

- `ShortName_RankEvent1074`
  - missing in `-13` `0.act`
- `LongName_RankEvent1074`
  - missing
- `Reward_RankEvent1074`
  - missing
- `Mail_Text_Ranking_1074`
  - missing

and direct table scans found no `1074` hits in `-13`:

- `0.lvst`
- `1.lvst`
- `3.lvst`
- `5.lvst`
- `6.lvst`
- `7.lvst`
- `8.lvst`

So `-13` should currently be treated as:

- a reduced hot-update shard for much earlier event families
- not as an override layer for late `RankEvent1074` content

### `-13` `1.lvst` also confirms the early-only pattern

Resolved text labels in `NPWR04428_00-13\0x58cf00c0\1.lvst` currently only expose:

- `LoadingTitle_Event_1`
- `LoadingTitle_Event_2`
- `LoadingMsg_Event_1`
- `LoadingMsg_Event_2`

This further supports the current interpretation that:

- `-13` is not carrying late-era loading-card overrides for `1074`

## Current Best Minimal Patch-Set Hypothesis for `1074`

If the goal is specifically to revive a late-era event like `1074`, the current evidence suggests the minimum useful logic/data surface is still in the main complete branch, not in `-13` or `-14`.

Current best hypothesis:

1. main late branch tables and text
   - `NPWR04428_00-1`
   - and likely equivalent late branch siblings `-5` / `-9`

2. critical resources for `1074` appear to live in:
   - `0x58cf00c0\0\0.act`
   - `0x3f20632f\3.lvst`
   - `0x3f20632f\5.lvst`
   - `0x3f20632f\8.lvst`
   - `0x3f20632f\0.lvst`

3. optional / still unproven supporting logic may also involve:
   - `0x3f20632f\6.lvst`

4. `-13` is probably not required for `1074` revival
   - because it does not carry `1074` text or table rows

5. `-14` is probably not required for `1074` logic revival
   - unless the goal also includes restoring matching menu/banner presentation assets

### Practical takeaway

For late-event reconstruction, the safest current assumption is:

- revive the event from the full late branch first
- treat `-13` as a separate early hot-update shard
- treat `-14` as presentation-only

This is a much narrower and more actionable patch target than "modify every TSS layer that exists."

## Late-Branch `-1 / -5 / -9` Comparison for `1074`

Targeted comparison across:

- `NPWR04428_00-1`
- `NPWR04428_00-5`
- `NPWR04428_00-9`

shows that the late-branch story is narrower than it first looked.

### `1074` itself matches across all three late branches

For `RankEvent1074`, the following resources are effectively the same across `-1 / -5 / -9`:

- `0x3f20632f\0.lvst`
- `0x3f20632f\5.lvst`
- `0x3f20632f\8.lvst`

The `1074`-specific rows pulled from those tables match across all three branches.

Direct `ACEText` entries for:

- `ShortName_RankEvent1074`
- `LongName_RankEvent1074`
- `Reward_RankEvent1074`
- `Mail_Text_Ranking_1074`

also matched across `-1 / -5 / -9` in the targeted comparison.

### `-5` differs globally, but not on the `1074` rows we care about

File hashes show:

- `0x58cf00c0\0\0.act`
  - `-1` and `-9` are byte-identical
  - `-5` is different
- `0x3f20632f\3.lvst`
  - `-1` and `-9` are byte-identical
  - `-5` is different

However, the targeted `1074` rows did not differ.

### `3.lvst` difference between `-1` and `-5` is extremely small

A row-by-row comparison of:

- `NPWR04428_00-1\0x3f20632f\3.lvst`
- `NPWR04428_00-5\0x3f20632f\3.lvst`

found only one changed row out of `202`.

Changed row key:

- `0x59FEC50B = 2015081701`

Changed field:

- end date:
  - `-1`: `2016-12-31`
  - `-5`: `3000-12-31`

Important implication:

- the `-5` branch does not represent a broadly different late-event schedule table
- at least in `3.lvst`, it differs by only a tiny patch-like adjustment unrelated to `1074`

### Current best interpretation of the late complete branches

For practical event-revival work:

- `-1` and `-9` can currently be treated as the same late baseline
- `-5` looks like a lightly patched late variant
- but the `1074` chain currently does not depend on the observed `-5`-only differences

### Practical takeaway for `1074`

If the goal is to reconstruct or revive `1074`, the current safest assumption is:

- use `-1` as the primary late-branch reference
- treat `-9` as confirming parity with `-1`
- treat `-5` as an intermediate variant whose known differences do not currently affect the `1074` chain

## `1074` Minimum Resource Checklist

This is the current smallest practical checklist for the late-event sample `1074`, based on the strongest confirmed links in `NPWR04428_00-1`.

### Primary text labels in `0x58cf00c0\0\0.act`

Directly confirmed labels:

- `ShortName_RankEvent1074`
  - hash `0xC5C35E47`
- `LongName_RankEvent1074`
  - hash `0x5C17A76D`
- `Reward_RankEvent1074`
  - hash `0x49971A2D`
- `Mail_Text_Ranking_1074`
  - hash `0xE03BD066`

### Challenge text labels in `0x58cf00c0\0\0.act`

Directly tied from `5.lvst`:

- `Challenge_Title_Sp_2155`
  - hash `0xEFA4819F`
- `Challenge_Msg_Sp_2155`
  - hash `0x3184BFE3`

### Mail text labels currently tied to the same ranking-mail text

Observed in `0.lvst` rows that also point to `Mail_Text_Ranking_1074`:

- `Mail_Title_Basic_084`
  - hash `0x76B14D50`
- `Mail_Text_Basic_084`
  - hash `0x66798B3B`
- `Mail_Title_Drop_085`
  - hash `0x26121888`
- `Mail_Text_Drop_085`
  - hash `0x23151525`
- `Mail_Title_Basic_095`
  - hash `0xA069913B`
- `Mail_Text_Basic_095`
  - hash `0xB0A15750`

Important caution:

- these are not proven to be one-to-one "the 1074 event title/body"
- they are mail-side texts that happen to share the `Mail_Text_Ranking_1074` linkage

### Mandatory table rows currently tied to `1074`

#### `0x3f20632f\3.lvst`

Direct timing row:

- key:
  - `0x59FEC50B = 1074`
- start:
  - `2015-10-16 22:13:20`
- end:
  - `2015-10-19 22:13:20`
- side text:
  - `0x67D3BFDF = 0xCEBCD43F`
  - resolves to `PresenceStr_19` in `FullGame\0x375ba2dc\0\160.act`

#### `0x3f20632f\5.lvst`

Direct challenge row:

- row id:
  - `0x56CB07C4 = 1993`
- date window:
  - `2017-12-26 22:13:20`
  - to `2018-01-15 21:05:59`
- event-family key:
  - `0xF7740E1D = 1074`
- challenge text:
  - `0x26B6DAC0 = 0xEFA4819F = Challenge_Title_Sp_2155`
  - `0xF67C9878 = 0x3184BFE3 = Challenge_Msg_Sp_2155`
- notable compact fields:
  - `0x0D6BDED7 = 1`
  - `0x7A3A1AD3 = 15`
  - `0x75CA4FC9 = 3`
  - `0x37E12563 = 33555800`
  - `0xD4FF61C1 = 1`
  - `0x3AA203BA = 65597`
  - `0xD9BC4718 = 10000`
  - `0xDE439831 = 1054`

#### `0x3f20632f\8.lvst`

Direct compact lookup row:

- `0x1F11A4B3 = 1074`
- `0xA8415CAD = 1074`
- `0x9B1CC9CB = 2015082101`
- stable companion values:
  - `0x9FFC816B = 3`
  - `0x81C6A2E2 = 3`
  - `0xE45D38C5 = 2`
  - `0x78672CE1 = 1`
  - `0x0FA8F878 = 1`
  - `0x5F83F66B = 1`
  - `0x287224C7 = 1`
  - `0xC87CA5B6 = 4`
  - `0x2C51C016 = 4`
  - `0xE642F3D3 = 1`
  - `0x5828DCA5 = 1`
  - `0x0803D2B6 = 1`
- float quartet:
  - `0xB25D305F = 25.0`
  - `0x034FFFF3 = 25.0`
  - `0x3C3D4209 = 15.0`
  - `0xFBF0F746 = 135.0`

#### `0x3f20632f\0.lvst`

Direct ranking-mail-linked rows:

- row `3025`
  - `0x2FDC3474 = 0xE03BD066 = Mail_Text_Ranking_1074`
  - date window `2016-06-28` to `2016-07-20`
  - `Mail_Title_Basic_084`
  - `Mail_Text_Basic_084`
- row `3470`
  - `0x2FDC3474 = 0xE03BD066 = Mail_Text_Ranking_1074`
  - date window `2018-02-01` to `2018-03-30`
  - `Mail_Title_Drop_085`
  - `Mail_Text_Drop_085`
- row `3570`
  - `0x2FDC3474 = 0xE03BD066 = Mail_Text_Ranking_1074`
  - date window `2018-01-01` to `2018-03-01`
  - `Mail_Title_Basic_095`
  - `Mail_Text_Basic_095`
  - gift-side helper references also appear in this row

### Current minimum practical data surface for `1074`

If the goal is to manually reproduce the currently visible `1074` chain, the smallest confirmed set is:

- one event-name text set in `0.act`
  - `ShortName_RankEvent1074`
  - `LongName_RankEvent1074`
  - `Reward_RankEvent1074`
  - `Mail_Text_Ranking_1074`
- one timing row in `3.lvst`
  - key `1074`
- one challenge row in `5.lvst`
  - row id `1993`
- one compact lookup row in `8.lvst`
  - `1074 / 1074`
- at least one mail/ranking row in `0.lvst`
  - exact minimum still unproven, because multiple rows reuse the same ranking-mail text

### Current uncertainty that still remains

The weakest part of the current checklist is still `0.lvst`.

What is already proven:

- multiple `0.lvst` rows reuse `Mail_Text_Ranking_1074`

What is not yet proven:

- which one of those rows is the truly essential row for making `1074` function
- whether all of them are historical leftovers, staged mail deliveries, or separate reward cycles for the same event family

## `0.lvst` Ranking-Mail Reuse Pattern

Focused review of all `31` `0.lvst` rows that reference `Mail_Text_Ranking_*` now shows a strong repeated pattern:

- every observed `Mail_Text_Ranking_*` label is reused by multiple rows
- the rows differ in:
  - date window
  - mail title
  - mail body
  - optional gift-side payload fields

This means `0.lvst` should currently be modeled as:

- a ranking-mail schedule table
- not a one-row-per-event ownership table

### Reuse pattern for the late sample family

Observed repeated ranking-mail labels include:

- `Mail_Text_Ranking_1073`
  - rows `3230`, `3490`, `3580`
- `Mail_Text_Ranking_1074`
  - rows `3025`, `3470`, `3570`
- `Mail_Text_Ranking_1075`
  - rows `3005`, `3450`, `3550`
- `Mail_Text_Ranking_1076`
  - rows `1173`, `3430`, `3530`
- `Mail_Text_Ranking_1077`
  - rows `10`, `3410`, `3510`, `3600`
- `Mail_Text_Ranking_2073`
  - rows `3400`, `3500`, `3590`
- `Mail_Text_Ranking_2074`
  - rows `3160`, `3480`, `3575`
- `Mail_Text_Ranking_2075`
  - rows `3015`, `3460`, `3560`
- `Mail_Text_Ranking_2076`
  - rows `1285`, `3440`, `3540`
- `Mail_Text_Ranking_2077`
  - rows `20`, `3420`, `3520`

This is strong evidence that:

- one ranking-mail text id can participate in several mail-delivery schedule rows over time

### `1074`-specific ranking-mail rows

The current `Mail_Text_Ranking_1074` rows are:

- row `3025`
  - `2016-06-28` to `2016-07-20`
  - `Mail_Title_Basic_084`
  - `Mail_Text_Basic_084`
  - no gift payload fields populated
- row `3470`
  - `2018-02-01` to `2018-03-01`
  - `Mail_Title_Drop_085`
  - `Mail_Text_Drop_085`
  - no gift payload fields populated
- row `3570`
  - `2018-01-01` to `2018-01-01`
  - secondary window `2018-01-01` to `2018-03-01`
  - `Mail_Title_Basic_095`
  - `Mail_Text_Basic_095`
  - gift-side payload fields are populated

### Current best interpretation of the three `1074` rows

The current evidence fits "staged mail scheduling" better than "historical leftovers."

Reasons:

- this exact multi-row reuse pattern also appears for nearby families:
  - `1073`
  - `1075`
  - `1076`
  - `1077`
  - and the parallel `207x` set
- the rows are not random duplicates
- they form structured late-era windows with changing mail-title/mail-body payloads

So the current best working interpretation is:

- `3025 / 3470 / 3570` are probably different mail-delivery schedule rows for the same `Mail_Text_Ranking_1074` family
- not just accidental leftovers

### Updated practical takeaway for the `1074` minimum set

For `1074`, `0.lvst` should currently be treated as:

- one required mail-schedule subsystem
- with at least one ranking-mail row definitely needed
- and possibly more than one row needed if the goal is to reproduce the full late behavior rather than just a minimally bootable event

The current safest conservative assumption is:

- keep all three `1074`-linked rows together until a smaller proven subset is established

## `1073 / 1074 / 1075` Neighbor Comparison

Comparing the neighboring late-family ids `1073 / 1074 / 1075` helps clarify which parts of the pipeline are actually continuous.

### `3.lvst` timing rows are cleanly consecutive

Observed late timing rows:

- `1073`
  - `2015-10-09` to `2015-10-13`
- `1074`
  - `2015-10-16` to `2015-10-19`
- `1075`
  - `2015-10-23` to `2015-10-26`

So `3.lvst` still behaves like a clean consecutive event-id timeline surface here.

### `8.lvst` compact lookup rows are also consecutive

Observed direct rows:

- `1073 / 1073`
- `1074 / 1074`
- `1075 / 1075`

with the usual shared companion structure.

Notable floating values:

- `1073`
  - `21.5 / 21.5 / 14.0 / 119.0`
- `1074`
  - `25.0 / 25.0 / 15.0 / 135.0`
- `1075`
  - `27.0 / 27.0 / 16.0 / 152.0`

So `8.lvst` also preserves a local consecutive pattern for this family.

### `5.lvst` only directly exposes `1074` and `1075`

Direct `5.lvst` hits:

- `1075`
  - row id `1992`
  - window `2017-12-26 22:13:20` to `2018-01-15 21:05:59`
  - `Challenge_Title_Sp_2154`
  - `Challenge_Msg_Sp_2154`
  - `0xDE439831 = 1109`
- `1074`
  - row id `1993`
  - same window `2017-12-26 22:13:20` to `2018-01-15 21:05:59`
  - `Challenge_Title_Sp_2155`
  - `Challenge_Msg_Sp_2155`
  - `0xDE439831 = 1054`

No direct `5.lvst` row was found for:

- `1073`

This is a strong sign that:

- `5.lvst` is not a complete one-row mirror of the `3.lvst` timeline
- direct challenge linkage only exists for some members of the neighboring ranking-id family

### `1074` and `1075` form an adjacent challenge-row pair

The two direct challenge rows are:

- `1992 -> 1075`
- `1993 -> 1074`

Shared properties:

- same date window
- same broad row family
- same `0xDE83BF5C = 257`
- same `0xD4FF61C1 = 1`
- same `0xD9BC4718 = 10000`
- both use late `Challenge_Title_Sp_215x` / `Challenge_Msg_Sp_215x`

This is currently the clearest evidence that:

- late `5.lvst` sometimes groups neighboring ranking ids into a compact challenge batch

### `0.lvst` shows a three-row family pattern for each ranking-mail id

For all three sampled ranking families:

- `1073`
  - rows `3230`, `3490`, `3580`
- `1074`
  - rows `3025`, `3470`, `3570`
- `1075`
  - rows `3005`, `3450`, `3550`

and the same pattern also appears for the paired `2073 / 2074 / 2075` family.

### Current best interpretation of the three-row `0.lvst` pattern

The neighboring comparison suggests `0.lvst` contains at least two temporal strata:

1. one older row for the ranking-mail text family
   - examples:
     - `1075 -> row 3005`
     - `1074 -> row 3025`
     - `1073 -> row 3230`
2. one or two later rows clustered in the `34xx / 35xx` range
   - examples:
     - `1075 -> rows 3450 / 3550`
     - `1074 -> rows 3470 / 3570`
     - `1073 -> rows 3490 / 3580`

This now makes "historical reuse plus late-stage scheduling" a better fit than "all three rows belong equally to one single event instance."

### Refined `1074` interpretation

After comparing `1073 / 1074 / 1075`, the current best model for `1074` is:

- `3025`
  - likely an older reuse of `Mail_Text_Ranking_1074`
- `3470` and `3570`
  - more likely the genuinely relevant late-era mail schedule rows for the `1074` late-family period

This is not yet absolute proof, but it is now better supported than the earlier "keep all three indefinitely" conservative reading.

### Updated practical takeaway

For a strict late-era `1074` reconstruction attempt, the current best priority order is:

1. definitely keep:
   - `3.lvst` row `1074`
   - `5.lvst` row `1993`
   - `8.lvst` row `1074 / 1074`
   - `0.act` `RankEvent1074` text set
2. in `0.lvst`, prioritize late rows:
   - `3470`
   - `3570`
3. treat the early row as lower-confidence / possibly legacy:
   - `3025`

That is the strongest current reduction of the `1074` minimum set without over-claiming certainty.

## `1074 / 1075` as a Shared Late Challenge Batch

Further comparison of the `5.lvst` neighborhood around rows `1992 / 1993` now strongly supports treating `1074` and `1075` as part of the same late challenge batch.

### `1992` and `1993` are adjacent peer rows

Observed rows:

- row `1992`
  - `0xF7740E1D = 1075`
  - `Challenge_Title_Sp_2154`
  - `Challenge_Msg_Sp_2154`
- row `1993`
  - `0xF7740E1D = 1074`
  - `Challenge_Title_Sp_2155`
  - `Challenge_Msg_Sp_2155`

Shared properties:

- both are root rows:
  - `0xE4FF913B = -1`
- same date window:
  - `2017-12-26 22:13:20`
  - to `2018-01-15 21:05:59`
- same `0x1297FABB = 127`
- same `0xABC16DF2 = 2`
- same `0x75CA4FC9 = 3`
- same `0xDE83BF5C = 257`
- same `0xD4FF61C1 = 1`
- same `0xD9BC4718 = 10000`
- same `0xE5B9FE19 = 0xF09AF8CC`

The main differences are exactly the kind expected for neighboring challenge variants:

- event id:
  - `1075` vs `1074`
- challenge title/message pair:
  - `2154` vs `2155`
- compact parameter fields:
  - `0x0D6BDED7`
  - `0x7A3A1AD3`
  - `0x0028F80E`
  - `0x298D0A45`
  - `0x37E12563`
  - `0xDE439831`

### `2154 / 2155` are consecutive text entries

In `0x58cf00c0\0\0.act`:

- `Challenge_Title_Sp_2154`
  - hash `0xEB659C28`
  - text index `800`
- `Challenge_Msg_Sp_2154`
  - hash `0x3545A254`
  - text index `801`
- `Challenge_Title_Sp_2155`
  - hash `0xEFA4819F`
  - text index `802`
- `Challenge_Msg_Sp_2155`
  - hash `0x3184BFE3`
  - text index `803`

This is strong structural evidence that:

- `2154` and `2155` were authored as a contiguous pair
- not as unrelated text labels that happened to land near each other

### The surrounding `1990..1998` rows reinforce the batch interpretation

Rows `1990..1998` contain several nearby challenge definitions sharing very similar layout and date windows.

Important observations:

- `1990..1993` all use the same:
  - `2017-12-26` to `2018-01-15` family window
- `1994..1995` shift to:
  - `2017-12-31` to `2018-01-15`
- `1996` extends to:
  - `2018-03-31`
- `1997..1998` use:
  - `2017-12-31` to `2018-01-31`

So `1992 / 1993` are not isolated anomalies.

They sit inside a compact late-era cluster of related challenge rows.

### Updated interpretation of `1074`

At this point the best current model is:

- `1074` and `1075` form a paired late challenge batch
- `1993` is the `1074` side of that pair
- `1992` is the `1075` side of that pair
- `2154 / 2155` are the corresponding paired text entries

This makes the `5.lvst` row `1993` one of the strongest anchors in the whole `1074` reconstruction chain.

## Updated Lowest-Confidence vs Highest-Confidence `1074` Assets

### Highest-confidence anchors

These now look like the strongest must-keep pieces for a late `1074` reconstruction:

- `0x58cf00c0\0\0.act`
  - `ShortName_RankEvent1074`
  - `LongName_RankEvent1074`
  - `Reward_RankEvent1074`
  - `Mail_Text_Ranking_1074`
  - `Challenge_Title_Sp_2155`
  - `Challenge_Msg_Sp_2155`
- `0x3f20632f\3.lvst`
  - row keyed by `1074`
- `0x3f20632f\5.lvst`
  - row `1993`
- `0x3f20632f\8.lvst`
  - row `1074 / 1074`
- `0x3f20632f\0.lvst`
  - rows `3470` and `3570`

### Lower-confidence / possibly legacy-support pieces

These now look less central:

- `0x3f20632f\0.lvst`
  - row `3025`

Current best interpretation:

- `3025` is more likely an older reuse row for `Mail_Text_Ranking_1074`
- `3470 / 3570` are more likely the late-era rows that actually matter for the final live-service period

## Late-Era Replay Pattern Hypothesis

The late-game data now shows a pattern that fits the user's reminder well:

- the final service period appears to reuse or replay earlier ranking/event families
- but it does so through new late-era challenge and mail schedules rather than by only preserving the original old rows

### Late challenge batch: `1990..1998`

The rows:

- `1990` through `1998`

form a compact late-era challenge batch built from:

- `Challenge_Title_Sp_2152..2160`
- `Challenge_Msg_Sp_2152..2160`

Observed row/event pairing:

- `1990 -> 1056 -> 2152`
- `1991 -> 1039 -> 2153`
- `1992 -> 1075 -> 2154`
- `1993 -> 1074 -> 2155`
- `1994 -> 1124 -> 2156`
- `1995 -> 1124 -> 2157`
- `1996 -> 1110 -> 2158`
- `1997 -> 1086 -> 2159`
- `1998 -> 1086 -> 2160`

Important timing pattern:

- `1990..1993`
  - `2017-12-26` to `2018-01-15`
- `1994..1995`
  - `2017-12-31` to `2018-01-15`
- `1996`
  - `2017-12-26` to `2018-03-31`
- `1997..1998`
  - `2017-12-31` to `2018-01-31`

This strongly suggests a real late-service batch rather than isolated leftovers.

### Late mail schedule pattern: `1073..1077 / 2073..2077`

In `0.lvst`, the late rows for these ranking-mail families cluster heavily in:

- `2017-09` through `2018-03`

Representative late rows:

- `1077`
  - `3410`, `3510`, `3600`
- `1076`
  - `3430`, `3530`
- `1075`
  - `3450`, `3550`
- `1074`
  - `3470`, `3570`
- `1073`
  - `3490`, `3580`
- `2077`
  - `3420`, `3520`
- `2076`
  - `3440`, `3540`
- `2075`
  - `3460`, `3560`
- `2074`
  - `3480`, `3575`
- `2073`
  - `3400`, `3500`, `3590`

This late clustering is much stronger evidence of live reuse/replay than the much older rows:

- `10`
- `20`
- `1173`
- `1285`
- `3005`
- `3015`
- `3025`
- `3160`
- `3230`

### Best current interpretation

The data now fits this model best:

1. old ranking/event families such as:
   - `1073`
   - `1074`
   - `1075`
   - `1076`
   - `1077`
   - and their `207x` counterparts
   remained addressable as reusable family ids
2. the late game created new live-service schedules around them:
   - new challenge rows in the `1990..1998` area
   - new ranking-mail rows in the `34xx..36xx` area
3. therefore the final service period likely did include replay/revival behavior for earlier activity families

### Practical implication for reconstruction

If the goal is to revive a late-period event like `1074`, the safest current assumption is:

- prioritize the late rows that sit inside the replay-era clusters
- do not start from the oldest `0.lvst` rows just because they share the same ranking-mail label

For `1074`, that means the late-era core is still best modeled as:

- `5.lvst`
  - row `1993`
- `0.lvst`
  - rows `3470`
  - `3570`

with:

- row `3025`
  - now looking more like an older historical reuse row than the primary late-era row

## `0xe82647a1` `1069 / 1071` Linkage Update

Focused comparison across:

- `E:\Games\Emulator\ACI\TSS\Unpack\NPWR04428_00-1`
- `E:\Games\Emulator\ACI\TSS\Unpack\NPWR04428_00-3`
- `E:\Games\Emulator\ACI\TSS\Unpack\NPWR04428_00-5`
- `E:\Games\Emulator\ACI\TSS\Unpack\NPWR04428_00-7`
- `E:\Games\Emulator\ACI\TSS\Unpack\NPWR04428_00-9`
- `E:\Games\Emulator\ACI\TSS\Unpack\NPWR04428_00-11`

shows the same stable `1069 / 1071` pattern in every full branch inspected.

### Confirmed `10.lvst` definition rows

In `0xe82647a1\10.lvst`, the late rows around `1069..1073` form a clean contiguous definition block:

- row `1068`
  - `nicknameId = 1069`
  - `itemId = 33555501`
  - `sort = 1069`
- row `1069`
  - `nicknameId = 1070`
  - `itemId = 33555502`
  - `sort = 1070`
- row `1070`
  - `nicknameId = 1071`
  - `itemId = 33555503`
  - `sort = 1071`
- row `1071`
  - `nicknameId = 1072`
  - `itemId = 33555504`
  - `sort = 1072`

Shared row traits:

- `type = 2`
- `status = 0`
- `category = 0`
- `specialEffect = 0`
- `paramInt = 0`
- `paramFloat = 0`
- `unlockType = 0`
- `unlockParamHash = 0x18197078`
- `unlockParamInt = 0`

Current best interpretation:

- `10.lvst` is not storing concrete event instances here
- this row band behaves more like an indexed definition/catalog layer that later tables reference by id

### Confirmed `8.lvst` mission-to-family pairing

In all inspected complete branches, `0xe82647a1\8.lvst` contains the same two important rows:

- row `88`
  - `MasterMapName = ms06`
  - `MissionName = micw22`
  - `MissionUniqueName = micw22e`
  - `Sort = 1069`
  - `0x148BB33F = 2015120404`
  - `0x949E5BB9 = 0x18197078`
- row `90`
  - `MasterMapName = ms08`
  - `MissionName = micw23`
  - `MissionUniqueName = micw23b`
  - `Sort = 1071`
  - `0x148BB33F = 2015120402`
  - `0x949E5BB9 = 0xCFD2EF71`

This is now the clearest compact pairing discovered for these ids:

- `1069` is bundled with the `2015120404` side of the `micw22 / ms06` family
- `1071` is bundled with the `2015120402` side of the `micw23 / ms08` family

Important implication:

- `1069 / 1071` are not floating text-only ids
- they participate in mission/event bundle tables inside `DPL_INFORMATION`

### `0x148BB33F` behaves like an owner/event-family field

Earlier scans already showed repeated `2015120402` / `2015120404` hits in `8.lvst`.

The targeted `1069 / 1071` rows strengthen that reading:

- row `88` uses `2015120404`
- row `90` uses `2015120402`

Current best interpretation:

- `0x148BB33F` is very likely an owner/event-family id field, or something extremely close to that role

### Confirmed `7.lvst` companion rows

`0xe82647a1\7.lvst` also carries one row for each id:

- row `283`
  - `0x2A58F9BC = 1069`
  - `0x5446ECC6 = 2904`
  - `0xDC643246 = 0xDE0E69EF`
  - `0x48C259DD = 4`
  - `0x1A8D8BDC = 4`
  - `0xF7740E1D = 2`
- row `36`
  - `0x2A58F9BC = 1071`
  - `0x5446ECC6 = 407`
  - `0xDC643246 = 0x906B9636`
  - `0x48C259DD = 7`
  - `0x1A8D8BDC = 5`
  - `0xF7740E1D = 2`

The exact semantics of these columns are still unresolved, but this table is clearly another consumer of the same `1069 / 1071` family ids.

### `AircraftId_RankEvent1069 / 1071` are still tokenized aliases

In `0x58cf00c0\0\0.act`:

- `AircraftId_RankEvent1069`
  - hash `0x30CE9E5C`
  - code units `E020 0001 5628 562E`
- `AircraftId_RankEvent1071`
  - hash `0xC4DFB238`
  - code units `E020 0001 5628 562E`

So both ids still collapse to the exact same short token payload.

This remains strong evidence that these are not direct serialized aircraft-name strings, but indirections into some runtime token-resolution path.

### `0xe82647a1\2\*.lvst` is another downstream consumer

Global scans for `1069 / 1071` show:

- `1069` appears in:
  - `0xe82647a1\2\54.lvst`
  - `0xe82647a1\2\55.lvst`
  - `0xe82647a1\2\57.lvst`
  - `0xe82647a1\2\58.lvst`
  - `0xe82647a1\2\60.lvst`
  - `0xe82647a1\2\61.lvst`
  - `0xe82647a1\2\136.lvst`
  - `0xe82647a1\2\137.lvst`
  - `0xe82647a1\2\165.lvst`
  - `0xe82647a1\2\170.lvst`
  - `0xe82647a1\2\187.lvst`
- each hit is in column `0x95B34A9E`

Observed behavior:

- these child tables all share the same `55`-column layout
- the rows carrying `1069` also contain large bundles of:
  - float parameters
  - dimension/count-like integers
  - several hash slots
  - one recurring `0x18197078`

Current best interpretation:

- `0xe82647a1\2\*.lvst` looks much more like a parameter/preset layer than a pure text table
- `1069` is therefore almost certainly feeding some gameplay/runtime preset chain, not only UI naming

### Important negative result

Direct ACT scans across:

- TSS unpack trees
- FullGame ACT dumps

did not resolve these hashes as ordinary plaintext labels:

- `0x906B9636`
- `0xDE0E69EF`
- `0xCFD2EF71`
- `0x18197078`

So the current best model is:

- `1069 / 1071` live inside a deeper runtime indirection path
- parts of that path are table-driven in `0xe82647a1`
- but the final human-readable name/aircraft restriction data is not stored here as a simple normal ACT string

### Additional caution: some nearby `8.lvst` hashes are forecast text, not event titles

Two nearby `8.lvst` hashes were confirmed in FullGame ACT resources:

- `0xE4A797D9 = IGE_Forecast_1`
- `0x0AB8F47B = IGE_Forecast_17`

This matters because it shows at least some hash columns in `8.lvst` are mission-side forecast / briefing text hooks, not activity titles.

So `8.lvst` should currently be modeled as a mixed mission bundle table rather than a dedicated event-name table.
