#!/usr/bin/env python3
"""
Convert all configs/**/*.yaml → configs/**/*.json

Run once on the developer machine before installing the Remote Script.
Requires: pip install pyyaml

Usage:
    python scripts/convert_configs.py
"""

import os
import sys
import json
import glob


def convert(yaml_path: str, json_path: str):
    try:
        import yaml
    except ImportError:
        print("ERROR: PyYAML not installed. Run: pip install pyyaml", file=sys.stderr)
        sys.exit(1)

    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)

    with open(json_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"  {yaml_path} → {json_path}")


def main():
    script_dir  = os.path.dirname(os.path.abspath(__file__))
    configs_dir = os.path.join(script_dir, "..", "configs")

    pattern = os.path.join(configs_dir, "**", "*.yaml")
    yaml_files = glob.glob(pattern, recursive=True)

    if not yaml_files:
        print("No YAML files found in configs/")
        return

    print(f"Converting {len(yaml_files)} YAML file(s)...")
    for yaml_path in sorted(yaml_files):
        json_path = yaml_path.replace(".yaml", ".json")
        convert(yaml_path, json_path)

    print("Done.")


if __name__ == "__main__":
    main()
