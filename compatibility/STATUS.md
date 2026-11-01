# J460 compatibility investigation

Status: **UNVERIFIED / NOT SUPPORTED**. This change does not add J460 to the supported versions. A successful CI build only establishes compilation and packaging, not hook correctness or CrossOver compatibility.

## Inputs and inspected sources

Requested executable: `isaac-ng.exe`, PE32/i386, 9,176,064 bytes, version `1.9.7.17.J460`, SHA-256 `b3c7fdbfce664d2600f1403f290c2a8d0df7a544d1a529295ff664173fd98469`. The executable was subsequently supplied and independently verified: hash, size, PE32/i386 and embedded version string all match. See `reports/j460-preflight.json`. The file is never committed, packaged or uploaded to CI.

The working fork and upstream TeamREPENTOGON/REPENTOGON both resolved to `2a4e3a5fc01f5a58fca3d4f1f62740af0c0c16a3` during inspection. Launcher was inspected at `c14b8721d50463ac0a7fb64cb0a33db73410920a`; CI pins this revision and initializes its recursive submodules.

## Findings

- The mod's documented ABI requires the game's compiler, Windows and Win32. Its CMake configuration uses MSVC flags, Windows APIs, RC resources, Imagehlp and dbghelp, inline assembly and generated ZHL bindings. A Linux or macOS native build does not substitute for this toolchain. Existing mod CI uses Visual Studio 2022 on windows-2022.
- Launcher `src/repentogon_installation.cpp::IsIsaacVersionCompatible` accepts exactly `v1.9.7.12.J273`. `include/launcher/isaac_installation.h` names that version as the patch target. Compatibility otherwise depends on available downpatch data. A version string does not establish that a modified executable matches a patch's expected source bytes.
- Launcher's `patch/manifest.json` includes the executable, packed resources and Lua scripts; replacing just an EXE is not a complete version migration. This project does not generate or apply downpatches, alter licensing checks, supply game files or remove protection mechanisms.
- Native J460 compatibility may be possible without touching licensing, through independently verified game API hooks and layouts. It cannot be established from a hash, filename or file size. We have no evidence identifying the modifications in this particular executable, or proving they are the sole incompatibility.
- `libzhl/functions/*.zhl` defines addresses, calling conventions, data layouts and offsets. `libzhl/SigScan.cpp` may use cached matches and first matches. Finding a byte pattern does not prove uniqueness, a valid instruction boundary, or equivalent behavior.
- ASM patch sites are both registered in `ASMDefinition` and scanned directly in patch implementations. `Definition::OfflineInit` enumerates function/variable signatures; the existing `offline_scanner` injects into a process and is **not** a complete static verifier or a save-safe certification tool.
- `repentogon/Patches/ASMPatches/ASMFixes.cpp` documents fixes already addressed by game version 1.9.7.13 (including issues 605 and 599). `ASMHud.cpp` also documents patches unnecessary after that version. Reapplying them blindly to J460 risks patching changed code. Field offsets, vtables, globals, resource formats, save behavior and renderer assumptions need auditing independently of signature matches.
- `InitZHL` previously continued after failing registered ASM definitions. This change logs the failure and returns an error before `ASMPatch::_Init` or `HookMain`. Valid loader callback/output pointers are also checked before initialization, and missing/null main addresses propagate a failure rather than reporting success. Existing successful scan paths and supported version checks are preserved. This is a defensive source fix, not a J460 port, and still requires Windows compilation/runtime verification.

## Implemented infrastructure

- `preflight.py`: reads PE headers and sections, validates i386/PE32 executable structure, reports SHA-256 and candidate version strings. No process launch, executable edits or save access. Exact identity still produces `safe_to_install: false`. Exit 1 means invalid/unreadable input; exit 2 means diagnostic report generated, compatibility unverified. There is no approving exit code.
- Sixteen local tests cover static pattern matching, inventory extraction and malformed/truncated inputs, section bounds, architecture, DLL rejection, invalid entry points, misleading version strings and the non-approval rule even for a matching identity.
- `compatibility-windows.yml`: builds the mod, scanner, launcher and updater on windows-2022/VS2022/Win32; pins CMake 3.31.6 for old dependency CMake files; retains failure diagnostics; packages only complete successful outputs. Uses existing recursive submodule commits, no game executable or credentials in CI. The launcher remains unmodified and retains its existing version checks, Steam integration and update/downpatch behavior.
- `package.ps1`: requires DLLs/resources/scanner/launcher outputs, checks PE32/i386 binaries, records source commits and file hashes, emits a ZIP and SHA-256 checksum. No packaging success is claimed until Windows CI actually executes it.

## Required next evidence

1. Exact executable received and identity verified. Static source-literal triage is complete; semantic hook validation remains outstanding. To reproduce: `python3 compatibility/static_scan.py /path/to/isaac-ng.exe > static-scan.json` (exit 2 expected).
2. To audit hooks: obtain the executable's executable sections, image base, relocations and imports, plus disassembly around each referenced function/ASM patch site. Compare to a legitimately obtained J273 baseline. Verify all registered and direct-scan sites, unique intended matches, displaced instruction lengths, branch destinations, calling conventions, argument/return storage, class sizes/offsets and vtables. Do not “fix” misses by weakening patterns or selecting arbitrary matches.
3. Windows CI must execute and its configure/build/packaging logs must be inspected. GitHub API access was denied in this cloud session; adding `api.github.com` has been saved to the environment draft. Review/save the network change in environment settings and retry API access; publication and permissions are separate prerequisites. Repository write/Actions permissions must also be available. No API access or CI result should be inferred from successful Git reads.
4. Only after an audited port exists: test startup, menus, new disposable saves, rooms/combat/transitions, representative Lua hooks, mod/resource loading and save/reload, then regress J273. Capture crash logs and ZHL logs. Test the same binaries under the user's exact CrossOver version on M4. None of those runtime checks has executed in this Linux environment.

## Results for the uploaded executable

`reports/j460-static-scan.json` records source paths, line numbers, original patterns, raw match RVAs and capped counts. `static_scan.py` constructs a preferred-base image from the file sections and zero-filled image space. It strips source comments, inventories ZHL function/variable signatures, `asm` registrations and additional C++ pattern candidates. This is not an emulation of LibZHL scan order, return-seeking, capture dereferences, relocations, imported addresses or runtime memory changes; C++ candidates are not necessarily active hooks. Dynamically composed/empty/stateful signatures and compile-time reachability require manual review.

| Literal category | Single raw match | Multiple raw matches | No raw match |
| --- | ---: | ---: | ---: |
| ZHL function/variable signatures | 703 | 74 | 453 |
| Registered ASM signatures | 162 | 14 | 92 |
| C++ pattern candidates | 91 | 4 | 89 |

Examples with no raw match: `Game::Update` (`Game.zhl:43`), `Entity_Player::EvaluateItems` (`EntityPlayer.zhl:158`), `Room::SaveState` (`Room.zhl:97`), ASM `DisableExitPrompt`, `SaveButtonMaps_InputConfigsPath`, `Game_Update_Return`, and several controller reassignment sites. `IsaacMain` and `Entity::constructor` each have a single raw match; this does not validate their ABI or any patch applied to them. In particular, save/restore layouts cannot be inferred from successful signatures elsewhere.

A direct byte-pattern cross-check of representative missing and matching signatures is also performed locally. The missing patterns demonstrate that changing the version check cannot supply compatibility. No signature was weakened or replaced speculatively. Completing the port now requires a legitimately obtained J273 reference executable (or equivalent disassembly/type-layout evidence) and a systematic cross-version function/layout mapping, followed by Windows and CrossOver validation. The supplied J460 binary alone does not establish the old/new behavioral equivalence of hundreds of changed sites.

The implementation branch was pushed to `karma2z/REPENTOGONMAC` as `compatibility/j460-audit`. Push-triggered CI is configured, but Actions API requests remain Forbidden, so no Windows job status, compilation result, downloadable binary artifact or PR creation is confirmed.

No game files are included. No runtime compatibility is confirmed. A completed hook port remains blocked on executable evidence; Windows compilation results remain pending CI access/execution.
