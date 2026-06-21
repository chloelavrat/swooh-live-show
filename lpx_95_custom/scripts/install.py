#!/usr/bin/env python3
"""
Install lpx_95_custom into Ableton's Remote Scripts directory.

By default the script installs into Ableton's User Library, which is
user-writable (no sudo) and survives Ableton updates:

    ~/Music/Ableton/User Library/Remote Scripts/lpx_95_custom

Usage:
    python scripts/install.py
    python scripts/install.py --user-library "/custom/User Library"
    python scripts/install.py --into-app                       # legacy: inside the .app bundle
    python scripts/install.py --into-app --ableton-path "/Applications/Ableton Live 12.app"

The script:
  1. Checks that JSON configs exist (aborts if convert_configs.py hasn't been run).
  2. Copies lpx_95_custom/ into the target Remote Scripts directory.
  3. Prints a reminder to restart Ableton and enable the script.
"""

import os
import sys
import shutil
import argparse
import glob

DEFAULT_ABLETON_PATHS = [
    "/Applications/Ableton Live 12 Suite.app",
    "/Applications/Ableton Live 12 Standard.app",
    "/Applications/Ableton Live 12 Intro.app",
    "/Applications/Ableton Live 11 Suite.app",
    "/Applications/Ableton Live 11 Standard.app",
    "/Applications/Ableton Live 11 Intro.app",
    "/Applications/Ableton Live.app",
]

REMOTE_SCRIPTS_SUBPATH = "Contents/App-Resources/MIDI Remote Scripts"

DEFAULT_USER_LIBRARY = os.path.expanduser("~/Music/Ableton/User Library")


def find_ableton(given: str = None) -> str:
    if given:
        return given
    for path in DEFAULT_ABLETON_PATHS:
        if os.path.isdir(path):
            return path
    return None


def resolve_dest_root(args) -> str:
    """Return the 'Remote Scripts' directory to install into (created if needed)."""
    if args.into_app:
        ableton_app = find_ableton(args.ableton_path)
        if not ableton_app:
            print("ERROR: Could not find Ableton Live. Pass --ableton-path explicitly.")
            sys.exit(1)
        dest_root = os.path.join(ableton_app, REMOTE_SCRIPTS_SUBPATH)
        if not os.path.isdir(dest_root):
            print(f"ERROR: Remote Scripts directory not found at: {dest_root}")
            sys.exit(1)
        return dest_root

    # Default: User Library (user-writable, survives app updates).
    dest_root = os.path.join(args.user_library, "Remote Scripts")
    os.makedirs(dest_root, exist_ok=True)
    return dest_root


def main():
    parser = argparse.ArgumentParser(description="Install LPX95Custom Remote Script")
    parser.add_argument("--ableton-path", default=None,
                        help="Path to Ableton Live .app (only with --into-app)")
    parser.add_argument("--into-app", action="store_true",
                        help="Install inside the Ableton .app bundle (legacy; may need sudo)")
    parser.add_argument("--user-library", default=DEFAULT_USER_LIBRARY,
                        help="Ableton User Library path (default: ~/Music/Ableton/User Library)")
    args = parser.parse_args()

    script_dir   = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    src_dir      = project_root   # lpx_95_custom/

    # 1. Check JSON configs exist
    yaml_files = glob.glob(os.path.join(project_root, "configs", "**", "*.yaml"), recursive=True)
    for yaml_path in yaml_files:
        json_path = yaml_path.replace(".yaml", ".json")
        if not os.path.isfile(json_path):
            print(f"ERROR: Missing JSON for {yaml_path}")
            print("Run: python scripts/convert_configs.py")
            sys.exit(1)

    # 2. Resolve destination
    dest_root = resolve_dest_root(args)
    dest_dir = os.path.join(dest_root, "lpx_95_custom")

    # 3. Copy
    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)
    shutil.copytree(
        src_dir,
        dest_dir,
        ignore=shutil.ignore_patterns("*.pyc", "__pycache__", "tests", "scripts", ".git"),
    )

    print(f"Installed to: {dest_dir}")
    print()
    print("Next steps:")
    print("  1. Open Ableton Live.")
    print("  2. Preferences → MIDI → Control Surface → select 'lpx_95_custom'.")
    print("  3. Set Input/Output to your Launchpad X.")
    print("  4. Done.")


if __name__ == "__main__":
    main()
