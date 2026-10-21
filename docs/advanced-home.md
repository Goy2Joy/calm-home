# Advanced Home/startup integration and recovery

This phase uses temporary root during setup. The TV owner must explicitly authorize it and have a concrete restoration plan first. No root daemon is left running. The normal app install does not require this phase.

## Exact verified profile

`compatibility.json` records the one tested model/build: Samsung UN65CU7000DXZA, Tizen 8, build `T-KSU2ECAKUC-0080-REL-202412040254`. Native helper checks also pin both relevant system libraries; startup changes additionally pin the boot-manager hash. Other models/builds are unsupported by these configuration scripts. Do not remove these checks to make an unsupported TV pass.

The reference TV's app launches, physical Home from Netflix/YouTube, Samsung Home restoration/reapply, HDMI, Samsung Apps and aerial-saver preview were physically confirmed. Startup standby/wake and a full cold restart were physically confirmed. Changes to startup are tested independently from Home.

## Recovery plan before changes

1. Normally install/launch Calm Home and confirm its on-screen Samsung Home button works.
2. Read the effective native Home target with the helper's safe AUL getter. **Do not use `app_operation_get_current_app` as a read-only probe**: this firmware can reset/write a default when none exists.
3. Require the current native target to be the verified stock `com.samsung.tv.csfs`, code 0. Save exact original startup values and types. These scripts accept the reference baseline `home_appid=csfs` and Smart Hub auto-start `0`; any different baseline requires a reviewed device-specific plan.
4. Keep SDB connected and both computer and TV on the same reachable network while testing. Save local recovery evidence before each change.
5. Home recovery is `set-stock` with an expected current `CalmHome01.Home`. Startup recovery restores only the two backed-up settings. Neither recovery replaces a database or stock binary.

## Pinned dependency and host preparation

Use Python **3.12+** and a supported Microsoft .NET SDK capable of building `net6.0`. Download the .NET SDK from [Microsoft](https://dotnet.microsoft.com/download) if absent, using the normal owner-handled installer/terms flow.

The reviewed root dependency is [chris-ritsen/samsung-tv-root](https://github.com/chris-ritsen/samsung-tv-root), commit `4ad2c4d3b0d0e0da4b5b7ebe4a787e94596f416b`. Download the exact gzip tarball at `sourceArchiveUrl` from compatibility.json into ignored `.setup/`, verify `sourceArchiveSha256` from compatibility.json, and extract it into `.setup/root-source` using safe extraction (reject absolute/traversal paths and links). Review the source before running it. A moving branch or release is not the same reviewed input.

The reference firmware's stripped .NET host rejects `--list-runtimes`. Replace only `.setup/root-source/src/samsung_tv_root/archive_root.py` with `tools/root-patches/archive_root.py`. This small compatibility patch falls back only for that specific unsupported-option error and requires real runtime files; all other preflight failures still stop. The dependency's Unlicense notice is retained alongside the patch. `family_session.py` verifies every Python source file against the reviewed snapshot plus this patch before importing it.

Configure the local session first, using this person's values. Then use the controlled build helper; it verifies the pinned C#/project inputs, builds all three .NET projects into fresh private output directories, and records output hashes. Existing DLLs by filename alone are not accepted.

```text
python3 setup.py advanced-session --tv-ip <TV_IP> --host-ip <COMPUTER_IP> --root-source .setup/root-source --payloads .setup/root-payloads
python3 setup.py build-advanced
python3 tools/prepare_native.py --owner-approved-root
```

The loader rejects links, bytecode caches and native replacements in the reviewed Python package, disables bytecode writes for its imports, and checks the recorded build outputs before executing any root operation. If a guard fails, rebuild from a clean verified source snapshot instead of bypassing it.

The preparation tool checks exact model/build before staging only three native helper files in the TV's dedicated `sdk_tools/calm-home-integration` folder. It then invokes the helper's read-only inspect action. This source contains no private key, signing profile, owner IP or precompiled exploit payload.

The `--owner-approved-root` flag records the intended phase; a flag or these instructions alone is not human authorization. The assistant must have the actual TV owner's authorization in the conversation.

## Physical Home: set, prove rollback, reapply

```text
python3 tools/device_configure.py inspect --owner-approved-root
python3 tools/device_configure.py set-launcher --expected com.samsung.tv.csfs --owner-approved-root
```

Inspect the new record under `.setup/recovery/`. Require verified readback, a closed authenticated root session, cleaned staging and unchanged monitored system-file hashes. Then have the owner test physical Home from Netflix and a second app. Readback alone is not proof of the physical button.

```text
python3 tools/device_configure.py set-stock --expected CalmHome01.Home --owner-approved-root
```

Have the owner confirm physical Home opens Samsung Home. Only after that succeeds, reapply `set-launcher` with expected stock Home and test again. Never leave a failed configuration enabled.

## Startup: two small settings, separate testing

The exact firmware's boot code reads `db/appfw/home_appid` for its launcher and `db/menu/smart_hub/ontvsetting/auto_start` for foreground/background Home behavior. Native MAIN default alone can work on physical Home while power-on still ends at HDMI.

The startup tool compares the original exact values/types, verifies the boot-manager hash, changes the Home target to `CalmHome01.Home` and auto-start to integer `1`, reads back both, and rolls back those same two values on failure. It leaves `db/appfw/startup_appid`, the TV viewer, HDMI and stock binaries intact.

```text
python3 tools/device_startup.py enable --owner-approved-root
```

Test remote off/on and wait at least 30 seconds: Calm Home must remain visible, rather than briefly appearing before an input takes over. Test startup restoration/readback using `restore`, then reapply `enable`. Finally hold Power until a full restart/Samsung logo, release, and test separately. Report standby/wake and cold restart independently.

```text
python3 tools/device_startup.py restore --owner-approved-root
```

Startup restoration is allowed after native Home has already been restored to Samsung. Failure returns a nonzero process exit status and a recovery record; do not interpret an attempted action as success.

## Cleanup and limits

Remove only this project's SDK helper after all device checks:

```text
python3 tools/prepare_native.py --cleanup --owner-approved-root
python3 setup.py disconnect --tv-ip <TV_IP>
```

Restore temporary computer networking. Keep local backups; do not commit them. No firmware flashing, system-package uninstall, bulk service disable, stock binary replacement, signing bypass, or always-running root service is part of this project. Showing an ad-free launcher does not establish that every Samsung background service or all advertising has been removed.
