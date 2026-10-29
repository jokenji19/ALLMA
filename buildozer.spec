[app]

# (str) Title of your application
title = ALLMA AI

# (str) Package name
package.name = allma_prime

# (str) Package domain (needed for android/ios packaging)
package.domain = org.allma

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,json,txt,zip,so,bin,html,css,js,woff2

# (list) List of inclusions using pattern matching
# Build 148: Explicit Code Blob Include
#source.include_patterns = assets/*,main.py,icon.png,code_blob.py,logo.png,allma_model,libs,libllama.so,payload.png

# (list) Source files to exclude (let empty to not exclude anything)
source.exclude_exts = spec

# (list) List of directory to exclude (let empty to not exclude anything)
source.exclude_dirs = tests, bin, venv, test_data, test_documents, tools, .github, .git, .buildozer, unpacked_brain, tmp_llama_check, allma_model/tests, models, Library, htmlcov, _quarantine, incremental_cache, data, logs, benchmarks/reports, libs/recipes, libs_custom, libs/native_backend/hexagon

# (list) List of exclusions using pattern matching
# Removed *.txt exclusion to allow requirements.txt
source.exclude_patterns = license,images/*/*.jpg,tools/*,*.pyc,*.md,*.bak,allma_model.zip,allma_model/allma_diary.json,personality_state.json,beta_test_conversations.json,allma.db,allma_memory.json,conversation_history.db,conversation_history.db.init.lock,allma_settings.json,model_binding.json,notifications.json,allma_modules.db,answer_recall.json,answer_recall.db,answer_recall.db.init.lock,incremental_cache/knowledge_states.json,incremental_cache/knowledge_states.db,incremental_cache/knowledge_states.db.init.lock,data/allma_vectors.db,data/dream_journal.json,data/dream_journal.json.pending.json,data/dream_journal.json.processed.json,message_delivery.json,data/dream_journal.json.reviews.db,cognitive_state.json,allma_diary.json

# (str) Application versioning (method 1)
version = 0.9.1.1
android.numeric_version = 102593

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
# NOTE: Heavy ML libraries (torch, transformers, llama-cpp-python) and numpy are excluded
# These will be downloaded# (list) Application requirements
# Build 136: Full Restoration (Standard + Graphics + Math)
requirements = python3==3.11.8,hostpython3==3.11.8,kivy==2.3.1,sqlite3,requests,plyer,kivymd==1.2.0,pillow,numpy,llamacpp_android,opencl_link,diskcache,typing_extensions,jinja2,markupsafe,pytz

# (str) Python for android branch to use, if not master, useful to try new features
p4a.branch = develop

# (str) Custom source folders for requirements
# Sets custom source for any requirements with recipes
# requirements.source.kivy = ../../kivy
# p4a.local_recipes = ./recipes

# (list) Garden requirements
#garden_requirements =

# (str) Presplash of the application
presplash.filename = %(source.dir)s/assets/android/presplash.png

# (str) Icon of the application
icon.filename = icon.png
# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (list) List of service to declare
services = allma_brain:service.py:foreground:foregroundServiceType=dataSync

#
# Android specific
#

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (str) SoftInputMode (adjustResize: standard behavior, backed by manual padding if needed)
android.softinput_mode = adjustPan

# (string) Presplash background color (for android)
# Supported formats are: #RRGGBB #AARRGGBB or one of the following names:
# red, blue, green, black, white, gray, cyan, magenta, yellow, lightgray,
# darkgray, grey, lightgrey, darkgrey, aqua, fuchsia, lime, maroon, navy,
# olive, purple, silver, teal.
android.presplash_color = #FAF9F5

# (list) Permissions
android.add_src = libs/android_src
android.add_aars = libs/sherpa-onnx-1.12.20-arm64.aar, libs/allma-native-manifest.aar
android.gradle_dependencies = org.jetbrains.kotlin:kotlin-stdlib:1.9.25
android.add_gradle_repositories = flatDir { dirs 'libs' }
android.add_resources = assets/android/drawable/ic_allma_notification.xml:drawable/ic_allma_notification.xml, assets/android/xml/allma_backup_rules.xml:xml/allma_backup_rules.xml, assets/android/xml/allma_extraction_rules.xml:xml/allma_extraction_rules.xml
android.add_assets = startup_ui.py:startup/startup_ui.py, assets/web/images/startup-connection.png:startup/assets/web/images/startup-connection.png, assets/web/fonts/Inter-Regular.ttf:startup/assets/web/fonts/Inter-Regular.ttf, assets/web/fonts/Inter-LICENSE.txt:startup/assets/web/fonts/Inter-LICENSE.txt
android.extra_manifest_application_arguments = libs/backup_application.xml
android.extra_manifest_xml = libs/voice_manifest.xml

android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,CAMERA,RECORD_AUDIO,WAKE_LOCK,VIBRATE,ACCESS_NETWORK_STATE,MODIFY_AUDIO_SETTINGS,BLUETOOTH,BLUETOOTH_CONNECT,FOREGROUND_SERVICE,POST_NOTIFICATIONS,FOREGROUND_SERVICE_DATA_SYNC

# (int) Target Android API, should be as high as possible.
android.api = 34

# (int) Minimum API your APK will support.
android.minapi = 24

# (int) Android SDK version to use
#android.sdk = 20

# (str) Android NDK version to use
android.ndk = 27d
android.sdk_path = ./.buildozer_local/android/platform/android-sdk
android.ndk_path = ./.buildozer_local/android/platform/android-ndk-r27d

# (str) Android Build Tools version to use (force stable version)
android.build_tools_version = 34.0.0

# (bool) Use --private data storage (True) or --dir public storage (False)
#android.private_storage = True

# (str) Android entry point, default is ok for Kivy-based app
#android.entrypoint = org.kivy.android.PythonActivity

# (list) Pattern to exclude from the user directory
#android.skip_update_options = path/to/exclude/*

# (list) The Android archs to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
android.archs = arm64-v8a

# (bool) enables Android auto backup feature (Android API >= 23)
android.allow_backup = True

# (list) Android libraries to add to the libs/arm64-v8a directory
#android.add_libs_arm64 = libs/lib-arm64/libhelloworld.so

# (str) XML file for the Android manifest
android.manifest = AndroidManifest.xml
#android.manifest_launch_mode = standard

# (str) XML file for the Android manifest
#android.manifest_placeholders = :

# (bool) Copy library instead of making a libpymodules.so
#android.copy_libs = 1

# (str) The directory in which python-for-android should look for your own build recipes (if any)
p4a.local_recipes = ./libs/recipes

# (str) Filename to the hook for p4a
p4a.hook = ./libs/android_build_hook.py

# (str) Bootstrap to use for android builds
# p4a.bootstrap = sdl2

# (int) Port number to specify an explicit --port= p4a argument (eg for bootstrap flask)
#p4a.port =

# (str) Env vars to export for the build process
# PERFORMANCE OPTIMIZED BUILD (OpenCL):
# EXPERIMENTAL (2026-02-02 04:00): Switched from Vulkan to OpenCL
# Reason: Vulkan unstable/slow on Adreno GPUs (0.6-6 tok/s)
#         OpenCL optimized for Qualcomm Snapdragon (15-40 tok/s)
# - OPENCL: GPU acceleration via Qualcomm-optimized backend
# - OPENMP: CPU multithreading (8 cores)
# - NATIVE: ARM64 NEON optimizations
# Expected: 3-4x speedup vs CPU-only
# Rollback: buildozer.spec.backup_vulkan if fails
# env_vars = CMAKE_ARGS="-DGGML_OPENCL=ON -DGGML_OPENMP=ON -DGGML_NATIVE=ON -DGGML_PERF=ON -DANDROID_PLATFORM=android-24",FORCE_CMAKE=1,CPATH="/Users/erikahu/ALLMA/ALLMA_V4/.buildozer/android/platform/android-ndk-r25b/toolchains/llvm/prebuilt/darwin-x86_64/sysroot/usr/include"
# CLEAN ENV FOR RECIPE CONTROL
env_vars = FORCE_CMAKE=1,PYTHONUSERBASE=./.buildozer_local/pythonuserbase,PIP_CACHE_DIR=./.buildozer_local/pipcache

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
build_dir = ./.buildozer_local

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
