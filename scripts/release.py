import os
import pathlib
import subprocess
import zipfile
import sys
import platform
import build_wheel

platform_name_alias = {
    "Windows": "win",
    "Linux": "linux",
    "Darwin": "macOS"
}
blender_matrix = {"310": "blender3.3-4.0", "311": "blender4.1"}

project_path = pathlib.Path(__file__).parent.parent.absolute()


def do_pack(wheel_dir: pathlib.Path, dist_path: pathlib.Path, blender_version: str, platform_key: str):
    branch = "main"
    packing_file = f"BGC-{blender_version}-{platform_key}.zip"
    print(f"Packing for {packing_file}")
    packing_file = str(dist_path.joinpath(packing_file))
    subprocess.run(
        [
            "git",
            "archive",
            "--format",
            "zip",
            "--output",
            packing_file,
            branch,
            "--prefix",
            "BGC/",
        ]
    )

    wheels = list(
        map(
            lambda x: str(wheel_dir.joinpath(x)),
            filter(lambda x: x.endswith(".whl"), os.listdir(wheel_dir)),
        )
    )
    for wheel in wheels:
        with zipfile.ZipFile(packing_file, "a") as zfile:
            zfile.write(wheel, f"BGC/wheels/{os.path.basename(wheel)}")
    return packing_file


def main():
    wheel_dir = project_path.joinpath("wheels")
    dist_path = project_path.joinpath("dist")
    print(f"Project is located at {str(project_path)}")
    if not dist_path.exists():
        print(f"Creating dist_folder at {dist_path}")
        os.mkdir(dist_path)

    assert platform.system() in platform_name_alias
    platform_key = f"{platform_name_alias[platform.system()]}_{platform.machine()}"
    python_code = f"{sys.version_info.major}{sys.version_info.minor}"
    assert python_code in blender_matrix

    build_wheel.download_all(str(wheel_dir))
    output_file = do_pack(wheel_dir, dist_path, blender_matrix[python_code], platform_key)
    print(f"Output file localed at {output_file}")


if __name__ == "__main__":
    main()
