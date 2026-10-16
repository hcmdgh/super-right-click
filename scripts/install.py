#!/usr/bin/env python3
"""Install a verified build and register its Finder extension."""

import argparse
import os
from pathlib import Path
import plistlib
import shutil
import signal
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
LSREGISTER = Path(
    "/System/Library/Frameworks/CoreServices.framework/Frameworks/"
    "LaunchServices.framework/Support/lsregister"
)
EXTENSION_RELATIVE = Path("Contents/PlugIns/ITermFinderExtension.appex")


def bundle_info(bundle):
    return plistlib.loads((bundle / "Contents/Info.plist").read_bytes())


def validate_destination(destination, expected_identifier):
    """Do not overwrite another application, a broken bundle, or a symlink."""
    if destination.is_symlink():
        raise ValueError(f"Refusing to replace a symlink: {destination}")
    if not destination.exists():
        return
    try:
        actual_identifier = bundle_info(destination).get("CFBundleIdentifier")
    except (OSError, plistlib.InvalidFileException, ValueError) as error:
        raise ValueError(f"Not a valid application bundle: {destination}") from error
    if actual_identifier != expected_identifier:
        raise ValueError(f"Refusing to overwrite another application: {destination}")


def stop_bundle_processes(bundle):
    """Stop only processes whose executable is inside this installed bundle."""
    output = subprocess.run(
        ["ps", "-axo", "pid=,comm="], check=True, capture_output=True, text=True,
    ).stdout
    prefix = str(bundle / "Contents") + "/"
    for line in output.splitlines():
        fields = line.strip().split(maxsplit=1)
        if len(fields) == 2 and fields[1].startswith(prefix):
            try:
                os.kill(int(fields[0]), signal.SIGTERM)
            except ProcessLookupError:
                pass


def run(*command):
    subprocess.run([str(part) for part in command], check=True)


def register(bundle, extension_identifier):
    run(LSREGISTER, "-f", bundle)
    run("pluginkit", "-a", bundle / EXTENSION_RELATIVE)
    run("pluginkit", "-e", "use", "-i", extension_identifier)


def install(applications_directory):
    info = plistlib.loads((ROOT / "resources/App-Info.plist").read_bytes())
    source = ROOT / "build" / (info["CFBundleName"] + ".app")
    if not source.is_dir():
        raise SystemExit("Build first: python3 scripts/build.py")
    if bundle_info(source).get("CFBundleIdentifier") != info["CFBundleIdentifier"]:
        raise SystemExit("Unexpected build bundle identifier; rebuild before installing.")
    run("codesign", "--verify", "--deep", "--strict", source)

    directory = applications_directory.expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / source.name
    validate_destination(destination, info["CFBundleIdentifier"])
    identifier = bundle_info(source / EXTENSION_RELATIVE)["CFBundleIdentifier"]

    # Stage the entire bundle before touching an existing installation.
    # Keep the previous copy until registration succeeds so a failure can roll back.
    with tempfile.TemporaryDirectory(prefix=".iterm-menu-install-", dir=directory) as temporary:
        staged = Path(temporary) / source.name
        backup = Path(temporary) / "previous.bundle"
        shutil.copytree(source, staged, symlinks=True)
        run("codesign", "--verify", "--deep", "--strict", staged)
        had_previous = destination.exists()
        installed_new = False
        try:
            if had_previous:
                run("pluginkit", "-e", "ignore", "-i", identifier)
                stop_bundle_processes(destination)
                destination.rename(backup)
            staged.rename(destination)
            installed_new = True
            register(destination, identifier)
        except Exception:
            # Only the freshly staged bundle is removed; the previous app is restored.
            if installed_new:
                shutil.rmtree(destination)
            if backup.exists():
                backup.rename(destination)
            if had_previous and destination.exists():
                register(destination, identifier)
            raise

    print(f"Installed: {destination}")
    print("If the menu is missing, enable 使用iTerm打开 in System Settings > General > Login Items & Extensions.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--applications-dir", type=Path, default=Path("/Applications"),
        help="installation directory (default: /Applications)",
    )
    args = parser.parse_args()
    try:
        install(args.applications_dir)
    except PermissionError as error:
        raise SystemExit(
            f"{error}\nTry: python3 scripts/install.py --applications-dir ~/Applications"
        ) from error
    except (ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
