#!/usr/bin/env python3
"""Build and ad-hoc sign the app using only macOS Command Line Tools."""

from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"


def read_plist(path):
    return plistlib.loads(path.read_bytes())


def run(*command):
    subprocess.run(command, check=True)


def build():
    if sys.platform != "darwin":
        raise SystemExit("This project requires macOS.")
    for tool in ("xcrun", "codesign"):
        if not shutil.which(tool):
            raise SystemExit(f"Missing {tool}; install Command Line Tools with xcode-select --install.")

    app_info = read_plist(ROOT / "resources/App-Info.plist")
    extension_info = read_plist(ROOT / "resources/Extension-Info.plist")
    BUILD.mkdir(exist_ok=True)
    destination = BUILD / (app_info["CFBundleName"] + ".app")
    # Only replace our own generated bundle, never an unrelated app or symlink.
    if destination.is_symlink() or (destination.exists() and (
        not (destination / "Contents/Info.plist").is_file()
        or read_plist(destination / "Contents/Info.plist").get("CFBundleIdentifier")
        != app_info["CFBundleIdentifier"]
    )):
        raise SystemExit(f"Refusing to replace an unrelated build output: {destination}")

    with tempfile.TemporaryDirectory(prefix=".stage-", dir=BUILD) as temporary:
        app = Path(temporary) / destination.name
        extension = app / "Contents/PlugIns/ITermFinderExtension.appex"
        targets = (
            (app, "App", app_info, "App.m", ("Cocoa",)),
            (extension, "Extension", extension_info, "FinderExtension.m", ("Cocoa", "FinderSync")),
        )
        for bundle, info_name, info, source, frameworks in targets:
            (bundle / "Contents/MacOS").mkdir(parents=True)
            shutil.copy2(ROOT / f"resources/{info_name}-Info.plist", bundle / "Contents/Info.plist")
            command = [
                "xcrun", "clang", "-fobjc-arc", "-O2", "-Wall", "-Wextra",
                f"-mmacosx-version-min={info['LSMinimumSystemVersion']}",
                str(ROOT / "src" / source),
                "-o", str(bundle / "Contents/MacOS" / info["CFBundleExecutable"]),
            ]
            for framework in frameworks:
                command.extend(("-framework", framework))
            run(*command)

        run("codesign", "--force", "--sign", "-", "--entitlements",
            str(ROOT / "resources/Extension.entitlements"), str(extension))
        run("codesign", "--force", "--sign", "-", str(app))
        run("codesign", "--verify", "--deep", "--strict", str(app))
        if destination.exists():
            shutil.rmtree(destination)
        app.rename(destination)
    print(destination)
    return destination


if __name__ == "__main__":
    build()
