$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$mod = Join-Path $root 'build/RelWithDebInfo'
$launcher = Join-Path $root 'launcher-build/RelWithDebInfo'
# Never publish a partial installation as a successful build.
$required = @('libzhl.dll','zhlLoader.dll','zhlREPENTOGON.dll','Lua5.3.3r.dll','freetype.dll','offline_scanner.exe','antlr4-runtime.dll')
foreach ($name in $required) {
    if (!(Test-Path "$mod/$name")) { throw "Missing required mod output: $name" }
}
foreach ($name in @('REPENTOGONLauncher.exe', 'launcher-data.bin', 'steam_appid.txt')) {
    if (!(Test-Path "$launcher/$name")) { throw "Missing required launcher output: $name" }
}
foreach ($name in @('resources','resources-repentogon')) {
    if (!(Test-Path "$mod/$name" -PathType Container)) { throw "Missing resources: $name" }
}
$stage = Join-Path $root 'research-package'
if (Test-Path $stage) { throw 'Staging directory already exists; use a fresh build workspace.' }
New-Item -ItemType Directory -Path "$stage/mod", "$stage/launcher", "$stage/diagnostics", "$root/artifacts" -Force | Out-Null
Copy-Item "$mod/*.dll" "$stage/mod"
Copy-Item "$mod/offline_scanner.exe" "$stage/mod"
Copy-Item "$mod/resources", "$mod/resources-repentogon" "$stage/mod" -Recurse
# Keep launcher-data-build: the upstream launcher also emits an embedded ZIP.
Copy-Item "$launcher/REPENTOGONLauncher.exe", "$launcher/launcher-data.bin", "$launcher/steam_appid.txt" "$stage/launcher"
if (Test-Path "$launcher/launcher-data-build") { Copy-Item "$launcher/launcher-data-build" "$stage/launcher" -Recurse }
Get-ChildItem $launcher -Filter '*.dll' | Copy-Item -Destination "$stage/launcher"
# Verify machine type and PE32 magic for every shipped executable and DLL.
Get-ChildItem $stage -Recurse -File | Where-Object { $_.Extension -in '.exe', '.dll' } | ForEach-Object {
    $bytes = [IO.File]::ReadAllBytes($_.FullName)
    if ($bytes.Length -lt 64 -or $bytes[0] -ne 77 -or $bytes[1] -ne 90) { throw "Invalid DOS header: $_" }
    $pe = [BitConverter]::ToInt32($bytes, 60)
    if ($pe -lt 64 -or $pe + 26 -gt $bytes.Length -or [BitConverter]::ToUInt32($bytes, $pe) -ne 0x4550 -or [BitConverter]::ToUInt16($bytes, $pe + 4) -ne 0x14c -or [BitConverter]::ToUInt16($bytes, $pe + 24) -ne 0x10b) { throw "Expected PE32/i386 output: $_" }
}
Copy-Item "$PSScriptRoot/preflight.py", "$PSScriptRoot/static_scan.py" "$stage/diagnostics"
Copy-Item "$PSScriptRoot/reports" "$stage/diagnostics" -Recurse
Copy-Item "$PSScriptRoot/WINDOWS.md", "$PSScriptRoot/CROSSOVER.md", "$PSScriptRoot/STATUS.md" $stage
$manifest = [ordered]@{
    mod_commit = (git rev-parse HEAD)
    launcher_commit = (git -C _launcher rev-parse HEAD)
    compilation = 'successful; required output presence and PE32 architecture checked'
    runtime_compatibility = 'UNVERIFIED; J460 is not supported by this research build'
    files = @(Get-ChildItem $stage -Recurse -File | ForEach-Object {
        @{ path = [IO.Path]::GetRelativePath($stage, $_.FullName); sha256 = (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant() }
    })
}
$manifest | ConvertTo-Json -Depth 5 | Set-Content "$stage/build-manifest.json" -Encoding utf8
Compress-Archive -Path "$stage/*" -DestinationPath "$root/artifacts/REPENTOGON-research-win32.zip"
(Get-FileHash "$root/artifacts/REPENTOGON-research-win32.zip" -Algorithm SHA256).Hash | Set-Content "$root/artifacts/SHA256SUM.txt"
