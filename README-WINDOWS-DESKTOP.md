# Lumo Code Windows Desktop Installer (Windows 10/11 x64)

This package adds a Windows setup executable build pipeline while keeping the existing Lumo Code terminal UI/agent source intact.

## User experience

1. Download and run `LumoCode-Setup.exe` from the GitHub Actions artifact or GitHub Release.
2. Setup installs the launcher into `%LOCALAPPDATA%\Programs\LumoCode` and the downloaded source/runtime/Bash components under `%LOCALAPPDATA%\LumoCode` (no administrator elevation for Lumo itself).
3. The setup post-install action fetches the default branch source archive from `https://github.com/alfar988/Lumo-code`, provisions a Python embeddable runtime and Git for Windows Bash if missing, and opens Lumo's existing terminal UI.
4. The Start Menu/Desktop shortcut starts the installed source in a fresh terminal window. Lumo configuration remains in `%USERPROFILE%\.lumo`; projects use `%USERPROFILE%\workspace`.

The first install needs an internet connection. The OpenRouter API key is still supplied by each user inside Lumo; it is not embedded in this installer.

## Build the setup EXE using GitHub Actions

Copy these files into the repository root:

- `windows-desktop/bootstrap.py`
- `windows-desktop/LumoCode.iss`
- `.github/workflows/build-lumo-windows.yml`

Commit and push them. On GitHub, open **Actions → Build Lumo Code Windows installer → Run workflow**. The resulting `LumoCode-Setup.exe` is downloadable under Artifacts. To attach it automatically to a Release, push a tag such as `desktop-v1.0.0`.

## Technical notes

- This is a bootstrap/setup EXE, not a Python one-file bundle of the whole agent. It retrieves the current public repository source when first installed. Lumo itself runs with a locally bundled Python 3.13.17 embeddable runtime.
- Git for Windows is installed per-user if Bash is not detected because the current agent's shell tool expects Bash/sh. Installer options use the Git for Windows documented silent flags.
- x64 Windows 10/11 only in this initial package. ARM64 Windows is not yet packaged.
- The current upstream codebase was originally documented for Termux/Linux/macOS and WSL on Windows. This installer provisions Bash, but it does not certify every generated shell command or all agent features as Windows-native. Windows-specific compatibility testing is still required before calling this a production-ready release.
- GitHub Actions runs on Windows to build the real `.exe`; this source bundle does not contain a prebuilt Windows binary.
