[app]
# Battle Zone Android APK
# This project is built automatically by GitHub Actions.
title = Battle Zone
package.name = battlezone
package.domain = org.battlezone
source.dir = .
source.main = main.py
source.include_exts = py,png,jpg,jpeg,json,txt
version = 1.0.0
requirements = python3,pygame
orientation = portrait
fullscreen = 1
icon.filename = %(source.dir)s/Battle_Zone_Game_Icon_512.png

# Android settings
android.debug_artifact = apk
android.release_artifact = apk
android.minapi = 21
android.api = 33
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
