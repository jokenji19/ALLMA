# Android voice sources — ALLMA 0.9.1

The APK includes the ARM64 native runtime from the official `sherpa-onnx-static-link-onnxruntime-1.12.20.aar`. ALLMA removes the unused ABIs; it does not modify the included ARM64 shared library or the Java/Kotlin classes. The original AAR SHA-256 is `c8a88a8390ea699b24c49a31c56e8b2e3515c5cd5a2a49f8555a3b3fd68d253a`.

ALLMA's own source retains its MIT license. The APK includes GPL-3.0-or-later eSpeak NG, and distribution of the combined binary is subject to that license and the other components' applicable notices. Full license texts are included under `assets/web/licenses/`.

## Downloadable sources

The [0.9.1 release](https://github.com/jokenji19/ALLMA/releases/tag/v0.9.1) supplies:

- ALLMA application sources at tag `v0.9.1`, including the Android glue, native integration, build configuration and recipes.
- `ALLMA-0.9.1-voice-sources.tar.gz`: upstream source snapshots and original build scripts for sherpa-onnx 1.12.20 and its pinned source dependencies. `SOURCE_MANIFEST.json` records each source URL, hash and selecting recipe. This source archive contains no model weights, personal audio or app state.
- Checksums in `SHA256SUMS.txt`.

Important pinned revisions include:

- sherpa-onnx: tag `v1.12.20`, source archive SHA-256 `1fdd05cd2552875a2d9dae13e415447ef422d939778b89be0bc4ed83ea2b9aef`.
- eSpeak NG fork: `csukuangfj/espeak-ng`, commit `f6fed6c58b5e0998b8e68c6610125e2d07d595a7`, selected by `cmake/espeak-ng-for-piper.cmake`.
- piper-phonemize fork: `csukuangfj/piper-phonemize`, commit `78a788e0b719013401572d70fef372e77bff8e43`, selected by `cmake/piper-phonemize.cmake`.
- ONNX Runtime: version `1.17.1`, selected by the upstream ARM64 Android build script. Its original sources, license and build files are included.
- The other source archives selected by sherpa-onnx's CMake recipes are included, including sources for optional upstream targets. Inclusion does not mean ALLMA calls all those targets.

## Build and local modification

1. Extract the sherpa-onnx source archive. The complete Android build and AAR packaging instructions and scripts are in that source tree; refer to `build-android-arm64-v8a.sh`, `android/` and `.github/workflows/` at the pinned revision.
2. Extract the dependency source archives. Preserve their license and notice files. CMake's `FETCHCONTENT_SOURCE_DIR_<DEPENDENCY>` overrides can point FetchContent dependencies to these local trees instead of downloading again. The manifest identifies which upstream recipe selects each archive.
3. Configure the Android NDK and build the ARM64 runtime with `BUILD_SHARED_LIBS=OFF` and JNI/TTS enabled, following the upstream script. The upstream script documents the static ONNX Runtime input and Android platform selection. Build the Java/Kotlin AAR using the upstream Android project and build recipes.
4. To reproduce ALLMA's ABI-only reduction from the official AAR, retain `AndroidManifest.xml`, `classes.jar`, metadata and `jni/arm64-v8a/`; omit the other `jni/` ABI directories. No ARM64 code patch is required.
5. Place the resulting archive at `libs/sherpa-onnx-1.12.20-arm64.aar`. ALLMA's `buildozer.spec` adds the Java helpers in `libs/android_src/`, Kotlin 1.9.25 and the AAR. Regenerate the embedded application with `python3 pack_brain.py`, then run `buildozer android debug`. Verify the artifact with `python3 tools/verify_android_apk.py <apk>`.

`tools/prepare_voice_sources.py` regenerates the source bundle inputs and checks the hashes supplied by the pinned CMake recipes. It downloads sources without building or executing them. Source modifications and rebuilt binaries should retain applicable licenses and identify their changes. The debug APK permits local replacement and installation using the ordinary Android development tools; ALLMA has no application-level signature check restricting a modified voice runtime.

The optional Kokoro INT8 model pack is downloaded separately, has its own notices and hashes, and is not an included native source dependency. The model and voice data remain governed by their respective licenses.
