# TSS_NOTES

## Scope

This note summarizes the current container-level reverse-engineering conclusions for:

- `E:\Games\Emulator\ACI\TSS`
- `E:\Games\Emulator\ACI\TSS\Unpack`

The focus here is:

- raw `.tss` package structure
- DPL/FHM resource layout
- package family relationships
- likely layering / override behavior

Higher-level event-table semantics should stay in:

- [GAME_EVENT_NOTES.md](E:/Games/Emulator/ACI-Reverse-Engineering/ACI-Localization-Research/Docs/GAME_EVENT_NOTES.md)

## Raw TSS Structure

### Core observation

The raw `.tss` files are DPL-family containers.

Their payload model matches the same high-level resource layering used by PAC-like packages:

- top-level table of FHM resources
- resources keyed by top-level hash
- later / higher-priority packages can replace earlier resources by the same hash

This aligns with the existing `Ulysses` DPL/FHM parsing model.

### Standard DPL-like `.tss` files

These files begin directly with `DPL` magic and parse as top-level DPL containers:

- `NPWR04428_00-1.tss`
- `NPWR04428_00-2.tss`
- `NPWR04428_00-3.tss`
- `NPWR04428_00-4.tss`
- `NPWR04428_00-5.tss`
- `NPWR04428_00-6.tss`
- `NPWR04428_00-7.tss`
- `NPWR04428_00-8.tss`
- `NPWR04428_00-9.tss`
- `NPWR04428_00-10.tss`
- `NPWR04428_00-11.tss`
- `NPWR04428_00-12.tss`
- `NPWR04428_00-13.tss`
- `NPWR04428_00-14.tss`

### Wrapped special case: `NPWR04428_00-0.tss`

`NPWR04428_00-0.tss` does not begin with `DPL` at offset `0`.

Its first bytes are:

- `GST444444\r\n`

The embedded DPL header begins at:

- `0x0B`

After stripping that wrapper, the inner payload is a valid `3`-resource DPL.

## Raw Package Inventory

Observed file sizes:

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

## Top-Level FHM Counts

Observed top-level resource counts:

- `-1`, `-5`, `-9` = `48`
- `-3`, `-7`, `-11` = `47`
- `-2`, `-4`, `-6`, `-8`, `-10`, `-12` = `2`
- `-13` = `10`
- `-14` = `4`
- wrapped `-0` inner DPL = `3`

This matches the unpacked odd-branch root resource counts:

- `NPWR04428_00-1`, `-5`, `-9` each unpack to `48` top-level resource folders
- `NPWR04428_00-3`, `-7`, `-11` each unpack to `47` top-level resource folders

So the odd-numbered unpacked branches are already complete top-level DPL views.

## Stable Main Branches

### Large complete branch

These three packages share the same `48` top-level resource hashes:

- `NPWR04428_00-1.tss`
- `NPWR04428_00-5.tss`
- `NPWR04428_00-9.tss`

### Small complete branch

These three packages share the same `47` top-level resource hashes:

- `NPWR04428_00-3.tss`
- `NPWR04428_00-7.tss`
- `NPWR04428_00-11.tss`

### Relationship between the two branches

The large and small branches are not simple revisions of one another.

Top-level comparison:

- common resources = `11`
- large-only resources = `37`
- small-only resources = `36`

Shared top-level core:

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

This strongly suggests two distinct content branches sharing a live-service core.

## Overlay Families

### Repeating menu overlay family

All of these packages contain the exact same `2` hashes:

- `NPWR04428_00-2.tss`
- `NPWR04428_00-4.tss`
- `NPWR04428_00-6.tss`
- `NPWR04428_00-8.tss`
- `NPWR04428_00-10.tss`
- `NPWR04428_00-12.tss`

Contents:

- `0x6976b3b3` = `DPL_UI_TSS_MENU`
- `0x9b9969d5` = unknown tiny metadata item

Important property:

- these hashes do not exist in the complete `-1` or `-3` branch top-level sets

So this family behaves like an extra UI/menu layer mounted beside the main branch, not a replacement of existing top-level main-branch resources.

### `-14` UI presentation overlay

`NPWR04428_00-14.tss` contains:

- `0x62bbe64d` = unknown 2D image package
- `0x6976b3b3` = `DPL_UI_TSS_MENU`
- `0x6ff8c094` = unknown 2D image package
- `0x9b9969d5` = unknown tiny metadata item

Important property:

- it strictly contains the two-resource menu overlay family as a subset

So `-14` currently looks like a richer UI/menu/banner presentation layer.

### `-13` reduced shared-core overlay

`NPWR04428_00-13.tss` contains these `10` resources:

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

This is a strict subset of the shared core in both complete branches.

However, it is not a byte-for-byte clone of those branch resources.

For several key shared resources, the `-13` versions are much smaller than the branch versions:

- `0x3f20632f DPL_TSS_INFO`
- `0x58cf00c0 DPL_UI_TSS_COMMON`
- `0xe82647a1 DPL_INFORMATION`

So `-13` currently looks like a reduced hot-update core layer, not a raw extracted sub-branch.

## Wrapped Boot Layer: `-0`

After stripping the `GST444444\r\n` wrapper, the inner DPL contains:

- `0x2b788994` = unknown small resource
- `0x921b52bb` = unknown small resource
- `0xd100550b` = `DPL_TSS_PRODUCT_BOOT`

Important observations:

- these hashes are not part of the normal `-1` or `-3` complete branch top-level sets
- `DPL_TSS_PRODUCT_BOOT` strongly suggests a startup/front/product-boot role

Current best interpretation:

- `NPWR04428_00-0.tss` is a separate boot/front wrapper layer

## Current Best Layering Model

This is still a working model, but the current top-level relationships are strong.

### Strong numbered-pair pattern

The numbering strongly suggests that the small even-numbered packages are companions of the preceding odd-numbered main branches:

- `1 + 2`
- `3 + 4`
- `5 + 6`
- `7 + 8`
- `9 + 10`
- `11 + 12`

Evidence:

- every odd package in this set is a complete branch package
- every even package in this set is the exact same `2`-resource menu overlay

Current best interpretation:

- odd-numbered package = main event-content branch
- following even-numbered package = companion menu/UI layer

### Candidate runtime layering chain

Current best high-level model:

1. select one complete base branch
   - either `-1/-5/-9`
   - or `-3/-7/-11`
2. apply shared hot-update core layer
   - `-13`
3. apply menu/UI layer
   - either one of `-2/-4/-6/-8/-10/-12`
   - or the richer `-14`
4. keep `-0` as a separate startup/front layer

### What this model does and does not prove

This model does explain:

- which packages are complete branches
- which packages are overlays
- which overlay families supersede smaller overlay families

It does not yet prove:

- the exact retail mount order
- the exact script/config switch that chooses one branch over another

## Tooling / Extraction Notes

### Important limitation in current `Ulysses.DPLUnpack`

`Ulysses.DPLUnpack` currently mounts:

- `*.PAC`

via its existing `ResourceManager.Mount()` path.

So raw `.tss` analysis still requires:

- direct DPL probing
- manual wrapper stripping for `-0`
- custom extraction helpers

### Probe outputs used in current analysis

Temporary resource-table probe outputs were written under:

- `E:\Games\Emulator\ACI\TSS\__probe`

These contain:

- per-package top-level resource tables
- resource hash / group / size summaries

They are useful as a quick reference for future TSS-layer comparison work.
