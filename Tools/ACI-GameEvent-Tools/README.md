# ACI-GameEvent-Tools

PyQt5 tool for browsing Ace Combat Infinity game event data from unpacked TSS directories.

## Current Page

- `Game Event View`
  - Input the unpacked TSS root directory such as `E:/Games/Emulator/ACI/TSS/Unpack`
  - Automatically scans all sibling `NPWR04428_00-*` package directories and merges their event rows
  - Still accepts a single package directory such as `NPWR04428_00-1`
  - Scans `.lvst` and `.act` files under each loaded package
  - Supports package filtering from a dropdown
  - Supports three merge modes:
    - `Merged by Event ID` (default): picks the highest-numbered `NPWR04428_00-*` package as the effective row
    - `Merged by Content`
    - `Raw Rows`
  - Supports optional external name resolution from:
    - `Full Game ACT Json`
    - `ParaTranz Json`
  - If an event `Text Hash` matches an entry `Hash` in the ACT Json, the matched `Label` is used to look up text in the ParaTranz Json
  - The list `Name` column prefers this external text first, then falls back to `Name (US)`, then `Name (JP)`
  - Parses event schedule rows from `LVST`
  - Resolves event names and linked challenge text from `ACT`
  - Uses plaintext fallback labels from sibling packages when tokenized TSS text cannot be displayed directly
  - Displays event ID, name, start time, end time, source table, and challenge count

## Run

```powershell
.\.venv\Scripts\python.exe .\main.py
```

## Current Parsing Model

- Event schedule rows:
  - detected from `LVST` tables containing:
    - `0x59FEC50B` event id
    - `0xC9593D6F` start date
    - `0xDF8C1FB7` start time
    - `0x8CA04356` end date
    - `0x38A4B1DD` end time
- Event names:
  - tries `ShortName_RankEvent{id}`
  - then `LongName_RankEvent{id}`
  - then `Reward_RankEvent{id}`
  - then falls back to the row text hash target if available
- Linked challenges:
  - detected from `LVST` tables containing:
    - `0xF7740E1D` event id
    - `0x26B6DAC0` challenge title hash
    - `0xF67C9878` challenge message hash

## Notes

- This is a first-pass event browser.
- Some event IDs still do not have a clean user-facing name in the current heuristic model.
- The next step can be adding more event families and richer cross-table linkage rules.
