# Schem & Litematic to NBT

A cross-platform graphical and command-line tool for batch-converting Minecraft Java Edition files:

- Sponge `.schem` files, versions 2 and 3;
- Litematica `.litematic` files, including multi-region schematics;
- to vanilla Java Edition structure `.nbt` files.

The converter preserves as much source data as the vanilla structure format allows, including block states, palettes, block entities, entities, and the source Minecraft `DataVersion`.

Large structures can be split automatically into configurable chunks. The default is `48 × 48 × 48`, which is suitable for vanilla structure blocks. A JSON manifest records the position and dimensions of every generated chunk.

## Graphical interface

The interface is entirely in English and includes:

- multi-file selection;
- recursive folder import;
- drag and drop when TkDND is available;
- folder-tree preservation in the output directory;
- conversion progress and a detailed activity log;
- a prominent conversion button and direct access to the output folder.

## Windows quick start

1. Install Python 3.10 or newer.
2. Extract the project.
3. Double-click `run_gui.bat`.
4. Add `.schem` or `.litematic` files, select the output directory, and click **Start conversion**.

The launcher detects `python`, `py -3`, or `python3`. It supports the Microsoft Store Python installation and creates an isolated `.venv-win` environment automatically.

### Build a Windows executable

Double-click:

```text
build_windows.bat
```

The resulting executable is written to:

```text
dist\SchemNBTConverter.exe
```

The build script deliberately uses:

```text
.venv-win\Scripts\python.exe -m PyInstaller
```

It therefore does not require the global `py` launcher or a globally accessible `pyinstaller` command.

A Windows executable must be built on Windows; PyInstaller does not cross-compile Windows executables from Linux.

## Linux quick start

Make the launcher executable if necessary, then run it:

```bash
chmod +x run_linux.sh
./run_linux.sh
```

The launcher creates `.venv-linux`, installs the dependencies, and opens the GUI.

Python Tk support must be installed by the operating system. Common package names are:

```text
Debian/Ubuntu: python3-tk python3-venv
Fedora:        python3-tkinter
Arch Linux:    tk
```

### Add an application-menu launcher

```bash
chmod +x install_linux_launcher.sh
./install_linux_launcher.sh
```

This installs a user-local desktop entry under `~/.local/share/applications`.

### Build a Linux executable

```bash
chmod +x build_linux.sh
./build_linux.sh
```

The resulting binary is written to:

```text
dist/SchemNBTConverter
```

Linux binaries must be built on Linux. For broad compatibility, build on a distribution that is at least as old as the target systems.

## Command-line usage

Windows:

```powershell
set PYTHONPATH=%CD%\src
.venv-win\Scripts\python.exe -m schem_nbt_converter build1.schem build2.litematic -o .\output
```

Linux:

```bash
PYTHONPATH="$PWD/src" .venv-linux/bin/python -m schem_nbt_converter build1.schem build2.litematic -o ./output
```

Main options:

```text
--max-size 48    maximum size of each generated chunk
--no-split       disable automatic splitting
--exclude-air    omit air blocks from the output
--overwrite      replace existing output files
--flatten        do not reproduce imported subdirectories
--gui            open the graphical interface
```

Example:

```bash
python -m schem_nbt_converter house.schem castle.litematic \
  -o ./nbt_output --max-size 48 --overwrite
```

## Preserving imported folders

When a folder is imported recursively, the relative directory structure is reproduced by default.

Input:

```text
worldpainter-trees/
├── rocks/stone01.schem
├── savanna/acacia1.schem
└── swamp/swamp_tree1.schem
```

Output:

```text
nbt_output/
├── rocks/stone01.nbt
├── savanna/acacia1.nbt
└── swamp/swamp_tree1.nbt
```

Files added individually are written directly into the selected output directory. Disable **Preserve imported folder structure** in the GUI, or use `--flatten`, to produce a flat output directory.

## Installing structures in Minecraft Java Edition

For the `minecraft` namespace, copy generated `.nbt` files into:

```text
.minecraft/saves/WORLD_NAME/generated/minecraft/structures/
```

In a structure block set to **Load**, enter the filename without `.nbt`.

Example:

```text
house.nbt -> minecraft:house
```

For a split structure, use the generated manifest. Each chunk contains an `origin` value in `[X, Y, Z]` order relative to the complete structure's origin.

## Supported formats

### Sponge `.schem`

- Sponge Schematic v2;
- Sponge Schematic v3;
- VarInt palettes;
- v3 roots nested under `Schematic`;
- block entities and entities.

The older MCEdit `.schematic` format is not supported.

### Litematica `.litematic`

- multiple regions;
- positive and negative region dimensions;
- block states;
- block entities and entities exposed by `litemapy`;
- region flattening into one common coordinate system.

When regions overlap, the last region in the file replaces earlier blocks at the same positions.

## Conversion options

### Include air blocks

Enabled by default. Air blocks in the source are exported and can clear existing blocks when the structure is placed.

When disabled, air is omitted and existing world blocks remain untouched at those positions.

### Automatic splitting

When any dimension exceeds the configured limit, the tool generates files such as:

```text
castle_x00_y00_z00.nbt
castle_x01_y00_z00.nbt
castle_manifest.json
```

Each NBT chunk has its own optimized palette.

## Known limitations

- Block IDs are not upgraded or downgraded between Minecraft versions. The source `DataVersion` and block data are preserved.
- Modded blocks remain in the NBT, but the corresponding mods must be installed when the structure is loaded.
- Vanilla structure NBT does not store biomes, scheduled ticks, or every Sponge/Litematica-specific metadata field.
- Sponge offsets have no direct vanilla structure equivalent. They are recorded in the split manifest.
- Very large files are loaded into memory during conversion.
- Some highly mod-specific entity or block-entity NBT may require manual adjustment.

## Tests

Windows:

```powershell
.venv-win\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv-win\Scripts\python.exe -m pytest -q
```

Linux:

```bash
.venv-linux/bin/python -m pip install -r requirements-dev.txt
.venv-linux/bin/python -m pytest -q
```

The automated tests cover Sponge v2 and v3, VarInt decoding, block entities, multi-region Litematica files, automatic splitting, manifests, and folder-tree preservation.

## License

GNU GPL version 3 or later, because the project uses `litemapy`, which is distributed under GPL v3.
