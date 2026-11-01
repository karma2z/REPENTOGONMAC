# CrossOver on Apple Silicon: research build precautions

**J460 support is unverified. Do not install this research build into your working game or point the stock launcher at your modified executable.** The launcher retains its supported-version checks and may offer updates/downpatching. This package does not make those operations appropriate for your installation. It does not bypass Steam, DRM, licensing or copy protection.

## Preserve saves first

1. Quit Isaac, the launcher and all programs in the CrossOver bottle. Record your CrossOver version, macOS version, bottle type and graphics settings.
2. In CrossOver, archive the existing bottle and make a duplicate for testing. Keep the archive outside the bottle. Also copy the complete game directory and all save/config folders to a dated backup outside it. Check that the backup contains files before continuing.
3. Use **Open C: Drive** to inspect the duplicate bottle. Saves may be under the Wine user's `Documents/My Games/Binding of Isaac Repentance+`, a launcher-configured save directory, Steam userdata if present, or a path selected by your modified installation. Find the actual save location; do not assume a single path. A Windows drive mapping can expose your real macOS home/Documents to both bottles. Ensure the duplicate cannot write to the originals; select an independent save location or use a separate macOS test account if you cannot establish isolation.
4. Use a fresh disposable save slot/profile for future tests. Keep cloud synchronization off for the test environment where applicable. Never test save-format compatibility on your only copy of a save.

## Collect the initial diagnostic (safe to do before a port)

On macOS, with Python 3 installed:

```sh
python3 compatibility/preflight.py '/full/path/to/isaac-ng.exe' > preflight.json
```

The package places this script under `diagnostics/` instead. Exit code 2 means the report was produced and compatibility is still unverified. The tool only reads the EXE. Share `preflight.json`, the exact CrossOver version, and the EXE for static analysis. No launcher execution is needed for this step.

## Installation procedure after a validated port exists

These are conditional instructions, not a claim that this build supports J460.

1. Download the successful Windows CI artifact, extract its inner `REPENTOGON-research-win32.zip`, and compare its hash using `shasum -a 256` with `SHA256SUM.txt`. Inspect `build-manifest.json` for the source revisions and compatibility status. Do not treat a build as runtime verified merely because compilation succeeded.
2. Work only in the isolated duplicate bottle and copied game directory. Preserve original DLLs outside the game directory. This source revision builds `zhlLoader.dll` and `Lua5.3.3r.dll`; do not rename these to older release names such as `dsound.dll`/`Lua5.4.dll` or mix versions from other packages.
3. The ZIP separates `mod/` (DLLs, resources, scanner) from `launcher/` (updater EXE, launcher-data.bin and dependencies). Keep each component's packaged files together. The launcher expects its own data layout and a compatible game installation; use upstream installation instructions only once the executable has a validated supported profile. Do not overwrite the game EXE or select an automatic downpatch as a substitute for the J460 hook audit.
4. For a supported installation, run the Windows launcher using CrossOver's **Run Command** in the test bottle, with its own directory as the working directory. If the required Visual C++ runtime is missing, install Microsoft's supported x86 VS2015–2022 runtime into that bottle. The exact CrossOver controls vary by version; no DLL override has been validated here. Preserve normal launcher/version checks.
5. Stop on missing-signature errors, incompatible-version prompts, unexplained crashes or save-path ambiguity. Do not force continuation. Collect `zhl.log`, `repentogon.log`, loader/launcher logs, `sig_*.log`, any crash dump and CrossOver's Run Command debug log, where present. Also record the executable hash, artifact source commit and reproduction steps. Logs can contain local paths; review before sharing.
6. After testing, quit all bottle processes. Restore the duplicate from its archive or discard it. Restore original saves only with the game closed, and only from a backup you verified; keep the original bottle untouched.

No CrossOver runtime test, save round trip or J460 hook validation has yet passed.
