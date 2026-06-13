# UIFONT `0x08..0x0B` Matrix

This table summarizes the `0x08..0x0B` header field seen in official local `.uifont` samples.

Field meaning is still not fully proven, but current evidence strongly supports:

- it is not the DPL/package hash
- it is not a glyph-count or atlas-count field
- it is not a simple block-signature hash
- it behaves most like a file-level font-resource family / template / variant ID

## Matrix

| Value | High 16 | Low 16 | FullGame files | Named resource paths | Block signature(s) | Glyph counts |
| --- | --- | --- | ---: | --- | --- | --- |
| `0x53EF4DC5` | `0x53EF` | `0x4DC5` | 6 | none named in current dumps | `A_OTF_Shin_Go_Pr5_R30_radio` | varies by file: `55`, `70`, `79`, `96`, ... |
| `0x540C21C6` | `0x540C` | `0x21C6` | 1 | `DATA94/DPL_UI_MENU/0/154/0.uifont` | `A_OTF_Shin_Go_Pr5_R30_radio \| Futura_MdCn_BT28` | `A_OTF_Shin_Go_Pr5_R30_radio:839`, `Futura_MdCn_BT28:1` |
| `0x59870669` | `0x5987` | `0x0669` | 9 | none named in current dumps | `A_OTF_Shin_Go_Pr5_R20_radio` | varies by file: `540`, `551`, `556`, `653`, ... |
| `0x5988B5FA` | `0x5988` | `0xB5FA` | 47 | none named in current dumps | `A_OTF_Shin_Go_Pr5_R20_radio \| Futura_MdCn_BT28` | varies by file: `566`, `692`, `1001`, `1002`, ...; `Futura_MdCn_BT28` is reference-only (`0`) |
| `0x59E5F2B4` | `0x59E5` | `0xF2B4` | 23 | none named in current dumps | `A_OTF_Shin_Go_Pr5_R20_radio \| Futura_MdCn_BT28` | varies by file: `997`, `1001`, `1002`, ...; `Futura_MdCn_BT28` is reference-only (`0`) |
| `0x5A22F8C2` | `0x5A22` | `0xF8C2` | 15 | none named in current dumps | `A_OTF_Shin_Go_Pr5_R20_radio \| Futura_MdCn_BT28` | varies by file: `566`, `759`, `1018`, ...; `Futura_MdCn_BT28` is reference-only (`0`) |
| `0x5F8C78FD` | `0x5F8C` | `0x78FD` | 1 | `DATA94/DPL_UI_MENU/0/153/1/0.uifont` | `Futura_MdCn_BT20 \| logo` | `Futura_MdCn_BT20:1`, `logo:28` |
| `0x5F8E00D8` | `0x5F8E` | `0x00D8` | 2 | `DATA94/DPL_UI_COMMON/0/0/0.uifont`; `DATA94/DPL_SFX_UNKNOWN_0xe1a4891d/10/2/0.uifont` | 1. `Futura_MdCn_BT62 \| Futura_MdCn_BT28 \| Futura_MdCn_BT26 \| Futura_MdCn_BT20 \| A_OTF_Shin_Go_Pr5_R20 \| A_OTF_Shin_Go_Pr5_R16 \| HUD_12 \| HUD_14 \| HUD_18 \| HUD_22 \| A_OTF_Shin_Go_Pr5_R20_radio` 2. `Futura_MdCn_BT28 \| HUD_18 \| Futura_MdCn_BT20 \| A_OTF_Shin_Go_Pr5_R20_radio \| A_OTF_Shin_Go_Pr5_R20 \| HUD_14 \| A_OTF_Shin_Go_Pr5_R16` | full UI-common family: `482/550/550/542/3462/1647/14/482/482/14/50`; SFX subset: only `A_OTF_Shin_Go_Pr5_R20_radio:6`, others reference-only |
| `0x5F8E00DB` | `0x5F8E` | `0x00DB` | 7 | `DATA94/DPL_MICW12A_RES/12/0.uifont`; `...12B...`; `...12C...`; `...12D...`; `...29A...`; `...29B...`; `...29C...` | `A_OTF_Shin_Go_Pr5_R20_radio \| Futura_MdCn_BT28` | stable in all named dumps: `A_OTF_Shin_Go_Pr5_R20_radio:996`, `Futura_MdCn_BT28:0` |
| `0x5F8E0144` | `0x5F8E` | `0x0144` | 4 | `DATA94/DPL_UI_COMMON_TEXT_FR/0/1/0.uifont`; `..._IT...`; `..._JP...`; `..._US...` | 1. `Futura_MdCn_BT26 \| Futura_MdCn_BT20 \| Futura_MdCn_BT28` 2. `Futura_MdCn_BT26 \| A_OTF_Shin_Go_Pr5_R20 \| Futura_MdCn_BT20 \| Futura_MdCn_BT28 \| A_OTF_Shin_Go_Pr5_R16` | FR: `276/15/5`; IT: `274/15/5`; US: `274/16/5`; JP: `274/45/126/5/161` |
| `0x5F8E0145` | `0x5F8E` | `0x0145` | 4 | `DATA94/DPL_UI_COMMON_TEXT/0/1/0.uifont`; `..._GE...`; `..._RU...`; `..._SP...` | 1. `Futura_MdCn_BT26 \| Futura_MdCn_BT20 \| Futura_MdCn_BT28` 2. `Futura_MdCn_BT26 \| A_OTF_Shin_Go_Pr5_R20 \| Futura_MdCn_BT20 \| Futura_MdCn_BT28 \| A_OTF_Shin_Go_Pr5_R16` | base: `277/45/127/5/161`; GE: `274/16/5`; RU: `274/15/5`; SP: `274/15/5` |
| `0x5F8E0173` | `0x5F8E` | `0x0173` | 1 | `DATA94/DPL_UI_MENU/0/161/0.uifont` | `A_OTF_Shin_Go_Pr5_R16 \| Futura_MdCn_BT20 \| A_OTF_Shin_Go_Pr5_R20 \| Futura_MdCn_BT28 \| Futura_MdCn_BT26` | `A_OTF_Shin_Go_Pr5_R16:80`, `Futura_MdCn_BT20:265`, `A_OTF_Shin_Go_Pr5_R20:17`, `Futura_MdCn_BT28:0`, `Futura_MdCn_BT26:20` |

## Strong Observations

### 1. The field is not a package hash

Within `DATA94/DPL_UI_MENU`, different `.uifont` files use different values:

- `0x5F8C78FD` -> `0/153/1/0.uifont`
- `0x540C21C6` -> `0/154/0.uifont`
- `0x5F8E0173` -> `0/161/0.uifont`

So `0x08..0x0B` does not simply identify the outer DPL package.

### 2. The field is not a simple block-signature hash

The same block signature can appear under multiple values:

- `A_OTF_Shin_Go_Pr5_R20_radio | Futura_MdCn_BT28`
  - `0x5988B5FA`
  - `0x59E5F2B4`
  - `0x5A22F8C2`
  - `0x5F8E00DB`

Likewise, one value can cover both a full family and a reduced subset:

- `0x5F8E00D8`
  - full `DPL_UI_COMMON`
  - reduced `DPL_SFX` subset

So the field is not a strict hash of the exact block list either.

### 3. High 16 bits look family-like in at least one clear cluster

The `0x5F8Exxxx` group covers:

- `DPL_UI_COMMON`
- `DPL_UI_COMMON_TEXT*`
- `DPL_UI_MENU`
- `DPL_MICW*`
- `DPL_SFX` font subset

That makes `0x5F8E` look like a broader UIFont family/domain tag.

### 4. Low 16 bits behave like local variant IDs within a high-16 family

Inside the `0x5F8Exxxx` cluster:

- `0x00D8` -> shared/common UI family and a small reused subset
- `0x00DB` -> `MICW12*` / `MICW29*` mission-result style fonts
- `0x0144` -> `UI_COMMON_TEXT_FR/IT/JP/US`
- `0x0145` -> `UI_COMMON_TEXT/GE/RU/SP`
- `0x0173` -> one `UI_MENU` composite font package

This does not yet reduce to a single exact rule such as "language group" or "block signature".
But it is much more consistent with:

- high 16 bits = broad font-resource family
- low 16 bits = family-local variant / usage template / content branch

than with any hash-like interpretation.

### 5. `0x0144` and `0x0145` are especially suggestive

These two differ by only `1`, yet both belong to `DPL_UI_COMMON_TEXT*` and split the language packs:

- `0x0144`: `FR`, `IT`, `JP`, `US`
- `0x0145`: base, `GE`, `RU`, `SP`

That pattern looks deliberate and enumerative.
It does not look like CRC output.

## Current Best Hypothesis

Current strongest interpretation of `0x08..0x0B` is:

- a file-level UIFont template/classification ID
- likely composed of:
  - a broad family/group component
  - a narrower family-local variant component

Practical writer guidance for now:

- preserve this field from the template when rebuilding a `.uifont`
- do not synthesize a new value unless stronger semantics are proven
