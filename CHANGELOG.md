# Changelog

## 1.2.0

- Replaced the original interface with a cleaner modern dark interface.
- Translated the GUI, command-line interface, logs, errors, documentation, and manifests into English.
- Added a prominent **Start conversion** button that remains visible in the settings panel.
- Added an output-folder shortcut, file counter, keyboard shortcuts, and improved progress reporting.
- Added `run_linux.sh`, `build_linux.sh`, and `install_linux_launcher.sh`.
- Reworked the Windows launch and build scripts to detect `python`, `py -3`, or `python3`.
- Fixed Windows builds when `py` and the global `pyinstaller` command are unavailable.
- PyInstaller now runs through the virtual environment with `python -m PyInstaller`.

## 1.1.0

- Added recursive folder imports with output-directory tree preservation.
- Added an option to flatten the output directory.
- Added tests for preserved subdirectories.

## 1.0.0

- Added a graphical interface with multi-file selection, recursive folder import, and drag and drop.
- Added Sponge Schematic v2/v3 to vanilla structure NBT conversion.
- Added multi-region Litematica to vanilla structure NBT conversion.
- Preserved block states, block entities, entities, and `DataVersion`.
- Added configurable automatic splitting and JSON manifests.
- Added a command-line interface.
- Added a PyInstaller Windows build script.
- Added automated tests for the main conversion paths.
