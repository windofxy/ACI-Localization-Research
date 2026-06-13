# ACT / UI Font Chain Notes

These notes track the current reverse-engineering state for how localized
`ACEText` / `.act` content reaches concrete UI font resources in Ace Combat
Infinity.

## Current Strongest Model

- `.act` stores localized string content.
- Lua scripts bind ACT keys into UI text slots such as `dt_001`, `dt_002`,
  `dt_003`.
- UI-side `.file` resources with `LMB` magic define those text slots and also
  embed human-readable font family names such as:
  - `Futura MdCn BT`
  - `A-OTF Shin Go Pr5 R`
- `.uifont` resources provide the actual bitmap-font blocks used by the game,
  for example:
  - `Futura_MdCn_BT20`
  - `Futura_MdCn_BT26`
  - `Futura_MdCn_BT28`
  - `A_OTF_Shin_Go_Pr5_R16`
  - `A_OTF_Shin_Go_Pr5_R20`

So the current best end-to-end chain is:

`ACT text -> Lua text binding -> UI text slot in LMB -> font family in LMB -> concrete glyph block in UIFONT`

What is still missing is the last exact mapping step:

- how an `LMB` text object that says `Futura MdCn BT` resolves to one concrete
  block such as `Futura_MdCn_BT20`, `BT26`, or `BT28`
- and likewise how `A-OTF Shin Go Pr5 R` resolves to `R16` or `R20`

## What Was Ruled Out

### ACT does not seem to choose the font block directly

Searches over the ACT-side package found the expected sibling font chain:

- `0xfcc2ac23/0/0.act`
- `0xfcc2ac23/0/1/0.uifont`
- `0xfcc2ac23/0/1/1/0.uitx`
- `0xfcc2ac23/0/1/1/1/0/0.nut`
- `0xfcc2ac23/0/1/1/1/0/1.nut`

But no evidence was found that the ACT payload itself stores explicit block
names like `Futura_MdCn_BT26` or `A_OTF_Shin_Go_Pr5_R20`.

### UI2D `.ui` resources are not the text-style carrier we wanted

Example checked:

- `0x375ba2dc/0/152/0.ui`

This resource parses as `UI2D` and appears to contain only:

- `type=1` texture layers
- `type=2` transition layers

No plain-text hits were found in that file for:

- `dt_001`
- `ButtonMessage`
- `SystemChainText`
- `Futura_MdCn_BT26`
- `A_OTF_Shin_Go_Pr5_R20`

So this `.ui` file looks like image/transition data, not the text-style layer.

### `.lar` is probably not the real text-style body

The `.lar` files sampled under `0x375ba2dc/0/119..151,159` are all tiny
24-byte records. Their current strongest read is a thin layout/reference header,
not a full text-definition payload.

Typical structure seen so far:

- magic `LAR `
- one hash-like `u32`
- width `0x64`
- height `0x64`
- constant/flag `0x00000001`
- final field either:
  - `0x00000002` when a sibling `uitx/nut` chain exists
  - `0xFFFFFFFF` when it does not

That does not look like the main place where font family or text object
definitions live.

## Positive Evidence for LMB / `.file`

The strongest current evidence comes from the `LMB`-magic `.file` resources in
`0x375ba2dc`.

### Text-slot names are present in `.file`

Examples:

- `dt_001`
- `dt_002`
- `dt_003`
- `dt_014`

These appear directly in many UI `.file` resources, for example:

- `0x375ba2dc/0/120/1.file`
- `0x375ba2dc/0/124/1.file`
- `0x375ba2dc/0/150/1.file`
- `0x375ba2dc/0/151/1.file`
- `0x375ba2dc/0/159/1.file`

### Font family names are present in `.file`

Examples found directly in `LMB` resources:

- `Futura MdCn BT`
- `A-OTF Shin Go Pr5 R`

Representative samples:

- `0x375ba2dc/0/120/1.file` contains both families
- `0x375ba2dc/0/124/1.file` contains only `A-OTF Shin Go Pr5 R`
- `0x375ba2dc/0/142/1.file` contains only `Futura MdCn BT`
- `0x375ba2dc/0/150/1.file` contains both families
- `0x375ba2dc/0/151/1.file` contains only `Futura MdCn BT`
- `0x375ba2dc/0/159/1.file` contains only `Futura MdCn BT`

This is the first strong direct evidence that the UI resource itself, not the
ACT, is carrying text-family information.

### The string area is length-prefixed

Around the font-family strings, the `.file` data uses a simple big-endian
length-prefixed representation:

- `00 00 00 13` -> `A-OTF Shin Go Pr5 R` (19 bytes)
- `00 00 00 0E` -> `Futura MdCn BT` (14 bytes)
- `00 00 00 04` -> `this`
- `00 00 00 0C` -> `onEnterFrame`

This strongly suggests the visible strings in `LMB` belong to a formal string
table or string-serialized object area, not random embedded debug text.

## UIFont Side Correlation

The ACT-side shared text package already gives a matching family set:

- `0xfcc2ac23/0/1/0.uifont`
  - `Futura_MdCn_BT20`
  - `Futura_MdCn_BT26`
  - `Futura_MdCn_BT28`
  - `A_OTF_Shin_Go_Pr5_R16`
  - `A_OTF_Shin_Go_Pr5_R20`

The `UI_MENU` package also contains local UIFont subsets:

- `0x375ba2dc/0/153/1/0.uifont`
  - `Futura_MdCn_BT20`
  - `logo`
- `0x375ba2dc/0/154/0.uifont`
  - `A_OTF_Shin_Go_Pr5_R30_radio`
  - `Futura_MdCn_BT28`
- `0x375ba2dc/0/161/0.uifont`
  - `A_OTF_Shin_Go_Pr5_R16`
  - `Futura_MdCn_BT20`
  - `A_OTF_Shin_Go_Pr5_R20`
  - `Futura_MdCn_BT28`
  - `Futura_MdCn_BT26`

This confirms that some UI packages carry both:

- a UI definition side (`.file`, `.lar`, `.ui`)
- and a local font package side (`.uifont`, `.uitx`, `.nut`)

## Package Layout Observations

Within `0x375ba2dc/0`:

- `0..118`, `156..172` are mainly `.file + .lua`
- `119..151`, `159` are mainly `.lar + .file`, with some of them also carrying
  `uitx/nut`
- `152` is `UI2D` (`0.ui`)
- `153`, `154`, `161` carry local `.uifont` chains

So `0x375ba2dc` is not just an image package. It is a mixed UI resource package
that includes scripts, UI text-bearing `.file` resources, and local font sets.

## `0xe1a4891d/10` Local UI Tree

The `0xe1a4891d/10` package is now known to contain a second, much richer local
UI subtree beyond:

- `0/0.ui`
- `1.act`
- `2/0.uifont`

It also contains `23..32`, each shaped as a local `LAR/LMB` page subtree:

- `23`, `25`, `26`, `30` also carry local `2/...uitx/nut` atlas chains
- `24`, `27`, `28`, `29`, `31`, `32` do not

Current coarse inventory:

- `23`
  - `lar hash = 0x1AD18925`
  - `child 2 atlas = yes`
  - `families = Futura MdCn BT + A-OTF Shin Go Pr5 R`
- `24`
  - `lar hash = 0x7B3C1A35`
  - `child 2 atlas = no`
  - `families = none`
- `25`
  - `lar hash = 0xCD5E59A5`
  - `child 2 atlas = yes`
  - `families = A-OTF Shin Go Pr5 R`
- `26`
  - `lar hash = 0x4E4012E1`
  - `child 2 atlas = yes`
  - `families = Futura MdCn BT + A-OTF Shin Go Pr5 R`
- `27`
  - `lar hash = 0x6BB6B1E3`
  - `child 2 atlas = no`
  - `families = Futura MdCn BT + A-OTF Shin Go Pr5 R`
- `28`
  - `lar hash = 0x82868E01`
  - `child 2 atlas = no`
  - `families = A-OTF Shin Go Pr5 R`
- `29`
  - `lar hash = 0xF93DE4D8`
  - `child 2 atlas = no`
  - `families = A-OTF Shin Go Pr5 R`
- `30`
  - `lar hash = 0x8C5E35CC`
  - `child 2 atlas = yes`
  - `families = Futura MdCn BT + A-OTF Shin Go Pr5 R`
- `31`
  - `lar hash = 0x0439547B`
  - `child 2 atlas = no`
  - `families = A-OTF Shin Go Pr5 R`
- `32`
  - `lar hash = 0x6792F22D`
  - `child 2 atlas = no`
  - `families = Futura MdCn BT + A-OTF Shin Go Pr5 R`

This matters because the `0.ui` bank-2 anomaly may be routing into this local
page subtree namespace instead of choosing only between the shared common font
package and the local `2/0.uifont`.

## Exact Shared-Subtree Reuse

The strongest concrete reuse result so far is:

- `0xdec73b58/0/9`
- `0xe1a4891d/10/23`

These two subtrees are byte-identical for the actual resource payloads:

- `0.lar`
- `1.file`
- `2/0.uitx`
- `2/1/0/0.nut`
- `2/1/0/1.nut`

Only the exported `.metadata.json` files differ, which is expected because they
encode extraction-context details such as offsets and parent item indices.

So at least one `0xe1a4891d/10` local page subtree is not merely similar to the
shared common UI package. It is a full embedded copy of the same page resource.

That strengthens two working ideas:

1. the game reuses complete UI page subtrees across packages, not only font
   families or atlas slices
2. the unresolved `0.ui` routing fields may select among local/shared page
   subtrees before font resolution happens

## Global Duplicate Map for `0xe1a4891d/10/23..32`

Full-game SHA-1 deduplication over all `LMB` `1.file` resources shows that
almost the entire `23..32` local page set is reused from other packages as
byte-identical payloads:

- `23/1.file`
  - exact match: `0xdec73b58/0/9/1.file`
- `24/1.file`
  - exact match: `0x375ba2dc/0/121/1.file`
- `25/1.file`
  - exact match: `0x375ba2dc/0/124/1.file`
- `26/1.file`
  - exact match: `0x375ba2dc/0/127/1.file`
- `27/1.file`
  - no other exact match found in the current full-game dump
- `28/1.file`
  - exact match: `0x375ba2dc/0/138/1.file`
- `29/1.file`
  - exact match: `0x375ba2dc/0/147/1.file`
- `30/1.file`
  - exact match: `0x375ba2dc/0/148/1.file`
- `31/1.file`
  - exact match: `0x375ba2dc/0/149/1.file`
- `32/1.file`
  - exact match: `0x375ba2dc/0/150/1.file`

So the `0xe1a4891d/10` local page set is not an isolated design. It is largely
composed of embedded copies of page resources that also exist in:

- the shared common UI package `0xdec73b58`
- the menu/UI package `0x375ba2dc`

For the following pairs, the match is stronger than just `1.file`: the entire
non-metadata subtree is byte-identical, including `0.lar` and any local
`uitx/nut` child chain when present:

- `0xe1a4891d/10/24` == `0x375ba2dc/0/121`
- `0xe1a4891d/10/25` == `0x375ba2dc/0/124`
- `0xe1a4891d/10/26` == `0x375ba2dc/0/127`
- `0xe1a4891d/10/28` == `0x375ba2dc/0/138`
- `0xe1a4891d/10/29` == `0x375ba2dc/0/147`
- `0xe1a4891d/10/30` == `0x375ba2dc/0/148`
- `0xe1a4891d/10/31` == `0x375ba2dc/0/149`
- `0xe1a4891d/10/32` == `0x375ba2dc/0/150`

This sharply narrows the problem space:

- `0.ui` is probably routing among already-known reusable page templates
- the unresolved bank-2 path may therefore be page-template selection, not a
  hidden text-string or glyph-specific namespace

## Unique Local Area-Select Page

`0xe1a4891d/10/27` is currently the only local page subtree in that package
that does not have an exact duplicate elsewhere in the extracted full-game dump.

Its `LMB` page is also semantically unique. Across all scanned `LMB` `1.file`
resources, the following object/type names were found only in:

- `0xe1a4891d/10/27/1.file`

Unique strings:

- `box_Areamap`
- `type_respawn_coop`
- `type_respawn_deathmatch`
- `type_freeflight`
- `type_campaign`

The subtree shape is:

- `0xe1a4891d/10/27/0.lar`
  - hash `0x6BB6B1E3`
  - final field `-1`
- `0xe1a4891d/10/27/1.file`
  - dual-family `LMB`
  - no local `child 2` atlas subtree

Negative result:

- `0x6BB6B1E3` does not appear directly in:
  - `0xe1a4891d/10/0/0.ui`
  - `0xdec73b58/0/1.afs`
  - `0xdec73b58/0/2.file`

So there is still no evidence that the current `UI2D -> AFS/ATS` routing fields
store this page hash directly.

## Stronger Lua -> LMB Bridge

The current best package-internal bridge for the unique area-select page is now
inside `0xe1a4891d/10` itself.

### `0xe1a4891d/10/11/1.lua`

This Lua resource is unique by SHA-1 in the current dump and contains:

- `AREA_SELECT`
- `_returnScript`
- `freeFlightMissionSelect`
- `box_Areamap`
- `dt_001`
- `dt_002`

It also contains free-flight menu context such as:

- `g_menuFreeFlightItemList`
- `MenuItem_Pause_015`
- `MenuDesc_Pause_015`
- `DlgMsg_Pause_008`

### `0xe1a4891d/10/27/1.file`

This is the only `LMB` page in the whole dump that contains:

- `box_Areamap`
- `dt_001`
- `dt_002`
- the free-flight / respawn type names listed above

So we now have strong direct evidence for a tighter chain:

`Lua script in 10/11 -> object names such as box_Areamap / dt_001 / dt_002 -> concrete LMB page 10/27`

This is materially stronger than the earlier family-only correlation, because it
connects one specific script subtree to one specific page subtree.

## Cross-Package Script Name Link

The script name `freeFlightMissionSelect` is currently visible in exactly two
Lua resources checked so far:

- `0xe1a4891d/10/11/1.lua`
- `0x375ba2dc/0/43/1.lua`

In `0x375ba2dc/0/43/1.lua`, the surrounding strings include:

- `FREEFLIGHT`
- `MenuItem_Main_028`
- `MenuDesc_Main_028`
- `freeFlightMissionSelect`

In `0xe1a4891d/10/11/1.lua`, the surrounding strings include:

- `AREA_SELECT`
- `_returnScript`
- `freeFlightMissionSelect`

Current best reading:

- `0x375ba2dc` likely exposes or launches the free-flight mission-select flow
- `0xe1a4891d/10/11` is a deeper local script in that flow
- `0xe1a4891d/10/27` is the corresponding unique local area-select page

## Local Lua Cluster vs Local Page Cluster

The `0xe1a4891d/10` package also has a strong split on the Lua side.

### Reused Lua subtrees

The following `1.lua` resources are byte-identical copies of scripts already
present in `0x375ba2dc/0`:

- `10/3  == 0x375ba2dc/0/1`
- `10/4  == 0x375ba2dc/0/2`
- `10/5  == 0x375ba2dc/0/5`
- `10/6  == 0x375ba2dc/0/9`
- `10/7  == 0x375ba2dc/0/13`
- `10/8  == 0x375ba2dc/0/31`
- `10/9  == 0x375ba2dc/0/32`
- `10/10 == 0x375ba2dc/0/66`
- `10/17 == 0x375ba2dc/0/102`
- `10/18 == 0x375ba2dc/0/86`
- `10/19 == 0x375ba2dc/0/87`
- `10/20 == 0x375ba2dc/0/88`
- `10/21 == 0x375ba2dc/0/89`
- `10/22 == 0x375ba2dc/0/90`

Their companion 12-byte `0.file` `LUA ` headers are also byte-identical across
those pairs.

### Unique local Lua subtrees

The following Lua resources are unique in the current full-game dump:

- `10/11`
  - header hash `0xA215C510`
- `10/12`
  - header hash `0xEC062E96`
- `10/13`
  - header hash `0x119596CA`
- `10/14`
  - header hash `0x504E87C5`
- `10/15`
  - header hash `0x11CE8EAC`
- `10/16`
  - header hash `0x36F8B88F`

This creates a clean local-only script cluster:

- `10/11..16`

which is a strong candidate for the script side of the same local-only UI flow
that contains page `10/27`.

## Strongest Script -> Page Object Matches Inside `0xe1a4891d/10`

Filtering both Lua and LMB resources down to concrete object-like strings such
as `box_*`, `dt_*`, `type_*`, `bar_*` gives several strong package-local
matches.

### `10/11 -> 10/27`

Shared object names:

- `box_Areamap`
- `dt_001`
- `dt_002`

This remains the strongest unique area-select bridge.

### `10/14 -> 10/27`

Shared object names:

- `box_extra`
- `bar_001`
- `dt_001`
- `dt_002`
- `dt_003`
- `dt_004`

This suggests `10/14` may be another local script in the same page flow, likely
touching the same `10/27` page but a different widget subset.

### `10/17 -> 10/23`

Shared object names:

- `box_alpha`
- `box_bravo`
- `box_icon`
- `box_item01..05`
- `box_ranking`
- `box_score`
- `box_strategicAttack`
- `box_txt_alpha`
- `box_txt_bravo`
- `box_txt_vs`
- `dt_001..dt_007`

This is a very strong object-level match and is consistent with both resources
also being duplicated from shared/common package content.

### `10/3 -> 10/28`

Shared object names:

- `box_fuel01`
- `box_fuel02`
- `dt_001..dt_014`

This is another strong object-level match, again consistent with a reused page
template plus reused script template.

## Current Best Local Flow Model

Within `0xe1a4891d/10`, the data now looks less like one monolithic custom UI
blob and more like:

- reused script/page templates copied from `0x375ba2dc` and `0xdec73b58`
- plus a local-only script cluster `10/11..16`
- plus at least one local-only page `10/27`

Current best reading for the free-flight branch is:

`0x375ba2dc/0/43/1.lua` (top-level launcher) -> `0xe1a4891d/10/11..16` (local script cluster) -> `0xe1a4891d/10/27` (local area-select page)

## Finer Split Inside the Local Script Cluster

The unique local Lua cluster `10/11..16` is not homogeneous. Current string
evidence suggests several different roles:

- `10/11`
  - pause-root / free-flight branch controller
  - contains:
    - `AREA_SELECT`
    - `freeFlightMissionSelect`
    - `box_Areamap`
    - `MenuHeader_Pause_001`
    - `MenuItem_Pause_015`
- `10/14`
  - respawn sub-menu controller
  - contains:
    - `RESPAWN`
    - `RESPAWN_FAST`
    - `MenuItem_Rsp_001`
    - `MenuItem_Rsp_007`
    - `MenuItem_Rsp_010`
    - `MenuItem_Rsp_011`
    - `DlgMsg_Rsp_001`
    - `DlgMsg_Rsp_002`
    - `box_extra`
    - `bar_001`
- `10/12`
  - controller-guide branch
  - contains:
    - `MenuHeader_Pause_003`
    - `aacomp_info_controller_guide`
- `10/15`
  - alternate pause-menu branch
  - contains:
    - `MenuHeader_Pause_002`
    - `MenuItem_Pause_010`
    - `DlgMsg_Pause_003`
    - `DlgMsg_Pause_005`
- `10/16`
  - online/start-online branch
  - contains:
    - `ctrl_StartOnlineMenu`
    - `aacomp_info_controller_guide`
- `10/13`
  - tutorial/guide dialog branch
  - contains:
    - `DlgMsg_SingleInGTutorial_001`
    - `DlgMsg_SingleInGTutorial_002`
    - `DlgMsg_SingleInGTutorial_003`

## Additional Page Correlation Notes

### `10/14 -> 10/27` is now very strong

Besides the earlier shared widget names, `10/14` contains explicit respawn
status text and gauge handling that line up well with the page structure seen in
`10/27/1.file`:

- `box_extra`
- `bar_001`
- `dt_001`
- `dt_002`
- `dt_004`
- respawn menu labels and dialog messages

So `10/27` no longer looks like only an area-select page. Current best reading
is that it is a broader free-flight / respawn state page whose visible widget
subset is controlled by different local scripts.

### `10/30` and `10/31` do not seem to belong to the local-only script cluster

`10/30/1.file` contains:

- `box_arrowL`
- `box_arrowR`
- `type_tree`

`10/31/1.file` contains:

- `type_2line`
- `type_4line`
- `trig_pagebreak`
- `param_pagebreak`

Negative result:

- none of those strings appear in the local unique scripts `10/11..16`

Additional clue:

- `param_pagebreak` was found in `0xdec73b58/0/6/1.lua`
- that Lua file is itself unique in the current dump

Current best reading:

- `10/30` and `10/31` may be driven by another script path outside the local
  free-flight-specific cluster
- the local unique cluster `10/11..16` is most clearly tied to `10/27`, and
  not yet to the tree/pagebreak pages

## Current Gaps

What remains unresolved:

1. the binary structure of `LMB`
2. how a specific `dt_xxx` entry is represented inside `LMB`
3. how a text object inside `LMB` points to one font family string
4. how that family then resolves to one exact `.uifont` block size/style
5. whether the resolution is:
   - explicit in `LMB`
   - implicit by resource package / type variant
   - or mediated by another hidden object table in the same file

## Early LMB Segment Model

Recent parsing of representative `LMB` files such as:

- `0x375ba2dc/0/124/1.file`
- `0x375ba2dc/0/142/1.file`
- `0x375ba2dc/0/150/1.file`
- `0x375ba2dc/0/151/1.file`
- `0x375ba2dc/0/159/1.file`

shows that the file is internally split into tagged sections. The currently
stable tags are:

- `F001`
- `F002`
- `F003`
- `F103`
- `F004`
- `F005`
- `F007`
- `F008`
- `F009`
- `F00A`
- `F00B`
- `F00C`
- `F00D`
- repeated `F022`
- repeated `F024`
- repeated `F105`

### `F001` currently looks like the string-table descriptor

`F001` starts at `0x40` in all checked samples.

The actual length-prefixed string table begins at `0x64` and continues until the
next `F002` marker.

For the checked samples above:

- `F001.u32[0] = ((f002_offset - 0x64) / 4) + 7`
- `F001.u32[1] = non_empty_string_count + 3`

So `F001` appears to describe the string-table region rather than glyph/font
content.

The second field also now has a stronger semantic read:

- `F001.u32[1]` matches the upper bound of a compact non-empty-string handle
  namespace
- handle assignment is:
  - `3` = first non-empty string
  - `4` = second non-empty string
  - and so on
- empty strings do not consume handle IDs

So later sections can reference strings in two different ways:

- raw string-table ordinal
- compact non-empty-string handle

That distinction explains several earlier false contradictions when trying to
map font-family references directly from small integers.

### String table shape

From `0x64` onward, the string area is a stream of:

- big-endian `u32` byte length
- raw ASCII bytes
- 4-byte alignment padding

This continues until the first `F002` marker.

Empty strings are serialized explicitly as zero-length entries.

### `F002` and `F103` share one structural pattern

Checked samples show:

- 12-byte section header:
  - tag
  - `u32 a`
  - `u32 n`
- payload size = `8 * n`
- `a = 2 * n + 1`

Examples:

- `0x375ba2dc/0/151/1.file`
  - `F002`: `a=317`, `n=158`
  - `F103`: `a=19`, `n=9`
- `0x375ba2dc/0/124/1.file`
  - `F002`: `a=17`, `n=8`
  - `F103`: `a=35`, `n=17`

The meaning of those 8-byte records is still unknown, but this section family
is now structurally constrained.

### `F004` and `F007` share another structural pattern

Checked samples show:

- 12-byte section header:
  - tag
  - `u32 a`
  - `u32 n`
- payload size = `16 * n`
- `a = 4 * n + 1`

Examples:

- `0x375ba2dc/0/151/1.file`
  - `F004`: `a=33`, `n=8`
  - `F007`: `a=33`, `n=8`
- `0x375ba2dc/0/124/1.file`
  - `F004`: `a=25`, `n=6`
  - `F007`: `a=61`, `n=15`

The 16-byte records often begin with float-like values and may be visual/object
parameter blocks.

### `F022` / `F024` look like object-group records

These two tags recur many times in the same file:

- `F022` has fixed total size `0x1C`
- the first visible `F024` header/body is `0x60`
- but the final `F024` before `F105` can continue into a much larger payload
  region until the next tagged section

Current strongest read:

- `F022` looks like a short group header / descriptor
- the first `0x60` bytes of each `F024` look like a display-object rectangle
  record
- the oversized trailing `F024` blocks are important because they contain
  nested data that still references string-table indices, including font-family
  strings

Evidence:

- `F00D + 0x08` matches the number of `F022` groups in checked samples:
  - `151`: `8`
  - `159`: `3`
  - `124`: `5`
- in samples such as `124` and `159`, one `F022` is followed by one or more
  `F024` records until the next `F022` or `F105`
- the first `0x60` bytes of `F024` contain four corner-like float tuples; for
  example in `0x375ba2dc/0/124/1.file`:
  - `332,230`
  - `332,194`
  - `372,194`
  - `372,230`
  which strongly looks like one rectangle
- oversized trailing `F024` blocks contain additional string-index hits for:
  - `dt_xxx`
  - font-family names such as `Futura MdCn BT` and `A-OTF Shin Go Pr5 R`
  - script names such as `this`, `_root`, `external`
- the oversized trailing `F024` payload is probably not a pure `u32` table:
  - it contains many words of the form `00010000`, `00020000`, `00170000`,
    `00180000`
  - across checked samples, these `hi16 != 0 && lo16 == 0` words are common:
    - `120`: `113`
    - `123`: `58`
    - `124`: `167`
    - `126`: `43`
    - `133`: `25`
    - `141`: `21`
    - `151`: `6`
    - `159`: `51`
  - and `lo16 != 0 && hi16 == 0` small words are even more common:
    - `120`: `806`
    - `123`: `255`
    - `124`: `645`
    - `126`: `258`
    - `133`: `134`
    - `141`: `119`
    - `151`: `96`
    - `159`: `225`

So the oversized `F024` tail likely mixes:

- normal `u32`
- float fields
- and a substantial amount of `u16/u16`-style packed data

That matters because some family-string hits sit right next to words like
`00170000` / `00180000`, which suggests the internal representation there is
halfword-oriented rather than a simple flat `u32` object list.

So `F022` plus the large trailing `F024` blocks remain the strongest current
candidates for where text-object metadata lives.

### Some oversized `F024` tails contain `0x34`-byte family-led subrecords

Looking only at samples whose oversized `F024` tail contains direct word-level
font-family hits, a useful new pattern appears:

- in at least some files, a candidate subrecord begins exactly where the family
  string index appears as a full `u32`
- a practical probe size is `0x34` bytes from that point

Representative samples:

- `0x375ba2dc/0/159/1.file`
  - family-led records at `big_F024 + 0x140`, `+0x620`, `+0x654`
- `0x375ba2dc/0/124/1.file`
  - family-led records at `big_F024 + 0x624`, `+0x6AC`, `+0xFA0`
- `0x375ba2dc/0/123/1.file`
  - family-led records at `big_F024 + 0x2D4`, `+0x4C8`, `+0x7FC`, `+0x800`
- `0x375ba2dc/0/126/1.file`
  - family-led records at `big_F024 + 0x308`, `+0x41C`, `+0x534`, `+0x56C`,
    `+0x6B8`
- `0x375ba2dc/0/120/1.file`
  - many such records, including paired `Futura` / `A-OTF` siblings

This is not universal:

- `0x375ba2dc/0/133/1.file`
  - no direct word-level or halfword-level family hits in the oversized
    `F024` tail
- `0x375ba2dc/0/141/1.file`
  - same result

So this looks like a real internal structure used by some `LMB` variants, not
yet a universal rule for every font-bearing file.

### Early family-led subrecord classes

Those `0x34` candidate records are not all the same, but some layouts recur
often enough to separate into rough classes.

#### Class A: sparse setup / binding-looking records

Examples:

- `123`: `big_F024 + 0x2D4`
- `126`: `big_F024 + 0x308`
- `120`: `big_F024 + 0x118`

Shared shape:

- `+0x00 = family string index`
- `+0x04 .. +0x14` are mostly zero or one-digit indices
- one field often appears as `0x00050000`, `0x00080000`, `0x00090000`
- trailing fields often contain small string indices

This class currently looks like a compact setup/binding record, but not yet a
decoded text-style record.

#### Class B: packed-halfword / state-looking records

Examples:

- `124`: `big_F024 + 0x624`
- `159`: `big_F024 + 0x620`
- `123`: `big_F024 + 0x4C8`, `+0x800`
- `126`: `big_F024 + 0x41C`, `+0x534`, `+0x56C`, `+0x6B8`

Shared shape:

- `+0x00 = family string index`
- somewhere very early in the record there is usually `0x00010000`
- another early field is often a small value shifted into the high halfword:
  - `0x00030000`
  - `0x00040000`
  - `0x00050000`
  - `0x00160000`
  - `0x00180000`
- another nearby field often has the form `0x8000000N`

This class is the strongest current evidence that the oversized `F024` tail is
using a packed halfword-oriented representation internally.

#### Class C: script-adjacent records

Examples:

- `124`: `big_F024 + 0x6AC`, `+0xFA0`
- `151`: `big_F024 + 0x94`

These records contain family at `+0x00`, but nearby fields decode to script
strings such as:

- `this`
- `onEnterFrame`
- `movie_clip`

So not every family-led record is a pure style/config record; some are likely
bridging text/font information with higher-level UI scripting state.

### Paired family-led sibling records appear in some multi-family files

Some samples contain near-duplicate records that differ mainly by which family
string index appears at the front.

Examples:

- `120`
  - `+0x7B0`: starts with `Futura MdCn BT`
  - `+0x7F8`: starts with `A-OTF Shin Go Pr5 R`
- `123`
  - `+0x7FC`: starts with `A-OTF Shin Go Pr5 R`
  - `+0x800`: starts with `Futura MdCn BT`

This suggests at least some `LMB` files store parallel sibling records for the
two available font families rather than one global family selector.

### `F00A` is a font-family inventory table in handle space

This section is now much better understood than earlier notes suggested.

The earlier contradiction came from mixing:

- raw string-table ordinals
- compact non-empty-string handles

Once the `F001` handle rule is applied, a broader scan over all font-bearing
`LMB` samples under `0x375ba2dc/0` shows that `F00A` consistently stores font
family references in handle space.

Representative matches:

- `120`
  - families:
    - raw indices `16`, `17`
    - handles `14`, `15`
  - `F00A` entries:
    - `14`, `15`
- `123`
  - families:
    - raw indices `23`, `24`
    - handles `21`, `22`
  - `F00A` entries:
    - `21`, `22`
- `124`
  - family:
    - raw index `24`
    - handle `24`
  - `F00A` entry:
    - `24`
- `126`
  - families:
    - raw indices `16`, `17`
    - handles `16`, `17`
  - `F00A` entries:
    - `16`, `17`
- `134`
  - families:
    - raw indices `127`, `128`
    - handles `121`, `122`
  - `F00A` entries:
    - `121`, `122`
- `150`
  - families:
    - raw indices `75`, `76`
    - handles `64`, `65`
  - `F00A` entries:
    - `64`, `65`

So `F00A` is not using raw string indices. It is using the compact handle
namespace defined by `F001`.

Its layout is also now more regular:

- single-family variant:
  - stable leading words:
    - `1, 0, 0x0A, 0x06, 1`
  - followed by one 5-word entry:
    - `[slot_index, 0, family_handle, 0, 0]`
- dual-family variant:
  - stable leading words:
    - `1, 0, 0x0A, 0x0B, 2`
  - followed by two 5-word entries:
    - `[0, 0, family_handle_0, 0, 0]`
    - `[1, 0, family_handle_1, 0, 0]`

Examples:

- `124`
  - `F00A = [1, 0, 0x0A, 0x06, 1, 0, 0, 24, 0, 0]`
- `126`
  - `F00A = [1, 0, 0x0A, 0x0B, 2, 0, 0, 16, 0, 0, 1, 0, 17, 0, 0]`
- `123`
  - `F00A = [1, 0, 0x0A, 0x0B, 2, 0, 0, 21, 0, 0, 1, 0, 22, 0, 0]`

What `F00A` still does not prove is the final per-text-object choice. The
current strongest read is:

- `F00A` enumerates which font families are available to this `LMB`
- but another layer still decides which `F022`/text object uses which family
  entry
- and the concrete `.uifont` block size mapping is still unresolved

### Pre-`F105` high-bit records are the best current family-usage candidates

Once the `F001` handle rule is applied, the most promising family-bearing
records are not in `F00A` itself but in the large pre-`F105` tail.

The current best candidates are the records whose first word has the high bit
set, for example:

- `123`
  - `0xDAC`: `8000000A ... 00000004 0000000C 00000015 ...`
  - `0xDE4`: `8000000B ... 00000004 0000000C 00000016 ...`
- `126`
  - `0xCCC`: `80000003 ... 00000004 0000000C 00000010 0000000C ...`
  - `0xDE0`: `80000002 ... 00000004 0000000C 00000013 00000010 ...`
  - `0xE18`: `80000003 ... 00000004 0000000C 00000014 00000011 ...`
  - `0xBB8`: `80000004 ... 00000027 00000007 00000011 ...`
- `159`
  - `0xF34`: `8000000C ... 00000004 0000000C 00000015 00000017 ...`
  - `0xF6C`: `8000000D ... 00000027 00000007 00000017 ...`

What is stable so far:

- family references in these records use `F001` handle space, not raw string
  ordinals
- the family handle most often lands in:
  - slot `7`
  - or slot `8`
- two recurring subshapes are already visible:
  - `800000?? ... 00000004 0000000C ...`
  - `800000?? ... 00000027 00000007 ...`

What is not solved yet:

- whether these records point directly to text styles, text fields, or some
  intermediate object/state layer
- why the family handle is sometimes in slot `7` and sometimes in slot `8`
- which neighboring slot, if any, is the real size/style selector that
  distinguishes:
  - `Futura_MdCn_BT20`
  - `Futura_MdCn_BT26`
  - `Futura_MdCn_BT28`
  - `A_OTF_Shin_Go_Pr5_R16`
  - `A_OTF_Shin_Go_Pr5_R20`

So the current best next target is no longer "`does `F00A` hold the family`?"
but rather:

- which pre-`F105` high-bit record class is the true per-style record
- and which adjacent field inside that class selects the concrete block size

### Some family-bearing high-bit records also carry style-name handles

A narrower pass over the same record family shows that at least some of these
records do not just mention a font family. They also carry a neighboring handle
that resolves cleanly to a style-like string.

Strongest current examples:

- `123`
  - `0xDAC`
    - `8000000A ... 00000015 0000000E ...`
    - handle `0x15` = `Futura MdCn BT`
    - handle `0x0E` = `type_normal`
  - `0xDE4`
    - `8000000B ... 00000016 0000000F ...`
    - handle `0x16` = `A-OTF Shin Go Pr5 R`
    - handle `0x0F` = `type_rate`
- `145`
  - `0xC30`
    - `8000000E ... 00000015 0000000F ...`
    - handle `0x15` = `Futura MdCn BT`
    - handle `0x0F` = `type_weapon`

These are the clearest current cases where a family-bearing pre-`F105` record
also carries a neighboring semantic label that looks more like a style name
than a geometry or state field.

This does not yet reveal the exact `.uifont` block size, but it does strengthen
the current model:

- `F00A` enumerates available font families
- some pre-`F105` high-bit records appear to bind:
  - a family handle
  - plus a style-name handle
- the remaining unknown is which field in that same record class, or in its
  immediate companion records, chooses the concrete block such as:
  - `Futura_MdCn_BT20`
  - `Futura_MdCn_BT26`
  - `Futura_MdCn_BT28`
  - `A_OTF_Shin_Go_Pr5_R16`
  - `A_OTF_Shin_Go_Pr5_R20`

### Generic handle ladders exist and should not be mistaken for family mapping

The tail also contains generic handle runs such as:

- `123`: `0x171C`
  - `0x15, 0, 1, 2, 0x16, 0, 1, 2, 0x17, 0, 1, 2 ...`
- `126`: `0x149C`
  - `0x10, 0, 1, 2, 0x11, 0, 1, 2, 0x12, 0, 1, 2 ...`
- `159`: `0x1348`
  - `0x17, 0, 1, 2, 0x18, 0, 1, 2, 0x19, 0, 1, 2 ...`

Those runs are important because they also include family handles, but they are
currently better explained as generic handle reference ladders than as the true
font selector.

### `F00D` appears to summarize the number of repeated object records

In the checked samples:

- `F00D + 0x08` matches the number of `F022` groups seen immediately afterward
  - `123`: `3`
  - `126`: `3`
  - `151`: `8`
  - `159`: `3`
  - `124`: `5`

This suggests `F00D` is a small section-level descriptor for the following
object list.

### `F00C` is probably not the font-family selector

`F00C` sometimes contains small index-like fields that can hit string-table
entries, but those hits are also not stable enough to identify it as the
font-selector block. It does carry shared display constants:

- `+0x24 = 60.0`
- `+0x28 = 1280.0`
- `+0x2C = 720.0`

So the strongest current read is that `F00C` is a global display/stage/layout
parameter block rather than the place where the font family is chosen.

### `F105` looks more like script / callback binding than font selection

The repeated `F105` sections were initially possible font candidates, but the
string-index evidence now points elsewhere.

Examples from checked samples:

- `0x375ba2dc/0/159/1.file`, large `F105` records reference string indices
  that decode to:
  - `this`
  - `_root`
  - `onEnterFrame`
  - `flash`
  - `external`
  - `ExternalInterface`
  - `addCallback`
- similar script-oriented string hits appear in `124`

That makes `F105` look more like ActionScript / callback / scene-binding data
than a font-style selector. It is still part of the same resource format, but
it is currently a lower-priority target for the font-resolution question.

### Local UIFONT subsets still give useful constraints

Although they have not yet closed the `LMB` mapping by themselves, the local
UIFont subsets inside `0x375ba2dc` remain useful outer constraints:

- `153` local UIFont contains:
  - `Futura_MdCn_BT20`
  - `logo`
- `154` local UIFont contains:
  - `A_OTF_Shin_Go_Pr5_R30_radio`
  - `Futura_MdCn_BT28`
- `161` local UIFont contains:
  - `A_OTF_Shin_Go_Pr5_R16`
  - `Futura_MdCn_BT20`
  - `A_OTF_Shin_Go_Pr5_R20`
  - `Futura_MdCn_BT28`
  - `Futura_MdCn_BT26`

So even before the exact `LMB` field mapping is solved, package-local UIFont
presence can still bound the set of concrete blocks a UI component is able to
resolve to at runtime.

### Shared UIFONT block line heights now match a style ladder inside `LMB`

Parsing the relevant shared/local UIFont files gives the following concrete
block metrics:

- `Futura_MdCn_BT20`
  - line height `25`
- `Futura_MdCn_BT26`
  - line height `32`
- `Futura_MdCn_BT28`
  - line height `34`
- `A_OTF_Shin_Go_Pr5_R16`
  - line height `22`
- `A_OTF_Shin_Go_Pr5_R20`
  - line height `26`
- `A_OTF_Shin_Go_Pr5_R30_radio`
  - line height `38`
- `HUD_12`
  - line height `14`
- `HUD_14`
  - line height `17`
- `HUD_18`
  - line height `22`
- `HUD_22`
  - line height `27`
- `logo`
  - line height `28`
- `Futura_MdCn_BT62`
  - line height `73`

New strong correlation:

- in `0x375ba2dc/0/124/1.file`, the oversized `F024` tail contains the
  repeated high-halfword sequence:
  - `14`
  - `17`
  - `22`
  - `25`
  - `26`
  - `27`
  - `28`
  - `32`
  - `34`
  - `38`
- serialized as:
  - `000E0000`
  - `00110000`
  - `00160000`
  - `00190000`
  - `001A0000`
  - `001B0000`
  - `001C0000`
  - `00200000`
  - `00220000`
  - `00260000`

This sequence appears twice in that one file:

- first run:
  - `+0x404`, `+0x4AC`, `+0x5C4`, `+0x66C`, `+0x6A4`, `+0x6DC`, `+0x714`,
    `+0x7F4`, `+0x864`, `+0x944`
- second run:
  - `+0xCC0`, `+0xD68`, `+0xE80`, `+0xF28`, `+0xF60`, `+0xF98`, `+0xFD0`,
    `+0x10B0`, `+0x1120`, `+0x1200`

Also, `0x375ba2dc/0/159/1.file` contains a smaller subset of the same ladder:

- `14`
- `17`
- `22`

at:

- `+0x470`
- `+0x518`
- `+0x630`

That earlier correlation is no longer safe to treat as established. A fuller
scan of the same runs shows that the field which seemed to produce a "font size
ladder" is often just part of a wider contiguous ordinal sequence inside the
record table. So the apparent match against some UIFont metrics may be a
coincidence caused by overlapping numeric ranges rather than a confirmed
font-size selector.

### The oversized `F024` tail now has a stable internal anchor

Recent re-scans of the final `F024 -> F105` region in:

- `0x375ba2dc/0/124/1.file`
- `0x375ba2dc/0/159/1.file`

show a much more stable local structure than the earlier ad-hoc windowing
suggested.

For these samples, the practical oversized-tail region is:

- `tail_start = last_f024_offset + last_f024_size`
- `tail_end = next_f105_offset`

which gives:

- `124`
  - `tail_start = 0x11FC`
  - `tail_end = 0x25D4`
  - `tail_len = 0x13D8`
- `159`
  - `tail_start = 0x098C`
  - `tail_end = 0x1050`
  - `tail_len = 0x06C4`

Inside that region:

- there is a short common preamble
- then a long run of fixed-stride records begins
- the strongest current anchor for those records is the repeated `u32` pair:
  - `00000004`
  - `0000000C`

Treating that pair as the start of a candidate record reveals a repeating block
with:

- record stride `0x38`
- a stable ordinal-like field at `record + 0x1C`

So a strong current local model is:

- the oversized `F024` tail contains one or more `0x38`-stride record tables
- each record begins with:
  - `00000004`
  - `0000000C`
- a record-local ordinal / selector-like field sits at:
  - `u32[7]`
  - or equivalently `record + 0x1C`

This is much firmer than the earlier "family-led `0x34` window" probe and gives
us a stable field position to compare across files.

### Concrete record table examples

In `124`, one important run begins at `tail + 0x358` and continues with stride
`0x38`. Representative records are:

- `tail + 0x390`
  - `00000004 0000000C 00000004 0000000E 00000000 00000000 00010000 000E0000 00000000 0000000C 00000005 00000004 00000000 00000000`
  - ordinal field `14`
- `tail + 0x438`
  - `00000004 0000000C 00000004 00000011 00000000 00000000 00010000 00110000 00000000 0000000F 00000005 00000004 00000000 00000000`
  - ordinal field `17`
- `tail + 0x550`
  - `00000004 0000000C 00000004 00000016 00000000 00000000 00010000 00160000 00000000 00000014 00000005 00000004 00000000 00000000`
  - ordinal field `22`
- `tail + 0x630`
  - `00000004 0000000C 00000004 0000001A 00000000 00000000 00010000 001A0000 00000000 00000018 00000005 00000004 00000000 00000000`
  - ordinal field `26`
  - note:
    - `u32[9] = 0x18`
    - in this file that is both:
      - numeric value `24`
      - and string index `24 = A-OTF Shin Go Pr5 R`
    - so this is not yet a safe confirmed family-field hit
- `tail + 0x668`
  - `00000004 0000000C 0000000A 0000001B 00000000 00000003 00010000 001B0000 00000000 80000002 00000006 00000007 00000000 00000000`
  - ordinal field `27`
- `tail + 0x8D0`
  - `00000004 0000000C 00000015 00000026 00000000 0000000E 00010000 00260000 00000000 8000000D 00000006 00000007 00000000 00000000`
  - ordinal field `38`

The same file contains a second later run beginning near `tail + 0x93C`, again
with the same `0x38` stride and the same ordinal / selector field at `+0x1C`.

In `159`, another clear run begins at `tail + 0x0EC` and the font-bearing
records include:

- `tail + 0x3FC`
  - `00000004 0000000C 0000000D 0000000F 00000000 00000007 00010000 000E0000 00000000 80000005 00000006 00000007 00000000 00000000`
  - ordinal field `14`
- `tail + 0x4A4`
  - `00000004 0000000C 00000010 00000012 00000000 0000000A 00010000 00110000 00000000 80000008 00000006 00000007 00000000 00000000`
  - ordinal field `17`
- `tail + 0x5BC`
  - `00000004 0000000C 00000015 00000017 00000000 0000000F 00010000 00160000 00000000 8000000D 00000006 00000007 00000000 00000000`
  - ordinal field `22`
  - `u32[3] = 0x17 = string index 23 = Futura MdCn BT`

### Important correction: the `+0x1C` field is often just a local ordinal

Full-run scans now show that the `record + 0x1C` field is commonly a contiguous
sequence tied to the current record run, not a sparse set of font-size-like
values.

Examples:

- `124`, run beginning at `tail + 0x358`
  - `u32[3] = 13..38`
  - `u32[7]>>16 = 13..38`
  - exact relation:
    - `u32[7]>>16 = u32[3]`
- `124`, later run beginning at `tail + 0x93C`
  - `u32[3] = 39..80`
  - `u32[7]>>16 = 0..41`
  - exact relation:
    - `u32[7]>>16 = u32[3] - 39`
- `159`, run beginning at `tail + 0x0EC`
  - `u32[3] = 1..23`
  - `u32[7]>>16 = 0..22`
  - exact relation:
    - `u32[7]>>16 = u32[3] - 1`
- `123`
  - multiple runs show the same behavior with different base offsets:
    - `u32[7]>>16 = u32[3] - 1`
    - `u32[7]>>16 = u32[3] - 8`
    - `u32[7]>>16 = u32[3] - 17`

So the safest current read is:

- `record + 0x1C` is a run-local ordinal / selector field
- it may still participate indirectly in text-style selection
- but it is not currently proven to be the concrete UIFont line-height metric

This means the earlier "UIFont metric ladder" interpretation should now be
treated as provisional at best.

### Important correction: many family hits inside the `0x38` runs are probably incidental

Another strong caution from the full-run scan is that many apparent "family
string hits" inside the `0x38`-stride records are likely just the record walk
passing through a contiguous range of string indices.

Examples:

- `124`, run beginning at `tail + 0x358`
  - `u32[3]` walks `13..38` contiguously
  - so the hit at `24 = A-OTF Shin Go Pr5 R` is part of that sweep
- `159`, run beginning at `tail + 0x0EC`
  - `u32[3]` walks `1..23` contiguously
  - so the hit at `23 = Futura MdCn BT` may likewise be just the end of the
    local string sweep
- `120` and `126`
  - several family hits occur at the edges of short contiguous string walks
  - these are not yet safe to treat as explicit font-selection records

So at the moment, a family hit inside a `0x38` record only proves:

- that this table can reference string-table indices

It does not yet prove:

- that the specific field is semantically "font family"

### Second correction: the current non-run "free hits" also look mostly generic

The more interesting family candidates were initially the word-level family hits
in the tail that do **not** sit inside the `0x38`-stride record spans.

Recurring contexts seen so far include:

- `... 00000027 00000007 <family_idx> 00000000 ...`
  - for example:
    - `123`, `tail + 0x27C`
    - `126`, `tail + 0x2B0`
    - `120`, `tail + 0x0C0`
    - `159`, `tail + 0x5FC`
- `... 00000001 00000002 <family_idx> 00000001 00000004 0000000C ...`
  - for example:
    - `120`, `tail + 0x758`
    - `120`, `tail + 0x7A0`

However, fuller scans now show that both of these patterns also occur broadly
with many non-family string indices.

#### The `00000027 00000007` pattern is generic

This pattern is not family-specific. In the checked samples it also targets:

- `dt_002`
- `dt_003`
- `selected`
- `type_rate`
- `Exit`
- `type_weapon`
- `this`
- `_root`
- `AAUtil_InputGuard`

Representative examples:

- `120`
  - `tail + 0x008 -> dt_002`
  - `tail + 0x04C -> selected`
  - `tail + 0x0B8 -> A-OTF Shin Go Pr5 R`
  - `tail + 0x2AC -> this`
- `123`
  - `tail + 0x0B8 -> type_rate`
  - `tail + 0x274 -> A-OTF Shin Go Pr5 R`
- `124`
  - `tail + 0x04C -> Exit`
  - `tail + 0x126C -> _root`
- `126`
  - `tail + 0x04C -> type_weapon`
  - `tail + 0x2A8 -> A-OTF Shin Go Pr5 R`
  - `tail + 0x540 -> AAUtil_InputGuard`
- `159`
  - `tail + 0x5F4 -> Futura MdCn BT`

So the safest read is that `00000027 00000007` is some generic string-reference
envelope rather than a font-family record.

#### The `00000001 00000002` pattern is also generic

The `00000001 00000002` family-looking hits turned out to be even more generic.
Large runs of this pattern enumerate long contiguous stretches of the string
table, including:

- `dt_xxx`
- state names like `Wait`, `In`, `Loop`, `Out`, `Exit`
- family strings
- script/callback strings such as `this`, `onEnterFrame`
- helper names such as `AAUtil_InputGuard`, `trig_select`, `param_select`

Representative examples:

- `120`
  - one long run walks `dt_001` through `_root`
  - the same run passes through:
    - `Futura MdCn BT`
    - `A-OTF Shin Go Pr5 R`
    - `this`
    - `onEnterFrame`
- `151`
  - similar runs enumerate:
    - `dt_001`
    - `type_jp`
    - `type_R`
    - `type_TM`
    - `Wait`, `In`, `Loop`, `Out`
- `124`, `126`, `159`
  - all show the same generic string-enumeration behavior

So this second non-run pattern is also not a strong current font-family
candidate by itself.

### Revised current status

At this point:

- contiguous family hits inside the `0x38` record runs look incidental
- the two strongest non-run free-hit patterns also look generic

So the current tail analysis does **not** yet isolate a clean, font-specific
family selector field.

What the tail *does* strongly prove is:

- it contains multiple different generic string-reference structures
- some of those structures are fixed-stride tables
- the tail is therefore structurally rich, but not yet solved at the semantic
  "font family selector" level

### New best next focus inside the same files

Since both the run hits and the current non-run hits are now mostly explained
as generic string referencing, the next best target is no longer "find another
string hit inside the tail".

The better next step is to decode how the small object headers chain into the
tail, especially:

- the repeated `F022` headers:
  - `F022, index, 0x16, ...`
- the small `F024` headers whose final words often point into:
  - another `F022`
  - another `F024`
  - or the `00000027 00000000` marker right before the tail body

In the checked samples:

- `123`
  - final small `F024` ends with:
    - `00000027 00000000`
- `124`
  - several small `F024` records daisy-chain through:
    - `F022 0`
    - `F022 1`
    - `F022 2`
    - `F022 4`
    - then finally `00000027 00000000`
- `126`
  - final small `F024` also ends with:
    - `00000027 00000000`
- `159`
  - final small `F024` also ends with:
    - `00000027 00000000`

That makes the `F022/F024` header chain a better current candidate for finding
the real semantic grouping of text objects than any isolated family string hit
inside the tail body.

## New Strong Result: the small `F022 / F024` chain is partly decoded

Recent passes over:

- `123`
- `124`
- `126`
- `159`

plus broader spot checks across `0x375ba2dc/0/*/1.file`, now support a much
clearer model for the small object chain that appears immediately before the
large tail.

### Small `F024` is a rectangle record

The common small `F024` body is now strongly read as a rectangle / quad record.

For the standard `0x16`-count form:

- `u32[2]`
  - local record id
- `u32[3]`
  - mode / flags field
  - common values seen:
    - `00000004`
    - `00410004`
- corner coordinates are stored as four `(x, y)` float pairs:
  - `(u32[5],  u32[6])`
  - `(u32[9],  u32[10])`
  - `(u32[13], u32[14])`
  - `(u32[17], u32[18])`

Representative examples:

- `123`, `0x878`
  - id `0`
  - `field3 = 00000004`
  - corners:
    - `(0, 10)`
    - `(0, 0)`
    - `(10, 0)`
    - `(10, 10)`
- `159`, `0x934`
  - id `2`
  - `field3 = 00000004`
  - corners:
    - `(0, 15)`
    - `(0, 0)`
    - `(15, 0)`
    - `(15, 15)`
- `124`, `0xC2C`
  - id `0`
  - `field3 = 00410004`
  - corners:
    - `(332, 230)`
    - `(332, 194)`
    - `(372, 194)`
    - `(372, 230)`

So the small `F024` records are no longer just abstract object blobs: they
carry concrete 2D bounds.

### `F022` is followed by an 8-byte node header before the first `F024`

Although the `F022` tag itself is only 5 words long:

- `F022`
- constant `5`
- one variable field
- zero
- one variable field

the actual layout before the first child `F024` includes an extra 8-byte node
header:

- `00000000`
- child_count

Then the first child begins:

- `F024`

So a practical local read is:

- `F022 core header`
- one 8-byte child-chain header
- one or more small child `F024` records

### The second word of the 8-byte node header is usually the child `F024` count

This field is now one of the strongest local semantics we have.

For most checked samples:

- `child_count = 1`

Examples:

- `123`
  - `F022(dt_002)` -> count `1` -> one child `F024 id 0`
  - `F022(dt_004)` -> count `1` -> one child `F024 id 1`
- `126`
  - `F022(dt_002)` -> count `1` -> one child `F024 id 0`
  - `F022(box_ac)` -> count `1` -> one child `F024 id 1`
- `159`
  - `F022(dt_002)` -> count `1` -> one child `F024 id 0`
  - `F022(dt_006)` -> count `1` -> one child `F024 id 1`

`124` gives the best multi-child confirmation:

- `F022(dt_007, field4=1)` -> node count `12`
  - followed by 12 child `F024` nodes
  - ids `0..11`
- `F022("", field4=4)` -> node count `2`
  - followed by 2 child `F024` nodes
  - ids `13, 14`

### Child `F024` nodes are also separated by 8-byte headers

For multi-child groups, the layout is not:

- `F024 + F024 + F024`

but:

- 8-byte node header
- `F024`
- 8-byte node header
- `F024`
- ...

In `124`:

- the first child after `F022(dt_007)` starts with:
  - `00000000 0000000C`
  - then `F024`
- subsequent children repeat:
  - `00020003 00000002`
  - then `F024`

In `124`, `F022("", field4=4)` shows the same pattern:

- first child:
  - `00000000 00000002`
  - then `F024 id 13`
- second child:
  - `00020003 00000002`
  - then `F024 id 14`

So the child list appears to have:

- a distinct first-node header
- then a repeated follow-on node header for additional children

The exact meaning of:

- `00000000`
- `00020003`
- `00000002`

is still unresolved, but the structural role is now much clearer.

### Current best read of `F022`

The `F022` payload itself is now best described as:

- `u32[1] = 5`
  - constant in all checked samples
- `u32[2]`
  - often decodes cleanly as a string-table index
  - examples:
    - `dt_002`
    - `dt_004`
    - `dt_007`
    - `box_ac`
    - `type_parts`
- `u32[3] = 0`
  - constant in all checked samples so far
- `u32[4]`
  - group / subtype-like value
  - often small:
    - `0`
    - `1`
    - `2`
    - `4`
    - `5`
    - `6`
    - `7`
  - exact semantics still unresolved

So the safest current read is:

- `F022` likely names or keys a UI object/group via a string index
- the trailing node header tells us how many small `F024` geometry records are
  attached to that group

### Strong negative result: `F022` is not the family-string layer

A broader scan over all `F022` records in `0x375ba2dc/0/*/1.file` found:

- no `F022` whose string index points directly to:
  - `Futura MdCn BT`
  - `A-OTF Shin Go Pr5 R`

Instead, the `F022` string indices point to things like:

- `dt_xxx`
- state names:
  - `Wait`
  - `In`
  - `Loop`
  - `Out`
  - `Exit`
- object/control names such as:
  - `box_ac`
  - `type_parts`
  - `AAUtil_InputGuard`

So the current evidence strongly suggests:

- `F022` belongs to the UI object/group naming layer
- not the font-family naming layer

That is an important narrowing result even though it is negative.

### Standard `0x16` small `F024` records already split into at least two practical classes

Among the normal `count=0x16` small `F024` bodies, the most useful practical
split so far is by the `mode` field at `u32[3]`.

#### Class A: `mode = 00000004`

This class often looks like a small anchor / point-like / simple square object.

Representative examples:

- `123`
  - `F022(dt_002, field4=0)` -> one child:
    - `id=0`
    - `mode=00000004`
    - `10 x 10`
  - `F022(dt_004, field4=0)` -> one child:
    - `id=1`
    - `mode=00000004`
    - `10 x 10`
- `159`
  - `F022(dt_002, field4=0)` -> one child:
    - `id=0`
    - `mode=00000004`
    - `10 x 10`
  - `F022(dt_010, field4=1)` -> one child:
    - `id=2`
    - `mode=00000004`
    - `15 x 15`

This class is common for:

- `dt_xxx` groups with:
  - `field4=0`
  - sometimes `field4=1`

#### Class B: `mode = 00410004`

This class looks much more like actual textured UI quads / regions.

Representative examples:

- `124`
  - `F022(dt_007, field4=1)` -> 12 children:
    - all `mode=00410004`
    - with real on-atlas rectangle sizes like:
      - `40 x 36`
      - `22 x 22`
      - `36 x 22`
      - `40 x 28`
  - `F022(dt_009, field4=2)` -> one child:
    - `id=12`
    - `mode=00410004`
    - `304 x 207`
- `146`
  - many `dt_xxx` groups with:
    - `field4 = 14..20`
    - one child each
    - `mode=00410004`
- `151`
  - `F022(Loop, field4=3)` -> one child:
    - `mode=00410004`
  - `F022(Out, field4=4)` -> one child:
    - `mode=00410004`

So a good current operational model is:

- `mode=00000004`
  - simpler anchor/small-quad class
- `mode=00410004`
  - richer rectangle/region class that likely corresponds to real drawn UI
    elements

This still does not solve the font link, but it gives a much cleaner semantic
split inside the standard object chain.

### Practical implication for the font hunt

At the moment, the strongest standard-chain pattern for text-like groups is:

- `F022` label is a `dt_xxx` text-slot-like name
- `F022` does not carry the font family directly
- its child `F024` records carry geometry, not obvious family data

So the missing font decision likely happens:

- outside `F022` itself
- outside the obvious rectangle fields of the child `F024`
- and probably in a neighboring semantic layer that references these named
  object groups

### Known exceptions

Not every checked `F022` leads into the common `0x16`-count rectangle form.

Examples:

- `148`
  - one branch goes into `F024 count=0x2F`
- `149`
  - one branch goes into `F024 count=0x11`

So there are at least a few `F024` body variants beyond the standard rectangle
record. Those remain a separate follow-up target.

### Follow-up on the two known non-`0x16` variants

A broader scan over all `0x375ba2dc/0/*/1.file` samples found:

- `F024 count = 0x16`
  - `188` occurrences
- `F024 count = 0x2F`
  - `1` occurrence
  - `148`, at `0xC98`
- `F024 count = 0x11`
  - `1` occurrence
  - `149`, at `0x908`

So within this package, the two non-`0x16` small `F024` bodies are genuine
exceptions rather than part of a large unseen family.

#### `149`: `F024 count=0x11` currently looks like a triangle primitive

The full word layout is:

- `0000F024`
- `00000011`
- `00000002`
- `00000003`
- `00000003`
- `00000000`
- `00000000`
- `00000000`
- `00000000`
- `41800000`
- `00000000`
- `3F800000`
- `00000000`
- `41000000`
- `41400000`
- `3F000000`
- `3F800000`

One useful current interpretation is:

- 5-word header
- followed by 3 records of 4 floats each

which yields:

- vertex 0:
  - `(0, 0, 0, 0)`
- vertex 1:
  - `(16, 0, 1, 0)`
- vertex 2:
  - `(8, 12, 0.5, 1)`

That is a plausible single textured triangle in `(x, y, u, v)` form.

So the strongest current hypothesis for `149` is:

- `count=0x11` encodes a triangle primitive rather than a rectangle

This is still a hypothesis, but it fits the field count cleanly and is much
more concrete than treating this record as opaque.

#### `148`: `F024 count=0x2F` currently looks like a mesh-like primitive

The full header begins:

- `0000F024`
- `0000002F`
- `00000001`
- `00000008`
- `00000018`

After that, the payload appears to split naturally into:

- a block of float data
- then a trailing block of packed integer pairs

The strongest current structural hypothesis is:

- 5-word header
- 8 records of 4 floats each
- followed by 10 packed `u16/u16` words

Under that read, the 8 float records are:

1. `(1, 1, 0.00296736, 0.0303030)`
2. `(0, 0, 0, 0)`
3. `(337, 0, 1, 0)`
4. `(1, 32, 0.00296736, 0.9696970)`
5. `(336, 32, 0.9970330, 0.9696970)`
6. `(0, 33, 0, 1)`
7. `(336, 1, 0.9970330, 0.0303030)`
8. `(337, 33, 1, 1)`

This strongly suggests:

- `(x, y, u, v)`-like vertex records
- with normalized UV-like values near:
  - `0`
  - `1`
  - `1 / 337`
  - `1 / 33`
  - `336 / 337`
  - `32 / 33`

That is much more consistent with a textured mesh / stretchable primitive than
with a plain rectangle.

The trailing 10 words are:

- `00000001`
- `00020003`
- `00010000`
- `00030004`
- `00050001`
- `00030005`
- `00000002`
- `00060006`
- `00020004`
- `00070005`

Interpreted as packed `(u16, u16)` pairs, they become:

- `(0, 1)`
- `(2, 3)`
- `(1, 0)`
- `(3, 4)`
- `(5, 1)`
- `(3, 5)`
- `(0, 2)`
- `(6, 6)`
- `(2, 4)`
- `(7, 5)`

The exact meaning of those pairs is not solved yet, but they are consistent
with:

- index / edge / triangle connectivity data

So the strongest current hypothesis for `148` is:

- `count=0x2F` encodes a small textured mesh-like primitive
- probably using multiple vertices plus an explicit connectivity/index section

### Practical implication

For the current font-chain task, these two exceptional `F024` bodies are now
less likely to be the missing font-family selector and more likely to be:

- special-purpose UI geometry primitives

That means the main font-selection path is still more likely to live in:

- the standard `F022` grouping logic
- the standard `0x16` small `F024` object chain
- or a different non-geometry semantic layer elsewhere in the same `LMB`

### What this new anchor does and does not prove

What is now strongly supported:

- the oversized `F024` tail is not a loose blob
- at least part of it is a fixed-stride record table
- a stable ordinal / selector-like field is stored in a stable slot:
  - `record + 0x1C`

What is still unresolved:

- which surrounding fields are true "family selector" fields and which are just
  local object/state IDs
- why some samples place the family string index at `u32[3]`, while others put
  it at `u32[9]`
- whether those are:
  - two record subclasses
  - two linked records in adjacent slots
  - or one shared record layout whose semantic meaning changes by file variant

So the current best refinement is:

- we now know where one stable run-local selector / ordinal field lives inside
  the tail records
- family linkage is still local-structure-dependent and remains the next field
  to decode exactly

## Best Next Step

The next most productive direction is to decode `LMB` / `.file` structure,
especially:

- header fields before the string area
- the string table shape beginning near the `lmf` marker
- object records, especially `F022` / `F024`, that reference both:
  - `dt_xxx`
  - a font family string such as `Futura MdCn BT`

The best current target is the oversized trailing `F024` block in text-bearing
samples, because that is where `dt_xxx`, family strings, and other object-like
indices begin to coexist in the same payload, and the next useful pass should
read that region with a stronger `u16/u16` mindset rather than only as `u32`.

## F105 Boundary Correction

The earlier working habit of scanning only the region before the first `F105`
is now known to be too narrow.

Newer cross-package checks show that genuine family-bearing high-bit records can
appear:

- before the first `F105`
- after the first `F105`
- or in both phases of the same file

So `F105` is still likely to be script / callback related, but it is **not** a
safe semantic boundary for "font-relevant data ends here".

This matters because earlier passes understated several good family hits simply
by stopping too early.

## Cross-Package Expansion

The font-bearing `LMB` set is broader than the original `0x375ba2dc` samples.

Confirmed additional families:

- `0x0df00808/0/3/1.file`
  - single-family inventory:
    - `A-OTF Shin Go Pr5 R`
- `0xdec73b58/0/9..12/1.file`
  - dual-family inventory:
    - `A-OTF Shin Go Pr5 R`
    - `Futura MdCn BT`
- `0xe1a4891d/10/23..32/1.file`
  - mixed single/dual-family `LMB` files
  - again using:
    - `A-OTF Shin Go Pr5 R`
    - `Futura MdCn BT`

So the same two human-readable family names are reused across multiple UI
packages, not just the original `UI_MENU` package.

## Two Stronger LMB Classes

The expanded scan now suggests at least two useful `LMB` subfamilies for the
font-chain problem.

### Class A: inventory-only or mostly-generic family references

Representative sample:

- `0x0df00808/0/3/1.file`

Observed properties:

- `F00A` clearly inventories available family handles
- family hits exist in generic `FFFFFFFF` envelopes
- no strong adjacent `type_*` style neighbor has been isolated

So this class currently proves:

- the file knows which family is available

But it does **not** yet prove:

- how the concrete `.uifont` block size is chosen

### Class B: post-`F105` family-bearing record templates

Representative samples:

- `0xdec73b58/0/9/1.file`
- `0xe1a4891d/10/23/1.file`

These two files are especially important because they show the same family-hit
record template pattern across different packages:

- `type 0x15` with family at slot `8`
- `type 0x16` with family at slot `8`
- `type 0x58` with both families in the same record, at slots `7` and `11`

For `0xdec73b58/0/9/1.file`:

- `0x3EFC`
  - `80000015 ... 00000028 0000003E 00000000 0000000B 00010000 00080000 00000000`
  - family slot `8` = handle `0x3E` = `A-OTF Shin Go Pr5 R`
- `0x3F34`
  - `80000016 ... 00000029 0000003F 00000000 0000000F 00010000 00090000 00000000`
  - family slot `8` = handle `0x3F` = `Futura MdCn BT`
- `0x8B30`
  - `80000058 ... 0000003E ... 0000003F ...`
  - both families appear in one record

The same `0x15 / 0x16 / 0x58` pattern also appears in:

- `0xe1a4891d/10/23/1.file`

This is strong evidence that these are reusable `LMB` record classes rather
than one-off local noise.

### Class C: repeated line/style-binding templates

Representative sample:

- `0xe1a4891d/10/32/1.file`

This file introduces another recurring post-`F105` family-bearing form:

- repeated `type 0x0` records with `Futura MdCn BT` at slot `12`
- repeated `FFFFFFFF` family envelopes
- at least one `type 0x1` family-bearing record

Representative repeated form:

- `80000000 00000007 00000008 00000000 00000000 0000F105 00000002 <selector> 00000006 00000004 0000000C 00000004 00000041 00000000`

where:

- slot `12` = handle `0x41` = `Futura MdCn BT`
- slot `7` changes across the run:
  - `0x03`
  - `0x05`
  - `0x07`
  - `0x09`
  - ...

The varying slot is currently more consistent with:

- repeated line / state / substyle selection

than with a final direct `.uifont` block choice.

## Local UIFONT Correlation From New Packages

The new packages also add useful constraints on the font-resource side.

### `0xdec73b58/0/0/0.uifont` is a full local font set

Confirmed block set includes:

- `Futura_MdCn_BT62`
- `Futura_MdCn_BT28`
- `Futura_MdCn_BT26`
- `Futura_MdCn_BT20`
- `A_OTF_Shin_Go_Pr5_R20`
- `A_OTF_Shin_Go_Pr5_R16`
- `A_OTF_Shin_Go_Pr5_R20_radio`
- `HUD_12`
- `HUD_14`
- `HUD_18`
- `HUD_22`

So this package is a strong candidate for studying how one `LMB` family space
maps onto multiple concrete block sizes.

### `0xe1a4891d/10/2/0.uifont` is only partially populated

This local file still declares several familiar block headers:

- `Futura_MdCn_BT28`
- `Futura_MdCn_BT20`
- `A_OTF_Shin_Go_Pr5_R20`
- `A_OTF_Shin_Go_Pr5_R16`
- `A_OTF_Shin_Go_Pr5_R20_radio`
- `HUD_14`
- `HUD_18`

But in the checked sample, most blocks have:

- `glyph_count = 0`
- `glyph_data_offset = 0`

while `A_OTF_Shin_Go_Pr5_R20_radio` is actually populated.

So a package can expose block-name inventory locally without embedding a full
atlas payload for every declared block.

That is an important constraint for the font-chain model:

- local block declaration
- and local glyph payload presence

are not always the same thing.

### Strong concrete example: identical LMB, different local UIFONT population

One especially useful pair is:

- `0x375ba2dc/0/150/1.file`
- `0xe1a4891d/10/32/1.file`

These two `LMB` files are byte-identical.

But the nearby local font payload situation is very different:

- `0x375ba2dc/0/161/0.uifont`
  - populated blocks include at least:
    - `A_OTF_Shin_Go_Pr5_R16` (`glyph_count = 80`)
    - `Futura_MdCn_BT20` (`glyph_count = 265`)
    - `A_OTF_Shin_Go_Pr5_R20` (`glyph_count = 17`)
    - `Futura_MdCn_BT26` (`glyph_count = 20`)
  - while `Futura_MdCn_BT28` is declared but empty
- `0xe1a4891d/10/2/0.uifont`
  - declares:
    - `Futura_MdCn_BT28`
    - `Futura_MdCn_BT20`
    - `A_OTF_Shin_Go_Pr5_R20_radio`
    - `A_OTF_Shin_Go_Pr5_R20`
    - `A_OTF_Shin_Go_Pr5_R16`
    - `HUD_14`
    - `HUD_18`
  - but only `A_OTF_Shin_Go_Pr5_R20_radio` is actually populated in the checked
    sample (`glyph_count = 6`)
  - the rest have `glyph_count = 0`

So in at least this case:

- the `LMB` semantic layer is unchanged
- but the nearby local font payload inventory is not

That makes it less likely that the `LMB` record by itself is the whole answer
to atlas/block sourcing, and more likely that some part of final resolution is
resource-context-sensitive.

### The local font chain is not stored under the same item index

In the same comparison pair, the package layout also shows that the text-bearing
`LMB` item and the local font-chain item are separate siblings, not one merged
directory:

- `0x375ba2dc/0/150`
  - contains only:
    - `0.lar`
    - `1.file`
- `0x375ba2dc/0/161`
  - contains the local font chain:
    - `0.uifont`
    - `1/0.uitx`
    - `1/1/0/0.nut`
    - `1/1/0/1.nut`

and likewise:

- `0xe1a4891d/10/32`
  - contains only:
    - `0.lar`
    - `1.file`
- `0xe1a4891d/10/2`
  - contains the local font chain:
    - `0.uifont`
    - `1/0.uitx`
    - `1/1/0/0.nut`
    - `1/1/0/1.nut`

So even inside a single package, the font chain is not simply:

- "text object directory contains its own direct font payload"

There is at least one extra package-internal association step still missing from
the model.

### Important disambiguation: per-item child `2` is not the UIFont chain

Several text-bearing child items also contain their own nested child `2`, for
example:

- `0x375ba2dc/0/146/2`
- `0x375ba2dc/0/148/2`
- `0x375ba2dc/0/151/2`
- `0xe1a4891d/10/23/2`
- `0xe1a4891d/10/25/2`
- `0xe1a4891d/10/30/2`

Those nested `2` children contain:

- `0.uitx`
- one or more `.nut`

but **no** `.uifont`.

So they should currently be treated as ordinary local texture-atlas chains for
that UI item, not as the missing font-source chain.

This is easy to confuse with:

- `0xe1a4891d/10/2`

which is a sibling child of the whole container and **does** contain the local
`0.uifont -> 0.uitx -> .nut` chain.

So at the moment there are two different things named "`2`":

- per-item nested child `2`
  - likely ordinary UI atlas data
- container-level child `2`
  - actual local font-resource chain

That distinction is important for avoiding false font-link conclusions.

## Declared Blocks vs Populated Blocks

Another useful constraint is that local `.uifont` blocks can be:

- declared in the block list
- but have `glyph_count = 0`

The clearest current example is:

- `0xe1a4891d/10/2/0.uifont`

Declared blocks:

- `Futura_MdCn_BT28`
- `HUD_18`
- `Futura_MdCn_BT20`
- `A_OTF_Shin_Go_Pr5_R20_radio`
- `A_OTF_Shin_Go_Pr5_R20`
- `HUD_14`
- `A_OTF_Shin_Go_Pr5_R16`

Actually populated blocks in the checked dump:

- only `A_OTF_Shin_Go_Pr5_R20_radio`

By contrast:

- `0x375ba2dc/0/161/0.uifont`

declares:

- `A_OTF_Shin_Go_Pr5_R16`
- `Futura_MdCn_BT20`
- `A_OTF_Shin_Go_Pr5_R20`
- `Futura_MdCn_BT28`
- `Futura_MdCn_BT26`

and populates all except:

- `Futura_MdCn_BT28`

This suggests the runtime may need to distinguish between:

- block declaration / availability in the resource namespace
- and actual local glyph payload presence

## Candidate Narrowing From Shared Templates

Because some `LMB` templates are byte-identical across packages, any concrete
block they rely on must at least be plausible under the block sets declared in
both packages being compared.

### `0x375ba2dc/0/150/1.file` = `0xe1a4891d/10/32/1.file`

The strongest current local-chain candidate pair is:

- `0x375ba2dc/0/161/0.uifont`
- `0xe1a4891d/10/2/0.uifont`

Their declared intersection is:

- `A_OTF_Shin_Go_Pr5_R16`
- `A_OTF_Shin_Go_Pr5_R20`
- `Futura_MdCn_BT20`
- `Futura_MdCn_BT28`

So if this shared `LMB` template resolves through those two local chains, then
it cannot rely on:

- `Futura_MdCn_BT26`
- `A_OTF_Shin_Go_Pr5_R20_radio`
- any `HUD_*` block

as a mandatory requirement of the template itself.

### `0x375ba2dc/0/124/1.file` = `0xe1a4891d/10/25/1.file`

This `LMB` inventories only one family:

- `A-OTF Shin Go Pr5 R`

So under the same local-chain hypothesis above, its plausible declared
intersection narrows to:

- `A_OTF_Shin_Go_Pr5_R16`
- `A_OTF_Shin_Go_Pr5_R20`

That makes it unlikely that this particular shared template depends on:

- `R30_radio`
- `R20_radio`

unless another package-level routing layer overrides the apparent local-chain
candidate.

### `0x375ba2dc/0/138/1.file` = `0xe1a4891d/10/28/1.file`

This file also inventories only:

- `A-OTF Shin Go Pr5 R`

and includes a stronger family-bearing high-bit record:

- `type 0x16`
  - tail words include:
    - `00010000`
    - `00070000`

So under the same declared-set intersection, its current plausible block
candidates are again:

- `A_OTF_Shin_Go_Pr5_R16`
- `A_OTF_Shin_Go_Pr5_R20`

## Practical refinement

The current best interpretation is now:

- `LMB` gives family/style-like semantics
- the package/container provides one or more candidate local font chains
- some templates are reused byte-for-byte across packages
- therefore the final block choice probably depends on:
  - shared `LMB` semantics
  - plus package-local font-chain context
  - and possibly whether a declared block is actually locally populated

## Current Best Refinement

The strongest current update to the chain is:

- `F00A` is still the family inventory table
- family-bearing high-bit records are still the best semantic selectors
- but those records are **not** restricted to the pre-`F105` region
- and there are now multiple reusable family-bearing record classes:
  - `0x0A / 0x0B / 0x0E / 0x0F` in older `0x375ba2dc` style-like cases
  - `0x15 / 0x16 / 0x58` in `0xdec73b58` and `0xe1a4891d/10/23`
  - `0x0 / 0x1` repeated forms in `0xe1a4891d/10/32`

What remains unresolved is still the same last mile:

- which field in those records selects the concrete `.uifont` block size
- or whether some of these records stop one layer short, selecting only:
  - family
  - style
  - line/state variant

before another local rule resolves:

- `BT20`
- `BT26`
- `BT28`
- `BT62`
- `R16`
- `R20`
- `R20_radio`

## Best Next Step

The next best pass is no longer just "scan pre-`F105` tail records".

It should instead compare **reused record types across packages**, especially:

- `0x15`
- `0x16`
- `0x58`
- `0x0`
- `0x1`

and correlate them against nearby local `.uifont` block inventories, looking
for a field that changes when:

- the family stays the same
- but the available concrete block set differs

## Cross-Package Byte-Identical LMB Reuse

Another strong constraint emerged from hashing the `LMB` `.file` payloads.

Several files under `0xe1a4891d/10` are byte-identical to files under
`0x375ba2dc/0`.

Confirmed identical pairs:

- `0x375ba2dc/0/124/1.file` = `0xe1a4891d/10/25/1.file`
- `0x375ba2dc/0/127/1.file` = `0xe1a4891d/10/26/1.file`
- `0x375ba2dc/0/138/1.file` = `0xe1a4891d/10/28/1.file`
- `0x375ba2dc/0/147/1.file` = `0xe1a4891d/10/29/1.file`
- `0x375ba2dc/0/148/1.file` = `0xe1a4891d/10/30/1.file`
- `0x375ba2dc/0/149/1.file` = `0xe1a4891d/10/31/1.file`
- `0x375ba2dc/0/150/1.file` = `0xe1a4891d/10/32/1.file`
- `0x375ba2dc/0/121/1.file` = `0xe1a4891d/10/24/1.file`

There is also one confirmed byte-identical pair between the other two
cross-package families:

- `0xdec73b58/0/9/1.file` = `0xe1a4891d/10/23/1.file`

### Why this matters

This sharply limits what can be safely attributed to the `LMB` payload alone.

If two packages reuse the exact same `LMB` bytes, then differences in actual
runtime font sourcing cannot come from:

- any field unique to that specific `LMB` copy

They would instead have to come from one of:

- package-local sibling resource layout
- which local `.uifont` / `.uitx` / `.nut` resources are actually populated
- a higher-level package routing rule
- or a global/shared fallback path

So this reuse result pushes the current model slightly away from:

- "`LMB` fully determines the concrete font block by itself"

and slightly toward:

- "`LMB` determines family/style-like semantics, while final block resolution may
  still depend on package/resource context"

### Important caution

This does **not** prove that `LMB` lacks a block-size selector field.

It only proves that if such a selector exists, it is:

- part of the shared `LMB` template reused across packages

and therefore cannot explain any package-to-package difference by itself unless
the surrounding font-resource context also changes.

## `0xdec73b58/0/2.file` (`ATS`) and `0xdec73b58/0/1.afs`

The package-local routing layer under `0xdec73b58/0` is now much clearer.

### `ATS` header layout

For `0xdec73b58/0/2.file`:

- magic: `ATS\0`
- `0x04-0x07`: `0x77BFABF5`
- `0x08-0x0B`: `0x5F8E00D8`
- `0x0C-0x0F`: `0x01000000`
- `0x10-0x11`: `0x00D2` = `210`
- `0x12-0x13`: `0x001F` = `31`
- `0x14-0x17`: `0x0000001C`
- `0x18-0x1B`: `0x000009F4`

The reliable interpretation is:

- `0x10-0x11` = entry count
- `0x12-0x13` = slot/descriptor count
- `0x14-0x17` = entry-table start offset
- `0x18-0x1B` = entry-table end offset

This means the valid `ATS` entry region is:

- `0x1C .. 0x9F4`

and contains exactly:

- `(0x9F4 - 0x1C) / 0x0C = 210` entries

which matches the stored count `0x00D2`.

### `ATS` entry shape

Each `ATS` entry is:

- `u32 hash`
- `char[2] lang`
- `u16 zero`
- `s32 slot`

The valid language set is:

- `JP`
- `US`
- `FR`
- `IT`
- `GE`
- `SP`
- `RU`

So the `ATS` core is a direct:

- `hash + language -> slot index`

table.

Observed facts:

- there are `30` distinct left-side hashes in the valid region
- the slot values are in the range `0..30`
- most hashes map to all 7 languages
- several hashes switch slot by language, usually:
  - `JP/RU`
  - versus `US/FR/IT/GE/SP`

Examples:

- `0x10733957 -> 21` for all languages
- `0x29DF7BCD -> 13` for `JP/RU`, `14` for the others
- `0x785BE878 -> 6` for `JP/RU`, `7` for the others
- `0xAA79A99A -> 30` for `JP`, `29` for `RU`, `27` for the others

### `ATS` tail

After the entry table, the remaining tail is:

- `0xE50 - 0x9F4 = 0x45C = 1116` bytes

Given the stored slot count `31`, that tail splits perfectly into:

- `31` records
- `0x24` bytes each

So `ATS` is not just a flat routing table. It has:

- a language routing table
- followed by `31` fixed-size slot descriptor records

Each slot descriptor is currently best treated as:

- `9 x u32`

The slot records contain many layout-sized values, for example:

- `0x00000280` = `640`
- `0x00000258` = `600`
- `0x00000438` = `1080`
- `0x000002D0` = `720`
- `0x0000012C` = `300`
- `0x000003FC` = `1020`

So this tail does **not** look like a plain child-index table.
It looks more like:

- slot metadata
- or slot layout / state descriptors

with the routing table selecting one of those `31` slot records.

### `AFS` header layout

For `0xdec73b58/0/1.afs`:

- magic: `AFS\0`
- `0x04-0x07`: `0x77FC6D79`
- `0x08-0x0B`: `0x5F8E00D8`
- `0x0C-0x0D`: `0x0100`
- `0x0E-0x0F`: `0x00CB` = `203`
- `0x10-0x13`: `0x00000014`

There is no tail here. The whole file is exactly:

- header size `0x14`
- plus `203 * 0x0C` bytes of entries

So the `AFS` entry shape is:

- `u32 hash`
- `char[2] lang`
- `u16 zero`
- `u32 value`

This gives a direct:

- `hash + language -> value`

table with:

- `29` distinct left-side hashes

### `AFS` to `ATS` cross-links

The strongest new clue is that several `AFS` right-side values are themselves
valid `ATS` left-side hashes.

Examples:

- `0x4D1A0761 -> 0xE09A4F62`
- `0x50576A50 -> 0xC692A2DA`
- `0xC6D5A64C -> 0xC214BBFB`
- `0xE6912703 -> JP: 0xAA79A99A, others: 0xE09A4F62`
- `0xFA5B0646 -> JP: 0xAA79A99A, others: 0xC692A2DA`

This means `AFS` is very likely not an unrelated side table.
It appears to participate in a package-local redirect / alias step such as:

- `hash A -> hash B`
- then `hash B + language -> ATS slot`

That is currently the strongest concrete evidence for a package-internal
intermediate routing layer between the higher-level UI semantics and the final
slot-descriptor selection.

### Cautions

What is still **not** proven:

- what the `ATS` left-side hashes name
- what each `ATS` slot descriptor field means
- whether the selected slot then points directly to:
  - a local `LMB`
  - a local `LAR`
  - a local atlas chain
  - or another intermediate rule

What is now safe to say:

- `ATS` is a real structured routing table, not random payload
- `ATS` chooses among `31` fixed slot descriptors
- `AFS` shares the same hash domain and redirects into `ATS` keys in multiple cases
- therefore `AFS + ATS` together are the strongest current candidates for the
  missing package-local resolution layer

### Repro helper

A reproducible parser for this analysis now lives at:

- `Scripts/analyze_ats_afs.py`

Example:

```powershell
python Scripts/analyze_ats_afs.py `
  "E:\Games\Emulator\ACI-Reverse-Engineering\ACI-FileSystem-Research\Tools\ACI-File-Tools\output\FullGame\0xdec73b58\0\2.file" `
  "E:\Games\Emulator\ACI-Reverse-Engineering\ACI-FileSystem-Research\Tools\ACI-File-Tools\output\FullGame\0xdec73b58\0\1.afs"
```

## `ATS` / `AFS` uniqueness in the current full-game dump

Within the current merged `FullGame` extraction:

- only one `ATS` file was found
- only one `AFS` file was found

Those are exactly:

- `0xdec73b58/0/2.file` (`ATS`)
- `0xdec73b58/0/1.afs` (`AFS`)

So the currently observed `AFS + ATS` routing layer is not a broadly repeated
generic side format in the dump.
At least in the present extraction, it is a very specific package-local
structure tied to `0xdec73b58`.

## `ACT` hash domain vs `AFS` / `ATS` hash domains

The direct compare against the shared text package now rules out another
possible shortcut.

Checked files:

- `0xfcc2ac23/0/0.act`
- `0xdec73b58/0/1.afs`
- `0xdec73b58/0/2.file` (`ATS`)

Distinct key counts from the current parsers:

- `ACT` left-side text hashes: `6836`
- `AFS` left-side hashes: `29`
- `AFS` right-side values: `13`
- `ATS` left-side hashes: `30`

Observed intersections:

- `ACT` vs `AFS` left: `0`
- `ACT` vs `AFS` right: `0`
- `ACT` vs `ATS` left: `0`

So the current evidence says:

- the `ACT` text-hash space is not the same domain as the package-local
  `AFS` / `ATS` routing hashes
- therefore `AFS` / `ATS` should currently be treated as UI-page / slot routing
  data, not as a direct `ACT text key -> font` selector

What still remains compatible with the evidence is:

- `ACT` supplies text content
- Lua or another higher-level binding layer chooses which text ids to push into
  UI text slots
- package-local `AFS` / `ATS` then participate in UI-side routing unrelated to
  the raw `ACT` text-hash ids themselves

One still-valid internal relation here is:

- `AFS` right-side values and `ATS` left-side keys do overlap
- current overlap set:
  - `0x8A34B81D`
  - `0xAA79A99A`
  - `0xC214BBFB`
  - `0xC692A2DA`
  - `0xE09A4F62`

So the `AFS -> ATS` redirect idea still stands, but it is now clearly separate
from the shared `ACT` text-id domain.

## Lua text-binding evidence

The current strongest bridge between `ACT` text ids and UI text slots is now
the binary Lua script string stream.

Important caution:

- this is not yet a full opcode-level Lua decode
- the evidence below is from ordered printable-string windows extracted from the
  `.lua` binaries
- so it should be read as strong adjacency evidence for binding calls, not as a
  final decompiled control-flow proof

A reproducible extractor for this now lives at:

- `Scripts/analyze_lua_text_bindings.py`

### Concrete binding windows in `0xe1a4891d/10/11/1.lua`

One strong local-page window is:

- `RegistTextId`
- `dt_001`
- `MsnPauseDesc_`
- `dt_002`
- `MsnObjective_`
- `ReplaceSymbolToTex`
- `box_Areamap`

This is the clearest current evidence that the script is binding mission text
ids into concrete page-local text slots, then pairing that with a specific page
object (`box_Areamap`).

The same script also contains a reusable menu-component path:

- `_textId`
- `MenuItem_Pause_001`
- `_msgId`
- `MenuDesc_Pause_001`

and later:

- `ctrl_SetHeaderTextId`
- `MenuHeader_Pause_001`
- `aacomp_menu_button`
- `aacomp_menu_message`
- `ctrl_SetMessageTextId`

So not every `ACT` text key is going straight into the same page-local `dt_xxx`
namespace. Some ids are passed into reusable component scripts instead.

### Concrete binding windows in `0xe1a4891d/10/14/1.lua`

The respawn page gives even better local-slot evidence.

Window 1:

- `RegistTextId`
- `dt_003`
- `InfoItem_UsingExContract`
- `ReplaceSymbolToTex2DObj`
- `box_extra`

Window 2:

- `RegistTextId`
- `dt_001`
- `InfoItem_RspGaugeStatus_001`
- `InfoItem_RspGaugeStatus_006`
- `dt_002`
- `dt_004`
- `ReplaceSymbolToGauge`
- `bar_001`

Window 3:

- `RegistTextId`
- `dt_001`
- `InfoItem_PvPRsp_002`
- `RegistCustomTextId`
- `dt_002`
- `string`
- `format`
- `dt_004`
- `%02d`
- `ReplaceSymbolToGauge`
- `bar_001`

These windows are the best current byte-backed evidence that:

- Lua selects named text ids such as `InfoItem_*`
- binds them into concrete `dt_xxx` slots
- and may mix direct text ids with custom/generated text before updating page
  objects like `box_extra` or `bar_001`

The same script also has reusable menu-item bindings:

- `_textId`
- `MenuItem_Rsp_001`
- `_msgId`
- `MenuItem_Rsp_010`
- `MenuItem_Rsp_007`

and:

- `_textId`
- `MenuItem_Rsp_011`
- `_infoId`

plus dialog ids:

- `DlgMsg_Rsp_001`
- `DlgMsg_Rsp_002`

So this script touches both:

- page-local `dt_001..dt_004`
- shared menu/dialog/component text-id flows

### Shared menu launcher evidence in `0x375ba2dc/0/43/1.lua`

This shared script has the same component-style pattern:

- `_textId`
- `MenuItem_SingleTop_006`
- `_msgId`
- `MenuDesc_SingleTop_008`
- `_scriptName`
- `campaignMissionSelect`

and later:

- `_textId`
- `MenuItem_SingleTop_009`
- `_msgId`
- `MenuDesc_Sto_026`
- `_scriptName`
- `freeFlightMissionSelect`

It also contains:

- `ctrl_SetHeaderTextId`
- `MenuHeader_Single_003`
- `aacomp_menu_button`
- `aacomp_info_basic`
- `aacomp_menu_message`
- `ctrl_SetMessageTextId`

So the shared launcher scripts are consistent with the same broader model:

- `ACT` text ids are chosen in Lua
- then passed into either:
  - page-local `dt_xxx` registrations
  - or reusable UI component scripts through `_textId`, `_msgId`,
    `ctrl_SetHeaderTextId`, and `ctrl_SetMessageTextId`

## Local page `10/27` as the current best slot/family sample

The paired page for the local respawn / free-flight script cluster remains:

- `0xe1a4891d/10/27/1.file`

Its string table directly contains:

- `dt_001`
- `dt_002`
- `dt_003`
- `dt_004`
- `box_extra`
- `bar_001`
- `type_campaign`
- `type_respawn_coop`
- `type_respawn_deathmatch`
- `type_freeflight`
- `A-OTF Shin Go Pr5 R`
- `Futura MdCn BT`

`F00A` confirms the local family inventory:

- slot `0` -> handle `0x13` -> `A-OTF Shin Go Pr5 R`
- slot `1` -> handle `0x14` -> `Futura MdCn BT`

`F022` groups in the same page reference the local slot/object namespace:

- one group references `dt_001` / `dt_002`
- another references `dt_001` / `dt_004`
- another references `dt_001` / `dt_003` together with `type_respawn_coop`

And the current pre-`F105` family-hit scan found two important high-bit
records:

- `0x1088`: record type `0x5`, family handle `0x13`
- `0x10C0`: record type `0x6`, family handle `0x14`

Those two records differ in family handle while staying inside the same local
page context, which is strong evidence that this page can select between both
known UI text families locally.

What is still not proven from this alone is the final per-slot rule, for
example:

- whether `dt_001` always means `A-OTF`
- whether `dt_003` always means `Futura`
- or whether the family choice depends on another record field / object subtype

But this page is currently the best compact sample where all of the following
coexist in one place:

- local `dt_xxx` slots
- local object names (`box_extra`, `bar_001`)
- mode/type names (`type_respawn_*`, `type_freeflight`)
- both known font families
- and Lua scripts that reference the same page-local objects and slots

### New constraint: the family hits sit inside two near-identical record clusters

The `10/27` family-bearing records are now better constrained structurally.

Around the current family hits, the page contains two near-identical
high-bit-record clusters:

- cluster A: `0x0E94 .. 0x0F74`
  - types: `3, 4, 5, 6, 7`
- cluster B: `0x1018 .. 0x10F8`
  - types: `3, 4, 5, 6, 7`

The most important point is that the known family records:

- `0x1088` = type `5`
- `0x10C0` = type `6`

are not isolated records. They are members of cluster B, and the whole cluster
shares a very stable template.

For cluster B:

- all records share:
  - word1 = `0x00000005`
  - word2 = `0x00000006`
  - word3 = `0x00000000`
  - word4 = `0x00000000`
  - word5 = `0x00000004`
  - word6 = `0x0000000C`
  - word9 = `0x00000000`
  - word11 = `0x00010000`
  - word13 = `0x00000000`
- the varying fields are mainly:
  - marker/type
  - word7
  - word8
  - word10
  - word12

The two concrete family hits are:

- `0x1088`
  - type `5`
  - word7 = `0x0F`
  - word8 = `0x13`
  - word10 = `0x07`
  - word12 = `0x00030000`
- `0x10C0`
  - type `6`
  - word7 = `0x10`
  - word8 = `0x14`
  - word10 = `0x08`
  - word12 = `0x00040000`

This is currently the strongest byte-backed reason to treat:

- word8 as the leading candidate for the per-record family selector field

because:

- `0x13` resolves to `A-OTF Shin Go Pr5 R`
- `0x14` resolves to `Futura MdCn BT`
- and the rest of the surrounding record template stays almost unchanged

This does **not** yet prove that word8 alone is sufficient for the final
concrete UIFONT block choice, but it does narrow the unknowns a lot:

- `F00A` inventories available families
- and word8 inside these cluster records is now the strongest current candidate
  for choosing one family per concrete record instance

### Cross-page support from `0xdec73b58/0/9/1.file`

The local `10/27` result is now reinforced by a second page that shows the same
general behavior.

In the reused common page:

- `0xdec73b58/0/9/1.file`

the two cleanest family-bearing sibling records are:

- `0x3EFC` = type `0x15`
- `0x3F34` = type `0x16`

Their words are:

- `0x3EFC`
  - `80000015 00000006 00000007 00000000 00000000 00000004 0000000C 00000028 0000003E 00000000 0000000B 00010000 00080000 00000000`
- `0x3F34`
  - `80000016 00000006 00000007 00000000 00000000 00000004 0000000C 00000029 0000003F 00000000 0000000F 00010000 00090000 00000000`

Here again:

- the surrounding template is almost identical
- and the family choice becomes visible in word8:
  - `0x3E` -> `A-OTF Shin Go Pr5 R`
  - `0x3F` -> `Futura MdCn BT`

So despite different record type numbers and different neighboring string ids,
both pages now show the same higher-level pattern:

- one pair of sibling records
- nearly identical fixed fields
- family change exposed in word8

This strengthens the current interpretation that:

- `F00A` is the page-level available-family inventory
- while word8 inside specific high-bit record templates is a per-record family
  selector candidate

### `word10` is now the strongest target-handle candidate

The next useful constraint came from comparing the `10/27` local page records
against the actual Lua bindings in `10/14/1.lua`.

For the duplicated `type 3..7` clusters in `10/27`, word10 is stable by type:

- type `3` -> word10 = `0x06`
- type `4` -> word10 = `0x04`
- type `5` -> word10 = `0x07`
- type `6` -> word10 = `0x08`
- type `7` -> word10 = `0x09`

Under compact-handle interpretation, those are:

- `0x06` -> `dt_003`
- `0x04` -> `dt_002`
- `0x07` -> `dt_004`
- `0x08` -> `box_extra`
- `0x09` -> `bar_001`

That set is important because the paired Lua page really does bind text and
symbols into exactly that local namespace:

- `RegistTextId -> dt_003 -> InfoItem_UsingExContract -> box_extra`
- `RegistTextId -> dt_001 / dt_002 / dt_004 -> ... -> bar_001`
- `RegistCustomTextId -> dt_002 / dt_004 -> ... -> bar_001`

So even though the exact record semantics are still unresolved, word10 is now
the strongest current candidate for:

- the local target handle
- or at least a field tightly coupled to the target slot/object selected by the
  record

This also fits the common-page sample.

For the `0xdec73b58/0/9` family-bearing sibling records:

- type `0x15` -> word10 = `0x0B`
- type `0x16` -> word10 = `0x0F`

Under compact-handle interpretation those are:

- `0x0B` -> `dt_005`
- `0x0F` -> `dt_006`

and nearby sibling records in the same cluster use:

- `0x0E` -> `dt_007`
- `0x04` -> `dt_002`

So in both the local and common pages, word10 repeatedly lands on plausible
local text-slot / object handles rather than on obviously unrelated values.

This is now the strongest working read for word10:

- `word10 = target-handle candidate`

with the caution that some low values are still ambiguous between raw string
indices and compact handles. The current evidence nonetheless favors compact
handle interpretation for this field.

### `word12` is currently best read as an in-cluster ordinal / id

In the `10/27` duplicated `type 3..7` clusters, word12 is:

- `0x00010000`
- `0x00020000`
- `0x00030000`
- `0x00040000`
- `0x00050000`

This value:

- does not look like a string reference
- does not vary with the family switch between the two duplicated clusters
- and increases in a clean 1-step pattern across sibling records

So the strongest current read is:

- `word12 = in-cluster ordinal / record id candidate`

The common-page family clusters show the same general shape, just at higher
steps such as:

- `0x00080000`
- `0x00090000`

which is consistent with the field behaving more like a record-local or
template-local running id than a semantic selector.

### `word7` is still unresolved, but now looks more like a secondary subtype field

For the duplicated `10/27` `type 3..7` clusters, word7 stays the same between
cluster A and cluster B:

- `0x0D`
- `0x0E`
- `0x0F`
- `0x10`
- `0x11`

while word8 shifts by `+6` between the two clusters.

That means:

- word7 is not participating in the visible family switch between the two
  duplicated clusters
- word7 is therefore more likely to encode:
  - a subtype
  - a state label
  - or another per-type secondary selector

rather than the final family choice itself.

The current best field split for this template family is therefore:

- `word8` = strongest family-selector candidate
- `word10` = strongest target-handle candidate
- `word12` = strongest ordinal / record-id candidate
- `word7` = secondary subtype / state candidate

### `type 8 / 9 / A / B` now look like a neighboring page-behavior layer

Pulling in the nearby `10/27` records after the `type 3..7` family clusters
helps separate concerns inside the local page.

The first nearby group is:

- `0x1470` = type `8`
- `0x1610` = type `9`
- `0x1698` = type `9`
- `0x1770` = type `8`

These records share a compact template centered on:

- word1 / word2 = `0x03 / 0x04`
- word5 / word6 / word10 / word12 repeatedly landing on:
  - `dt_002`
  - `box_Areamap`
  - small control values

Most importantly, word7 walks:

- `0x02` -> `box_Areamap`
- `0x05` -> `box_extra` under raw indexing, but also compact-handle overlap with
  `box_Areamap`
- `0x08` -> `type_respawn_coop` / compact overlap with `box_extra`
- `0x0B` -> `Wait` / compact overlap with `type_respawn_coop`

Even with the raw-vs-handle ambiguity, the cluster clearly stays in the local
page-object namespace around:

- `box_Areamap`
- `box_extra`
- `type_respawn_coop`

That makes this group look less like a font-choice layer and more like:

- local page object / mode routing

### The later `type A / B` group looks even more behavior-oriented

The later local block:

- `0x20D0` = type `A`
- `0x2118` = type `B`
- `0x2150` = type `A`
- `0x2198` = type `B`
- `0x21E0` = type `B`
- `0x2218` = type `A`
- `0x2260` = type `A`

shows repeated references to:

- `F105`
- `box_Areamap`
- `type_respawn_deathmatch`
- `ExternalInterface`
- `addCallback`
- `movie_clip`

This is very different from the clean family-bearing `type 3..7` text clusters.

The current best reading for this `A/B` group is:

- a scene / callback / movie-control layer
- or at least a page-behavior layer tightly coupled to embedded scene control

rather than a direct text-style selector layer

This matters because it narrows the likely family-selection search space:

- `type 3..7` are still the strongest local candidates for text/family-bearing
  records
- `type 8/9/A/B` now look more like neighboring page-structure / mode /
  callback records that happen to live in the same local `LMB`

### Practical consequence

For the current `ACT -> slot -> font` line, the cleanest next focus remains:

- the duplicated `type 3..7` clusters in `10/27`

rather than the later `type 8/9/A/B` groups, because:

- the family switch is visible there
- the target-handle candidate field is visible there
- and the surrounding records are structurally cleaner and less polluted by
  scene-callback machinery

What still remains unresolved is:

- whether the same template family is reused everywhere under different type
  numbers
- or whether several related templates each place the family selector in the
  same word position by convention

### The earlier sibling cluster has the same template without family hits

Cluster A (`0x0E94 .. 0x0F74`) uses the same general template as cluster B, but
its word8 series is:

- `0x0B`
- `0x0C`
- `0x0D`
- `0x0E`
- `0x0F`

while cluster B uses:

- `0x11`
- `0x12`
- `0x13`
- `0x14`
- `0x15`

So cluster B is not just two standalone family records. It is a second, shifted
copy of the same `type 3..7` template, and only inside that second copy do the
type `5` / `6` entries land on the two known family strings.

That makes the current best reading:

- type `5` / `6` are special within this template family
- and the pair of type `5` / `6` records is where the concrete text-family
  choice becomes visible

### Repro helper

A reproducible cluster dumper for this stage now lives at:

- `Scripts/analyze_lmb_record_clusters.py`

Example:

```powershell
python Scripts/analyze_lmb_record_clusters.py `
  "E:\Games\Emulator\ACI-Reverse-Engineering\ACI-FileSystem-Research\Tools\ACI-File-Tools\output\FullGame\0xe1a4891d\10\27\1.file"
```

## Updated best model

The current strongest end-to-end model is now:

- `ACT` stores localized text content keyed by `hash_label` / text ids
- Lua scripts choose which text ids are used in a given UI state
- Lua then binds those ids either:
  - into page-local `dt_xxx` slots with `RegistTextId` /
    `RegistCustomTextId`
  - or into reusable UI components via `_textId`, `_msgId`,
    `ctrl_SetHeaderTextId`, `ctrl_SetMessageTextId`
- `LMB` pages define the local slot/object namespace and carry font-family
  inventory via `F00A`
- `.uifont` provides the concrete bitmap glyph blocks for those families

So the current best chain is now slightly more precise:

`ACT text id -> Lua binding call -> page-local dt slot or component text slot -> LMB family inventory / page record -> UIFONT block`

## Minimal 24-byte `LAR` header model

The compact `LAR` files under these UI chains are now constrained much better.

Across the current `FullGame` dump:

- there are `55` compact `LAR` files of exactly `24` bytes
- all `55` share the same fixed field pattern:
  - `0x08-0x0B = 100`
  - `0x0C-0x0F = 100`
  - `0x10-0x13 = 1`
- only the final field varies:
  - `0x14-0x17 = 2` in `28` files
  - `0x14-0x17 = -1` in `27` files

The current minimal header model is therefore:

- `0x00-0x03`: magic `LAR `
- `0x04-0x07`: hash / id
- `0x08-0x0B`: constant `100`
- `0x0C-0x0F`: constant `100`
- `0x10-0x13`: constant `1`
- `0x14-0x17`: signed nested-child selector

### Strong evidence for `0x14-0x17`

For every compact `LAR` with final value `2`:

- the parent directory contains child folder `2`

For every compact `LAR` with final value `-1`:

- the parent directory contains no numeric child folder

Observed full-dump counts:

- non-negative final value with matching child dir: `28`
- non-negative final value without matching child dir: `0`
- negative final value: `27`

So the strongest current interpretation is:

- `0x14-0x17 = 2` means "this `LAR` has a nested child chain at child `2`"
- `0x14-0x17 = -1` means "no nested child chain"

This is especially relevant for the current font-route candidates:

- `0xdec73b58/0/9/0.lar` ends in `2` and has nested child `2`
- `0xdec73b58/0/10/0.lar` ends in `-1` and has no nested child `2`
- `0xdec73b58/0/11..14/0.lar` end in `2` and all have nested child `2`

The byte-identical reused pair also preserves this exactly:

- `0xdec73b58/0/9/0.lar`
- `0xe1a4891d/10/23/0.lar`

Both are:

- byte-identical
- end in `2`
- and both have a nested child `2`

### Repro helper

A reproducible scanner for this compact `LAR` pass now lives at:

- `Scripts/analyze_lar_headers.py`

Example:

```powershell
python Scripts/analyze_lar_headers.py `
  "E:\Games\Emulator\ACI-Reverse-Engineering\ACI-FileSystem-Research\Tools\ACI-File-Tools\output\FullGame"
```

## Header `0x04` vs `0x08`

The current full-dump scan now makes the split between header `0x04` and
header `0x08` much clearer.

### `0x04` behaves like a resource-format signature

Observed across the current `FullGame` extraction:

- all `ACT` files share the same `0x04`:
  - `0x77BFB429`
- all `UIFONT` / `ACF` files share the same `0x04`:
  - `0x77BF873D`
- the only `ATS` file uses:
  - `0x77BFABF5`
- the only `AFS` file uses:
  - `0x77FC6D79`
- `LMB` is different again and currently uses:
  - `0x00000010`

So `0x04` is **not** behaving like a per-package or per-font-chain id.
It is behaving much more like:

- a resource-type-specific build/version/signature field

This is especially clear because:

- `119 / 119` `ACT` files have the same `0x04`
- `120 / 120` `UIFONT` files have the same `0x04`

### `0x08` behaves like a sibling font-group id

The situation at `0x08` is the opposite.

Across the current full-dump scan:

- `ACT` has `12` distinct `0x08` values
- `UIFONT` also has `12` distinct `0x08` values
- every `ACT` file has an `0x08` that appears in at least one `UIFONT`

This makes `0x08` the strongest current candidate for:

- sibling group id
- font-chain id
- or a shared resource binding id between text-side and font-side assets

### Strong direct examples

For `0xfcc2ac23`:

- `0xfcc2ac23/0/0.act`
  - `0x08-0x0B = 0x5F8E0145`
- `0xfcc2ac23/0/1/0.uifont`
  - `0x08-0x0B = 0x5F8E0145`

For `0xdec73b58`:

- `0xdec73b58/0/2.file` (`ATS`)
  - `0x08-0x0B = 0x5F8E00D8`
- `0xdec73b58/0/1.afs`
  - `0x08-0x0B = 0x5F8E00D8`
- `0xdec73b58/0/0/0.uifont`
  - `0x08-0x0B = 0x5F8E00D8`

So the safe current interpretation is:

- `0x08` links `ACT`, `AFS`, `ATS`, and `UIFONT` siblings into one font/text
  resource group

### Important special case: `0x5F8E00D8`

The most informative group is:

- `0x5F8E00D8`

Current members:

- `0xe1a4891d/10/1.act`
- `0xe1a4891d/10/2/0.uifont`
- `0xdec73b58/0/0/0.uifont`
- `0xdec73b58/0/1.afs`
- `0xdec73b58/0/2.file`

This group is important because the two `UIFONT` members are not equivalent:

- `0xdec73b58/0/0/0.uifont`
  - full local font set
  - `11` blocks
  - all blocks populated
- `0xe1a4891d/10/2/0.uifont`
  - only `7` declared blocks
  - only `A_OTF_Shin_Go_Pr5_R20_radio` is locally populated in the checked dump

This reinforces the current model:

- `0x08` identifies the font/text resource group
- but multiple resources can participate in that group
- and not every local participant has to carry the full usable payload

In other words, `0x08` does **not** mean:

- "this one exact local file is the entire answer"

It more likely means:

- "this resource belongs to the same font/text chain"

with the final runtime resolution still depending on:

- package-local routing (`AFS` / `ATS`)
- local population state
- and possibly fallback to another group member that carries the complete data

### What this rules out

This new scan makes two negative statements reasonably safe:

- `ATS` left-side keys are not just `ACT` package ids
- `ATS` left-side keys are not the internal `ACT` text-entry hashes from
  `0xfcc2ac23/0/0.act`

The direct check against the exported `0xfcc2ac23_0_0.act.json` produced:

- `6836` internal `ACT` entry hashes
- intersection with the current `ATS` key set: `0`

So whatever the `ATS` key domain is, it is currently **not** the same as:

- the `ACT` content-label hash table

It remains more likely to be:

- a package-local UI route/state key space
- or another higher-level indirection layer above raw text-entry hashes

## `0x08` groups also correlate with package-local path patterns

The `0x08` field is not only shared between `ACT` and `UIFONT`.
It also clusters files into very stable **relative-path patterns** inside the
package tree.

Current full-dump examples:

- `0x59870669`
  - `ACT`: always `13.act`
  - `UIFONT`: always `12/0.uifont`
- `0x5988B5FA`
  - `ACT`: always `13.act`
  - `UIFONT`: always `12/0.uifont`
- `0x59E5F2B4`
  - `ACT`: always `13.act`
  - `UIFONT`: always `12/0.uifont`
- `0x5A22F8C2`
  - `ACT`: always `13.act`
  - `UIFONT`: always `12/0.uifont`
- `0x5F8E00DB`
  - `ACT`: always `13.act`
  - `UIFONT`: always `12/0.uifont`

So for those large groups, the package-local pattern is strongly:

- `.../13.act`
- paired with
- `.../12/0.uifont`

Other groups show similarly stable but different local patterns:

- `0x5F8E0144`
  - `ACT`: always `0/0.act`
  - `UIFONT`: always `0/1/0.uifont`
- `0x5F8E0145`
  - `ACT`: always `0/0.act`
  - `UIFONT`: always `0/1/0.uifont`
- `0x53EF4DC5`
  - `ACT`: `14/0.act`, `14/2.act`, `14/4.act`
  - `UIFONT`: `14/1/0.uifont`, `14/3/0.uifont`, `14/5/0.uifont`
- `0x540C21C6`
  - `ACT`: `0/155.act`
  - `UIFONT`: `0/154/0.uifont`
- `0x5F8E0173`
  - `ACT`: `0/160.act`
  - `UIFONT`: `0/161/0.uifont`
- `0x5F8C78FD`
  - `ACT`: `0/153/2.act`
  - `UIFONT`: `0/153/1/0.uifont`

### Why this matters

This makes `0x08` look even less like a raw font-face id and more like a
package-local **text/font chain binding id**.

The routing pattern is often not:

- "same folder, same filename stem"

but rather:

- "known neighboring/local structural counterpart"

Examples:

- `13.act -> 12/0.uifont`
- `0/0.act -> 0/1/0.uifont`
- `14/0.act -> 14/1/0.uifont`
- `14/2.act -> 14/3/0.uifont`
- `14/4.act -> 14/5/0.uifont`

So the engine's effective chain is likely not built from filenames alone.
It seems to use:

- package-local structure
- plus shared group id `0x08`

to bind text resources to their font resources.

### The important exception remains `0x5F8E00D8`

This one still stands out:

- `ACT`: `0xe1a4891d/10/1.act`
- `UIFONT`: both
  - `0xe1a4891d/10/2/0.uifont`
  - `0xdec73b58/0/0/0.uifont`

This is the current strongest evidence that:

- the group id `0x08` can identify a chain shared across packages
- and the local package member does not have to be the complete payload carrier

## Direct `0xe1a4891d/10/0/0.ui` inspection

To pursue the `0x5F8E00D8` exception, I directly parsed:

- `0xe1a4891d/10/0/0.ui`
- its local child chain:
  - `0xe1a4891d/10/0/1/0.uitx`
  - `0xe1a4891d/10/0/1/1/0/1.nut`

### Stable `UI2D` header

`0.ui` begins with a stable big-endian `UI2D` header:

- magic: `UI2D`
- image id: `0x5F8DFEC6`
- layer count: `404`

The layer pointer table is:

- `404 * 12` bytes
- each entry:
  - `u32 layer_id`
  - `s32 payload_offset`
  - `s32 payload_size`

### Layer payload type split

The first `s32` of each payload behaves like `UI2DLayerType`.

Observed distribution in `0xe1a4891d/10/0/0.ui`:

- type `1`, size `56`: `122` entries
- type `2`, size `40`: `275` entries
- type `3`, size `52`: `3` entries
- type `3`, size `68`: `1` entry
- type `4`, size `24`: `3` entries

This matches the existing Ulysses enum shape:

- `1 = Texture`
- `2 = Transition`
- `3 = Properties`
- `4 = Shape`

### The local `UITX` link is real

`0xe1a4891d/10/0/1/0.uitx` has:

- magic: `UITX`
- variable count: `0`
- texture count: `111`

The `122` texture-layer payloads in `0.ui` behave like:

- type `1`
- `UnknownIndex = -1`
- `Scale = (1.0, 1.0)` in all observed cases
- `UITXUniqueIndex` values spanning the local atlas entry space

Representative decoded texture-layer fields:

- `LayerId = 0x04A236A8`
  - `FHMIndex = 1`
  - `UITXUniqueIndex = 2`
  - crop/size: `x=415 y=89 w=38 h=17`
  - rect: `0.0, 0.0, 38.0, 17.0`
  - `UITXIndex = 2`
- `LayerId = 0x1D39229E`
  - `FHMIndex = 1`
  - `UITXUniqueIndex = 7`
  - crop/size: `x=203 y=2 w=379 h=37`
  - rect: `0.0, 0.0, 379.0, 37.0`
  - `UITXIndex = 4`

So this `0.ui` definitely has a normal local image-atlas chain:

- `0.ui -> 0/1/0.uitx -> 0/1/1/0/1.nut`

### Global anomaly: one texture layer uses `FHMIndex = 2`

Across the `122` texture-layer payloads:

- `121` use `FHMIndex = 1`
- exactly `1` uses `FHMIndex = 2`

That unique layer is:

- `LayerId = 0xF0C316BA`
- payload offset `0x56AC`
- size `56`
- `UnknownIndex = -1`
- `FHMIndex = 2`
- `UITXUniqueIndex = 6`
- crop/size: `x=39 y=490 w=2 h=5`
- rect: `0.0, 0.0, 2.0, 5.0`
- `Unknown1 = 0`
- `UITXIndex = 4`

This matters because a global scan over the current full dump found:

- `2328` `UI2D` files with at least one texture layer
- only **one** of them has any texture-layer `FHMIndex != 1`
- that one file is exactly:
  - `0xe1a4891d/10/0/0.ui`

So the `FHMIndex = 2` case is not normal `UI2D` noise.
It is a real global exception tied to the same package that also carries:

- `1.act`
- the incomplete local `10/2/0.uifont`
- and the cross-package `0x5F8E00D8` anomaly

### Important refinement: `FHMIndex` is not selecting a different atlas here

I checked the `122` texture layers against the local:

- `0xe1a4891d/10/0/1/0.uitx`

Result:

- all `122` texture-layer `UITXUniqueIndex` values are in range of the local `UITX`
- all `122` texture-layer crop rectangles match the local `UITX` entry at that same index exactly
- including the anomalous one:
  - `layer[386]`
  - `FHMIndex = 2`
  - `UITXUniqueIndex = 6`
  - crop `39,490,2,5`
  - and local `0/1/0.uitx` texture entry `6` is also exactly `39,490,2,5`

So for this file, `FHMIndex = 2` does **not** mean:

- "use a different `UITX` table"
- or
- "use a different texture atlas package"

That interpretation would also fail structurally, because:

- all currently scanned `UIFONT` sibling `UITX` files are just empty headers
  - current full-dump count: `120 / 120`
  - `variable_count = 0`
  - `texture_count = 0`
- so the `UIFONT` atlas metadata is not carried by sibling `UITX`
  - it is still consistent with the current `UIFONT` reverse-engineering model that atlas metadata lives inside the `.uifont` block data
- and the specific local font texture for `0xe1a4891d/10/2/0.uifont` is far too small for this crop
  - local `1.nut` surface: `64 x 72`
  - shared/common `0xdec73b58/0/0/0.uifont` `1.nut` surface: `2048 x 2048`
  - so a crop using `y = 490` cannot possibly refer to the local `10/2` font atlas

The current stronger reading is:

- `FHMIndex` is some additional routing/ownership field
- while the actual texture crop source here is still the local `0/1/0.uitx`

### Scope inference from package layout

Inside `0xe1a4891d/10/0`, the `0.ui` resource only has:

- local child `1`

There is no local child `2` under `10/0`.

So if `FHMIndex` is truly an index-like field, then for this record it cannot be:

- relative to the immediate `10/0` child container

It would have to be one of:

- relative to some higher-scope parent container
- or a different kind of logical/resource-bank id

### The package shape is also globally unique

A full scan of the current dump found that `0xe1a4891d/10` is the only package that simultaneously contains:

- `0/0.ui`
- `1.act`
- `2/0.uifont`

Counts observed:

- packages with `0/0.ui` and `1.act`: `1`
- packages with `1.act` and `2/0.uifont`: `1`
- packages with `0/0.ui`, `1.act`, and `2/0.uifont`: `1`

and all three counts point to the same path:

- `0xe1a4891d/10`

This does not yet prove what `FHMIndex = 2` means,
but it materially strengthens the suspicion that the anomalous field is tied to
this package's unusual coexistence of:

- local `UI2D`
- local `ACT`
- and local incomplete `UIFONT`

### Stronger `UI2D` bank model

Further direct parsing shows that `type 1`, `type 2`, and `type 3` layer payloads
share a common prefix:

- word `0`: layer type
- word `1`: always `-1`
- word `2`: a shared bank-like field

Observed in `0xe1a4891d/10/0/0.ui`:

- `type 1`
  - bank `1`: `121`
  - bank `2`: `1`
- `type 2`
  - bank `1`: `264`
  - bank `2`: `11`
- `type 3`
  - bank `1`: `4`
  - bank `2`: `0`

A full-dump scan over `2328` `UI2D` files found:

- only `0xe1a4891d/10/0/0.ui` contains any `type 1/2/3` layer with bank `!= 1`

So this is not just a texture-layer anomaly.
It is a file-wide abnormal bank value pattern unique to this one package.

### `type 2` word 6 behaves like an `AFS` key

For `type 2` layers specifically, the payload word at index `6`
(counting from the payload start, where word `0` is the type)
is now strongly correlated with `AFS` keys in:

- `0xdec73b58/0/1.afs`

Observed in `0xe1a4891d/10/0/0.ui`:

- total `type 2` layers: `275`
- `word6` matching an `AFS` key: `265`
- only one non-`AFS` exception value:
  - `0xB4C07103`
  - appears `10` times
  - appears only in this `0.ui`

This is the current strongest direct structural bridge from:

- local `0xe1a4891d/10/0/0.ui`

to:

- cross-package `0xdec73b58/0/1.afs`

#### Dominant `type 2` `word6` keys

Largest groups:

- `0x14756F71`
  - count `73`
  - banks `{1: 71, 2: 2}`
  - `AFS` value `0xFDF9282F`
- `0x2179F415`
  - count `56`
  - banks `{1: 51, 2: 5}`
  - `AFS` value `0xC8F5B34B`
- `0xF6B45FC6`
  - count `56`
  - banks `{1: 56}`
  - `AFS` value `0xE09A4F62`
- `0xE6912703`
  - count `49`
  - banks `{1: 49}`
  - `AFS` value `0xAA79A99A`

#### Bank-2-only `type 2` route keys

The bank-2 `type 2` subset uses only four `word6` keys:

- `0x2179F415`
  - `5` uses
  - `AFS` value `0xC8F5B34B`
- `0x14756F71`
  - `2` uses
  - `AFS` value `0xFDF9282F`
- `0x3BFFB9A7`
  - `3` uses
  - `AFS` value `0xD273FEF9`
- `0x4914E674`
  - `1` use
  - `AFS` value `0xA098A12A`

Notably:

- `0x3BFFB9A7`
- `0x4914E674`

were first noticed because they occur in bank-2 layers and also appear as
language-repeated `AFS` keys.

### What this means right now

At current confidence, the bank field is better described as:

- a shared `UI2D` bank / resolver selector

and `type 2` `word6` is better described as:

- an `AFS`-domain route key

This still does **not** prove the exact runtime meaning of bank `2`.
But it does make one thing much stronger:

- `0xe1a4891d/10/0/0.ui` is not only structurally unusual
- it is also explicitly carrying keys from the same cross-package `AFS` domain
  used by the suspicious `0xdec73b58` package

That is the strongest concrete connection so far between the `UI2D` side and
the `AFS/ATS` routing side.

### The bank-2 `AFS` values still do not land in any known next-hop domain

For the four bank-2-associated `AFS` keys:

- `0x2179F415 -> 0xC8F5B34B`
- `0x14756F71 -> 0xFDF9282F`
- `0x3BFFB9A7 -> 0xD273FEF9`
- `0x4914E674 -> 0xA098A12A`

the current negative results are now stronger:

- the four `AFS` values are **not** `AFS` keys
- the four `AFS` values are **not** `ATS` keys
- the four `AFS` values are **not** compact `LAR` ids
- the four `AFS` values are **not** top-level package-folder hashes
- the four `AFS` values do not occur anywhere inside:
  - `0xe1a4891d/10`

So these values are not simply:

- a second-stage `AFS` redirect key
- an `ATS` resolver key
- or a literal id reused directly by the local `e1a4891d/10` resource files

### They are also not `ACEText` entry hashes

Using the current Python `ACEText` parser:

- `0xe1a4891d/10/1.act` parses successfully with:
  - `7` languages
  - `180` entries
- none of the following appear in that local `ACT`'s internal entry-hash table:
  - the four bank-2 `AFS` keys
  - the four resulting `AFS` values

The exclusion also holds globally across the current full dump:

- parsed `ACT` files: `119`
- total parsed `ACEText` entries: `317863`
- intersection with:
  - `{0x2179F415, 0x14756F71, 0x3BFFB9A7, 0x4914E674, 0xC8F5B34B, 0xFDF9282F, 0xD273FEF9, 0xA098A12A}`
- result:
  - `0`

So at current confidence these hashes do **not** belong to the same domain as:

- localized `ACEText` entry hashes

This narrows the unresolved next-hop space further:

- `UI2D type2 word6` clearly enters the `AFS` key domain
- but the resulting `AFS` value still points into another, still-unidentified
  resource/state namespace above raw `ACEText` content hashes

### Negative results from direct byte cross-checks

The following direct checks produced no matches:

- `0.ui` image id `0x5F8DFEC6` does not occur in:
  - `0xe1a4891d/10/1.act`
  - `0xdec73b58/0/1.afs`
  - `0xdec73b58/0/2.file`
  - `0xe1a4891d/10/23/0.lar`
  - `0xe1a4891d/10/23/1.file`
- the anomalous layer id `0xF0C316BA` also does not occur in those files
- none of the `0.ui` image/layer hashes intersect the currently parsed `AFS` or `ATS` key domains

So at the current confidence level, `0.ui` does **not** provide a direct
explicit byte-for-byte bridge from `1.act` to `0xdec73b58/0/0/0.uifont`.

What it does provide is:

- a confirmed local image-atlas chain
- plus one globally unique `FHMIndex = 2` texture-layer exception
- inside the same package that already contains the cross-package font-group anomaly

That keeps `0xe1a4891d/10` highly suspicious, but the explicit routing key is
still not recovered.

### Repro helper

A reproducible scanner for these `0x08` path-group patterns now lives at:

- `Scripts/analyze_act_uifont_groups.py`
- `Scripts/analyze_ui2d_fhm_indices.py`
- `Scripts/analyze_ui2d_afs_links.py`

Example:

```powershell
python Scripts/analyze_act_uifont_groups.py `
  "E:\Games\Emulator\ACI-Reverse-Engineering\ACI-FileSystem-Research\Tools\ACI-File-Tools\output\FullGame"

python Scripts/analyze_ui2d_fhm_indices.py `
  "E:\Games\Emulator\ACI-Reverse-Engineering\ACI-FileSystem-Research\Tools\ACI-File-Tools\output\FullGame\0xe1a4891d\10\0\0.ui"

python Scripts/analyze_ui2d_afs_links.py `
  "E:\Games\Emulator\ACI-Reverse-Engineering\ACI-FileSystem-Research\Tools\ACI-File-Tools\output\FullGame\0xe1a4891d\10\0\0.ui" `
  "E:\Games\Emulator\ACI-Reverse-Engineering\ACI-FileSystem-Research\Tools\ACI-File-Tools\output\FullGame\0xdec73b58\0\1.afs"
```

## Current Best Constraint on `dt_xxx -> A-OTF ... RXX`

The newest cross-checks suggest a narrower but also more careful conclusion:

- `HashLabel -> dt_xxx` is real and script-visible.
- `dt_xxx -> family` is real and `LMB`-visible.
- but `dt_xxx -> exact A-OTF size tier` is **not** yet proven to be a direct,
  one-step mapping.

At current confidence, `dt_xxx` alone is not enough to tell us whether the
final block is:

- `A_OTF_Shin_Go_Pr5_R16`
- `A_OTF_Shin_Go_Pr5_R20`
- `A_OTF_Shin_Go_Pr5_R20_radio`
- or `A_OTF_Shin_Go_Pr5_R30_radio`

The strongest current model is instead:

`ACT HashLabel -> Lua slot name dt_xxx -> LMB text object/style template -> font family -> concrete block constrained by the bound UIFONT chain`

So the exact `RXX` tier appears to depend on at least:

- the `LMB` record/template that owns the slot
- plus the package/group-local font chain bound at header `0x08`
- plus which blocks are actually declared/populated in that bound `.uifont`

### Hard size-domain constraints from confirmed ACT/UIFONT groups

The following group bindings are now especially useful because they sharply
limit which concrete `A-OTF` blocks are even available.

#### Group `0x540C21C6`

Confirmed pair:

- `0x375ba2dc/0/155.act`
- `0x375ba2dc/0/154/0.uifont`

Observed local `A-OTF` inventory:

- `A_OTF_Shin_Go_Pr5_R30_radio`

Observed ACT content shape:

- `155.act` is dominated by entries such as:
  - `movie05.xml_Sheet1_051`
  - `movie07.xml_Sheet1_017`
  - `movie13.xml_Sheet1_035`

So any `A-OTF` text resolved through this specific ACT/UIFONT chain is
currently constrained to:

- `R30_radio`

This is the cleanest current proof that the final size tier can be constrained
by the group-bound font chain itself, not by a bare `dt_xxx` name.

#### Group `0x5F8E0173`

Confirmed pair:

- `0x375ba2dc/0/160.act`
- `0x375ba2dc/0/161/0.uifont`

Observed local `A-OTF` inventory:

- `A_OTF_Shin_Go_Pr5_R16`
- `A_OTF_Shin_Go_Pr5_R20`

and **not**:

- `R20_radio`
- `R30_radio`

Observed script evidence in the same package:

- `0x375ba2dc/0/106/1.lua`
- `0x375ba2dc/0/168/1.lua`

These scripts contain strong radio-menu anchors such as:

- `TabHeader_HgrRadio_002 .. 008`
- `GetRadioTextId`
- `SetupRadioMenuList`
- `SetupCurrentRadioMenuList`

So for this hangar/radio chain, any `A-OTF` text the page resolves cannot
currently be higher-confidence than:

- one of `R16` / `R20`

but it is already very unlikely to be:

- `R20_radio`
- `R30_radio`

#### Group `0x5F8E00D8`

Confirmed chain members:

- `0xe1a4891d/10/1.act`
- `0xe1a4891d/10/2/0.uifont`
- `0xdec73b58/0/0/0.uifont`

Observed `A-OTF` inventory across the participating local/shared chains:

- local `10/2/0.uifont`
  - `A_OTF_Shin_Go_Pr5_R20_radio` populated
  - `A_OTF_Shin_Go_Pr5_R20` declared
  - `A_OTF_Shin_Go_Pr5_R16` declared
- shared `0xdec73b58/0/0/0.uifont`
  - `A_OTF_Shin_Go_Pr5_R20`
  - `A_OTF_Shin_Go_Pr5_R16`
  - `A_OTF_Shin_Go_Pr5_R20_radio`

So for this chain the currently plausible `A-OTF` size domain is:

- `R16`
- `R20`
- `R20_radio`

This again supports the idea that `dt_xxx` does not directly encode the full
final tier by itself.

### Script/page evidence that still stops at slot/style, not final size

Recent script checks further reinforce the same boundary.

#### `0x375ba2dc/0/102/1.lua` == `0xe1a4891d/10/17/1.lua`

This duplicated script contains:

- `Challenge_Msg_Header_001`
- `Challenge_Msg_Text_001`
- `Challenge_Msg_Text_003`
- `Challenge_Msg_Text_004`
- `Challenge_Msg_Text_006`

and also registers:

- `dt_001 -> SystemChainText`
- `dt_002 -> ButtonMessage`

The current object-level match in the notes remains:

- `10/17 -> 10/23`

and `10/23/1.file` does indeed inventory both:

- `A-OTF Shin Go Pr5 R`
- `Futura MdCn BT`

But that still only proves:

- which slot names the script uses
- and which families the page template exposes

It does **not** uniquely collapse the `A-OTF` side to one concrete `RXX` tier.

### Current safest reading

The safest current statement is:

- `dt_xxx` is a slot/object binding name
- not yet a proven direct size-tier id

The engine likely resolves the final `A-OTF ... RXX` block from:

- slot/template semantics in `LMB`
- plus the family-bearing record template
- plus the ACT/UIFONT chain selected by group/context

So the remaining work is no longer:

- "which `dt_xxx` exists?"

but specifically:

- "which `LMB` record archetype inside a given font-chain context picks `R16`
  vs `R20` vs `R20_radio`?"

### `*_radio` does not currently behave like a simple content-semantic flag

One tempting shortcut was to read the `_radio` suffix literally and assume:

- radio-themed text uses `A_OTF_Shin_Go_Pr5_R20_radio`
- non-radio text uses the plain `R16/R20` blocks

The current package evidence argues against that simple reading.

#### Hangar radio chain without any `_radio` block

In group `0x5F8E0173`:

- `0x375ba2dc/0/160.act`
- `0x375ba2dc/0/161/0.uifont`

the local `A-OTF` inventory is only:

- `A_OTF_Shin_Go_Pr5_R16`
- `A_OTF_Shin_Go_Pr5_R20`

There is no:

- `A_OTF_Shin_Go_Pr5_R20_radio`
- `A_OTF_Shin_Go_Pr5_R30_radio`

Yet the paired script side is clearly radio-oriented.

`0x375ba2dc/0/106/1.lua` contains:

- `SetupCurrentRadioMenuList`
- `SetupRadioMenuList`
- `GetRadioTextId`
- `TabHeader_HgrRadio_002 .. 017`
- `MenuDesc_HgrRadio_001`
- `MenuDesc_HgrRadio_002`

So at least this confirmed hangar-radio chain does **not** require a `_radio`
font block.

#### Another radio-flavored text path also lacks a `_radio` block

`0x375ba2dc/0/168/1.lua` contains a clan/chat path that explicitly includes:

- `RADIO`
- `CHATWORD_TYPE_RADIO`
- `MenuItem_HgrCatalog_016`

and still sits in the same package context whose known local font chain is the
same `0x5F8E0173 -> 0/161/0.uifont` pair above.

So even a second radio-flavored UI path inside that context still does not
force the presence of a `_radio` block.

#### Safer current interpretation of the suffix

At current confidence, the `_radio` suffix is better treated as:

- a concrete style/block lineage name
- not yet a proven direct marker for "all radio-related content"

In other words, the current data supports:

- some radio-themed UI chains using plain `R16/R20`

and therefore does **not** support:

- a simple content-semantic rule like "radio text => `*_radio` block"
