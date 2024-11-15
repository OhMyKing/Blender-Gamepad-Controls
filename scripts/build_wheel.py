import sys
import os
import subprocess


def download_dep(dep_name: str, target_dir: str):
    args = [
        sys.executable,
        "-m",
        "pip",
        "wheel",
        dep_name,
        "-w",
        target_dir,
    ]
    subprocess.run(args)


deps = ["inputs==0.5"]


def download_all(wheel_dir: str):
    for dep in deps:
        download_dep(dep, wheel_dir)
