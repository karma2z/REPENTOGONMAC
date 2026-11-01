# Windows J460 compatibility status

Target: the supplied PE32 `isaac-ng.exe`, version `1.9.7.17.J460`, SHA-256 `b3c7fdbfce664d2600f1403f290c2a8d0df7a544d1a529295ff664173fd98469`.

**The current research branch is not a completed J460 port.** It must not be installed as a compatible release. Windows is the only target required for this investigation; no macOS toolchain or compatibility-layer configuration is needed to investigate these blockers.

## Actual compatibility blockers

- Native code: static analysis found 453 ZHL and 92 ASM signature literals absent from the preferred-base image. The full report is in `reports/j460-static-scan.json`. Essential functions such as `Game::Update`, `Entity_Player::EvaluateItems` and `Room::SaveState` are affected. Matching other functions does not establish object layouts or patch correctness.
- Launcher: the inspected upstream bundled patch identifies J460 as its input version, but its expected input hash is `3bdfc8bae0dc7e334b76009d0ad45dfbb16ee5f00c06ffbc3a0094e34d44616b`. Your executable has a different hash. The launcher only directly supports J273. A stock downpatch cannot be assumed valid for a modified executable. Its input validation is retained.
- Build: the Windows workflow is published on `compatibility/j460-audit`, but this cloud session cannot access the GitHub API. CI status and artifacts cannot be inspected, and PR creation was denied. The saved `api.github.com` network setting must be applied, and repository Actions/API access must work, to continue that part of the task.

## What has actually been tested

- Executable identity and PE32/i386 format verified.
- Sixteen Python tests passed.
- Main hook's seven-byte displaced-instruction window at RVA `0x531053` is two complete immediate-push instructions. A compiled C++ validator accepts this window from the uploaded file at file offset `0x530453` (the harness reads ten bytes starting three bytes earlier at `0x530450`). This validates instruction shape only; it neither launches the game nor authorizes the other hooks.
- The C++ test project configures, compiles and passes CTest locally. Address/undefined-behavior sanitizer checks passed on the final standalone validator; leak detection is disabled because the execution sandbox prevents LeakSanitizer's process inspection. These are Linux-hosted tests of portable validation code, **not a Windows mod build**. The same project is registered for Win32/MSVC CI.
- `Game::GetPlayer` and `Game::GetNumPlayers` candidate disassembly both access the player vector at `Game + 0x1baa8` (end at `+0x1baac`), consistent with the source's `PlayerManager` location. This is corroboration of one field relationship; it does not validate the complete Game or PlayerManager layout.

## Files required to continue the port

A legitimately obtained **J273 reference executable**, or equivalent disassembly with known function/type mappings, is needed to map the changed game functions and layouts against the supplied J460 binary. The exact target EXE has already been received; there is no need to upload it again. No licensing files, credentials or crack components are requested.

Windows build results must also become accessible. Once a hook port is complete and compiled, test it against a copied game installation with independent disposable saves. Back up the whole game directory and actual save/config directory with all game/launcher processes stopped; keep backups outside the test directories. Never weaken signatures, bypass version checks, force a mismatched downpatch, or test on the only copy of a save.

A working release ZIP cannot honestly be supplied until the port, Windows compilation and runtime checks succeed.

A further search allowing equivalent register-to-register MOV/arithmetic opcode encodings still found no candidates for the existing `Game::Update`, `Entity_Player::EvaluateItems`, `Room::SaveState` and `HUD::Render` patterns. These four misses are not explained by that simple encoding substitution. No replacement signatures were inferred from this search.
