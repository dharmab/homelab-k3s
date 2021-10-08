#!/usr/bin/env python3
"""Hack script to make kubeconfig work with Vagrant VM"""

import argparse

import yaml
import pathlib


def main() -> None:
    """
    Update the given kubeconfig's server URL
    """
    parser = argparse.ArgumentParser(
        description="Update admin kubeconfig for external use"
    )
    parser.add_argument(
        "--kubeconfig",
        help="Path to admin kubeconfig file",
        metavar="FILE",
        required=True,
    )
    args = parser.parse_args()

    kubeconfig_path = pathlib.Path(args.kubeconfig)
    with open(kubeconfig_path, encoding="utf-8") as path:
        kubeconfig = yaml.safe_load(path)

    for cluster in kubeconfig["clusters"]:
        cluster["cluster"]["server"] = "https://127.0.0.1:6443"

    with open(kubeconfig_path, encoding="utf-8", mode='w') as path:
        yaml.dump(kubeconfig, path)


if __name__ == "__main__":
    main()
