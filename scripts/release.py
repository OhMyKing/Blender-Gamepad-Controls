import os
import pathlib
import subprocess
import zipfile
import build_wheel


project_path = pathlib.Path(__file__).parent.parent.absolute()


def do_pack(wheel_dir: pathlib.Path, dist_path: pathlib.Path):
    branch = "main"
    packing_file = f"BGC.zip"
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

    build_wheel.download_all(str(wheel_dir))
    output_file = do_pack(wheel_dir, dist_path)
    print(f"Output file localed at {output_file}")


if __name__ == "__main__":
    main()
