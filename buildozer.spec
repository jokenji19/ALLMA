[app]

# (str) Title of your application
title = ALLMA AI

# (str) Package name
package.name = allma

# (str) Package domain (needed for android/ios packaging)
package.domain = org.allma

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,json,txt,zip

# (list) List of inclusions using pattern matching
# Build 97 Fix: Removed libs/* and Model/* to prevent conflict with exclude_dirs
source.include_patterns = assets/*,images/*,ui/*,allma_data/*

# (list) Source files to exclude (let empty to not exclude anything)
source.exclude_exts = spec

# (list) List of directory to exclude (let empty to not exclude anything)
source.exclude_dirs = tests, bin, venv, libs/Model, Model

# (list) List of exclusions using pattern matching
source.exclude_patterns = license,images/*/*.jpg,tools/*,*.pyc,*.txt,*.md

# (str) Application versioning (method 1)
version = 0.1

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
# NOTE: Heavy ML libraries (torch, transformers, llama-cpp-python) and numpy are excluded
# These will be downloaded at runtime by the app
# Build 125: Plan K - Golden Revert (Restore Build 113 Config)
requirements = python3,kivy,kivymd,sqlite3,pillow,requests,plyer,numpy

# (str) Python for android branch to use, if not master, useful to try new features
# p4a.branch = develop

# (str) Custom source folders for requirements
# Sets custom source for any requirements with recipes
# requirements.source.kivy = ../../kivy
# p4a.local_recipes = ./recipes

# (list) Garden requirements
#garden_requirements =

# (str) Presplash of the application
#presplash.filename = %(source.dir)s/data/presplash.png

# (str) Icon of the application
#icon.filename = %(source.dir)s/data/icon.png

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (list) List of service to declare
#services = NAME:ENTRYPOINT_TO_PY,NAME2:ENTRYPOINT2_TO_PY

#
# Android specific
#

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (string) Presplash background color (for android)
# Supported formats are: #RRGGBB #AARRGGBB or one of the following names:
# red, blue, green, black, white, gray, cyan, magenta, yellow, lightgray,
# darkgray, grey, lightgrey, darkgrey, aqua, fuchsia, lime, maroon, navy,
# olive, purple, silver, teal.
android.presplash_color = #1E1E1E

# (list) Permissions
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,CAMERA,RECORD_AUDIO,WAKE_LOCK,VIBRATE

# (int) Target Android API, should be as high as possible.
android.api = 34

# (int) Minimum API your APK will support.
android.minapi = 24

# (int) Android SDK version to use
#android.sdk = 20

# (str) Android NDK version to use
#android.ndk = 19b

# (str) Android Build Tools version to use (force stable version)
android.build_tools_version = 34.0.0

# (bool) Use --private data storage (True) or --dir public storage (False)
#android.private_storage = True

# (str) Android entry point, default is ok for Kivy-based app
#android.entrypoint = org.kivy.android.PythonActivity

# (list) Pattern to exclude from the user directory
#android.skip_update_options = path/to/exclude/*

# (list) The Android archs to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
# android.archs = arm64-v8a

# (bool) enables Android auto backup feature (Android API >= 23)
android.allow_backup = True

# (str) XML file for the Android manifest
#android.manifest_launch_mode = standard

# (str) XML file for the Android manifest
#android.manifest_placeholders = :

# (bool) Copy library instead of making a libpymodules.so
#android.copy_libs = 1

# (str) The Android resource to load
#android.ouya.category = GAME
#android.ouya.icon.filename = %(source.dir)s/data/ouya_icon.png

# (str) Filename to the hook for p4a
#p4a.hook =

# (str) Bootstrap to use for android builds
# p4a.bootstrap = sdl2

# (int) Port number to specify an explicit --port= p4a argument (eg for bootstrap flask)
#p4a.port =

#
# iOS specific
#

# (str) Path to a custom kivy-ios folder
#ios.kivy_ios_dir = ../kivy-ios
# (str) Name of the certificate to use for signing the debug version
# Get a list of available identities: security find-identity -v -p codesigning
#ios.codesign.debug = "iPhone Developer: <lastname> <firstname> (<hexstring>)"

# (str) Name of the certificate to use for signing the release version
#ios.codesign.release = %(ios.codesign.debug)s

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1

# (str) Path to build artifact storage, absolute or relative to spec file
# build_dir = ./.buildozer

# (str) Path to build output storage, absolute or relative to spec file
# bin_dir = ./bin

#    -----------------------------------------------------------------------------
#    List as sections
#
#    You can define all the "list" as [section:name].
#    Each line will be considered as a option to the list.
#    Let's take [app] / requirements. Instead of:
#
#    requirements = sqlite3,kivy
#
#    You can extend it in the spec file:
#
#    [app:requirements]
#    sqlite3
#    kivy
#
#    -----------------------------------------------------------------------------
#    Profiles
#
#    You can extend section / key with a profile
#    For example, you want to deploy a debug version of your application as
#    usually, but you want a release version to be adjusted to the print
#    anoying message "Hello world" every time the application starts.
#
#    [app@debug]
#    title = My Application Debug
#
#    [app@release]
#    title = My Application
#
#    Then, invoke buildozer with the "profile" target:
#
#    buildozer --profile debug android debug
