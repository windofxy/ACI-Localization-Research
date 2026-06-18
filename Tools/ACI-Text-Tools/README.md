# ACI Text Tools

Desktop utility for inspecting `ACEText` resources from *Ace Combat Infinity*.

Current scope:

- open raw `ACEText` / `.act` files
- open raw `ACETable` / `.lvst` files
- parse the `ACT` container structure
- parse the `LVST` table structure
- list hash entries
- inspect per-language localized strings
- inspect table columns and per-row values
- edit `ACETable` cell display values in a working editor page
- export and import edited `ACETable` JSON snapshots
- validate edited `ACETable` cells before binary export
- export edited `ACETable` files by fixed-layout in-place payload overwrite
- show builder support coverage for the current `ACETable` signature set

## Run

Use the local virtual environment:

```powershell
.\.venv\Scripts\python.exe main.py
```
