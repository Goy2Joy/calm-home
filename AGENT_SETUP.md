# Install Calm Home with an AI assistant

This is the working guide for the assistant; the person should only need to identify their TV, operate its remote, and handle their private account/certificate screens. An AI that can run local tools can do the downloads, checks, builds and installation. A chat-only assistant must explain those steps without claiming it performed them.

## 1. Establish this person's setup

Confirm the person's intended TV, exact model and full firmware/software version. Read this checkout's README and compatibility.json. Check their computer's OS, architecture, an available Python runtime, and existing Tizen Studio installation. Use an available bundled Python runtime if the system's `python3` launches an Xcode/license prompt; do not accept unrelated licenses for them.

Run `python3 setup.py doctor` (Windows: `py -3 setup.py doctor`). Reuse the installed SDK. The ordinary helper needs Python 3.10+; the optional pinned root dependency needs Python 3.12+ and the .NET SDK. Do not install root tools during the ordinary app phase.

Normal app installation is authorized by the person's request to install this project. Do not ask them to approve every routine command. Their request to install an app does not by itself authorize rooting, firmware changes, disabling system packages, or making this the default launcher.

## 2. Download the official tools

If Tizen Studio is absent, run `setup.py download-tools --dry-run`, then `setup.py download-tools`. It downloads the pinned official Tizen Studio installer into `.setup/downloads/`. The helper never runs downloaded installers or accepts licenses.

Open the downloaded installer with the person's normal computer controls. Let the person handle its license, new passwords, and any required OS approval. On Apple Silicon, check whether Rosetta is available; if needed, use Apple's normal Rosetta installation flow with the person handling its license. Do not disable Gatekeeper or certificate validation.

In Tizen Package Manager, install the TV Web tools/TV Extension and Samsung Certificate Extension. Use [Samsung's current TV SDK instructions](https://developer.samsung.com/smarttv/develop/getting-started/setting-up-sdk/installing-tv-sdk.html). The reference Mac used Tizen Studio 6.1, TV Extension 10 and the Samsung certificate extension. If package names have changed, inspect the installed manager instead of guessing names or accepting terms silently.

The Windows installer URL is official, but this project has not been physically set up on Windows. Report that limit and verify each local result.

## 3. Enable TV Developer mode

Have the person open Home → Apps (then App Settings if shown). Enter **1, 2, 3, 4, 5**.

For a remote without number keys: press its **123** or **…** button and choose the on-screen number pad. Select the five digits in order. An alternative is SmartThings → this TV → Remote → 123/keypad. Do not instruct them to open the hidden service menu.

In the Developer Mode popup, enable the mode, enter this computer's current local IPv4 address as the Host PC address, save, and restart the TV. Get the TV address from Settings → Connection/General → Network → Network Status → IP Settings. Follow [Samsung's TV connection guide](https://developer.samsung.com/smarttv/develop/getting-started/using-sdk/tv-device.html).

Use `setup.py connect --tv-ip <their-TV-address>`. The helper checks SDB's output as well as its exit code. “Already connected” and a cached device list are not proof that an off TV is reachable. A successful real install/launch is a stronger check.

If the connection fails, check that the TV is on and both devices share a network that permits device communication. Resident/guest Wi-Fi can isolate clients even on the same subnet or account. A phone hotspot may help, but verify both devices' leases and local reachability. Do not scan unrelated apartment devices or disable the firewall as a blanket fix. Never copy the reference owner's addresses; there are no universal hotspot addresses.

Save the computer's existing IP/DNS configuration before any temporary change. If DHCP fails on a hotspot, obtain its actual gateway, subnet and unique address information before proposing a temporary static address. Restore the original networking after device work.

## 4. Create the person's Samsung TV certificate

Open Tizen Certificate Manager. Create a **Samsung → TV** profile, conveniently named `CalmHome`, with a new author certificate and a Public distributor certificate. Include this TV's DUID. The person completes new passwords, Samsung login and terms privately. Never ask for their certificate password in chat or reuse another person's certificate.

Keep the TV on and connected during device inclusion. If an old Java window's automation times out, explain the exact current screen and guide the person through that screen; do not create duplicate profiles repeatedly. [Samsung certificate instructions](https://developer.samsung.com/smarttv/develop/tools/additional-tools/vscode/creating-certificates.html).

## 5. Optional live artwork

The repository's TMDB key is blank. If the person wants recommendations, help them obtain their own non-commercial developer key at [TMDB](https://developer.themoviedb.org/docs/getting-started). For its application URL, the project URL is `https://github.com/Goy2Joy/calm-home`.

Have the person enter it privately into a local environment variable named `CALM_TMDB_KEY`, then run `setup.py configure --tmdb-env CALM_TMDB_KEY`. Do not print it, put it in command arguments, commit it, or upload a personal signed build. `.setup/config.json` is ignored by Git. The TV app includes TMDB attribution under About & credits.

## 6. Build, sign and upload

Run, with this person's address and profile:

```text
python3 setup.py build --profile CalmHome
python3 setup.py install --tv-ip <TV_IP>
python3 setup.py launch --tv-ip <TV_IP>
```

Use `py -3` on Windows. An existing SDK outside the default location can be supplied before the action: `setup.py --sdk <directory> doctor`. The build's entry point stays `CalmHome01.Home`; its own generated files live under `.setup/`. If an existing Calm Home installation has a different author certificate, stop and recover the correct profile instead of uninstalling it or weakening signing.

Installation errors must stay errors. Do not fall back to preview/demo apps on a real TV or claim success from a package file existing on the computer. Keep desktop preview results separate from TV results.

## 7. Verify on the actual TV

Have the person confirm the visible interface and test two installed streaming apps, Samsung Apps under All Apps, Samsung Home, TV Settings, Back, and an actual HDMI source. Check arrow/Select navigation and saved preferences after reopening.

Resume Watching starts empty. Opening a title from Explore/Movies/Shows adds it locally; reopening its card launches that provider app. It does not retrieve provider watch history, episodes, or progress. Do not manufacture progress bars or playback claims.

Preview the aerial photo saver in Home Settings. Its first remote press wakes it. Leave it running longer than the TV's normal saver timeout to check for an overlay, then verify the native saver still works after leaving the app. If suppression fails, the custom saver stays off so two savers do not stack. Report unperformed long-idle checks as pending.

## 8. Optional physical Home and startup integration

Only continue if the person wants it and explicitly authorizes temporary root after reviewing a concrete recovery plan. Existing authorization for this same TV/scope persists; do not repeatedly request it. Read [the advanced guide](docs/advanced-home.md) first.

These operations are guarded for the single exact reference model/firmware profile. A different TV or firmware requires a new read-only compatibility review, not bypassing the guards. Normal app installation can still be useful without root. Do not claim any root path is universal.

## 9. Finish cleanly

If advanced work was done, verify each root session closed, staging was cleaned, monitored system-file hashes stayed unchanged, and the dedicated SDK helper was removed. Save recovery records locally for the owner.

Close idle Tizen Studio/Certificate Manager windows before stopping SDB, because they can restart its background server. Run `setup.py disconnect --tv-ip <TV_IP>` and do not run `sdb devices` afterward (that restarts the server). Verify it stopped.

Restore temporary computer IP/DNS settings and reconnect the person's usual saved network. Confirm automatic addressing and actual HTTPS internet access. Do not leave a hotspot-specific static address on apartment Wi-Fi. The TV can use its normal internet network after setup; Home/startup do not depend on keeping the computer or root agent running.

Summarize installed app version, physical Home behavior, stock rollback, standby/wake, cold restart, long saver test, and any remaining limitation separately. Never publish `.setup/`, certificates, keys, personal signed WGT files, network details, recovery logs or photos of the person's room.
