[app]

# Core app metadata
title = MLBB AI Overlay
package.name = mlbb_ai_chooser
package.domain = org.ai.builds
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0.0
requirements = python3,kivy,pyjnius
android.permissions = SYSTEM_ALERT_WINDOW, FOREGROUND_SERVICE, INTERNET
android.api = 33
android.minapi = 21
orientation = landscape
android.entrypoint = main.py
android.archs = arm64-v8a

# Build system
p4a.branch = master

[buildozer]
# Leave buildozer defaults operational for a clean CI build
