BATTLE ZONE - APK BUILDER

What this ZIP contains:
- main.py = your Battle Zone game source
- Battle_Zone_Game_Icon_512.png = app icon
- buildozer.spec = Android build settings
- .github/workflows/build-apk.yml = automatic GitHub APK builder

PHONE STEPS:
1. Extract this ZIP.
2. Upload ALL files/folders inside it to your GitHub Game repository.
3. Open GitHub > Actions.
4. Select "Build Battle Zone APK".
5. Tap "Run workflow" > Run workflow.
6. Wait for the green check.
7. Open the successful run.
8. Under Artifacts, download "battle-zone-apk".
9. Extract that downloaded ZIP.
10. The .apk inside is the Android APK to install.

IMPORTANT:
- The GitHub Actions artifact is a ZIP. Extract it first.
- The old 11-12 KB game.apk from the WebAssembly artifact is NOT a valid Android APK.
- The first Android build can take a while because Android SDK/NDK build tools are downloaded.
- If the workflow shows a red X, send a screenshot of the failed step/log.
