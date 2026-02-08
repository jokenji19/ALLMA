# Host toolchain for macOS - compiles vulkan-shaders-gen natively
# This file overrides Android toolchain for ExternalProject host builds

# Force native macOS compilation - this is the key setting
set(CMAKE_SYSTEM_NAME Darwin)
set(CMAKE_SYSTEM_PROCESSOR arm64)

# Use Apple's standard compilers (not NDK versions)
set(CMAKE_C_COMPILER "/usr/bin/clang")
set(CMAKE_CXX_COMPILER "/usr/bin/clang++")

# Target native macOS ARM64 (NOT Android!)
set(CMAKE_C_COMPILER_TARGET "arm64-apple-macos")
set(CMAKE_CXX_COMPILER_TARGET "arm64-apple-macos")

# Completely reset all flags (remove Android contamination)
set(CMAKE_C_FLAGS "-O2" CACHE STRING "" FORCE)
set(CMAKE_CXX_FLAGS "-O2 -std=c++17" CACHE STRING "" FORCE)
set(CMAKE_EXE_LINKER_FLAGS "" CACHE STRING "" FORCE)
set(CMAKE_SHARED_LINKER_FLAGS "" CACHE STRING "" FORCE)

# Unset all Android-specific variables
unset(ANDROID CACHE)
unset(ANDROID_ABI CACHE)
unset(ANDROID_PLATFORM CACHE)
unset(CMAKE_ANDROID_NDK CACHE)
unset(CMAKE_TOOLCHAIN_FILE CACHE)

# Don't inherit search paths from cross-compile environment
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE NEVER)

# Build settings
set(CMAKE_BUILD_TYPE Release)
