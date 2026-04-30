import os
import shutil
import subprocess
from pathlib import Path


class BlenderRunner:
    def __init__(self, logger, blender_executable: str | None = None):
        self.logger = logger
        self.blender_executable = blender_executable or self._resolve_blender_executable()

    def _resolve_blender_executable(self) -> str:
        env_override = os.environ.get("BLENDER_PATH")
        if env_override:
            return env_override

        discovered = shutil.which("blender")
        if discovered:
            return discovered

        common_paths = [Path("C:/Program Files/Blender Foundation/Blender/blender.exe")]

        foundation_dir = Path("C:/Program Files/Blender Foundation")
        if foundation_dir.exists():
            versioned_installs = sorted(
                foundation_dir.glob("Blender*/blender.exe"),
                key=lambda path: path.parent.name,
                reverse=True,
            )
            common_paths.extend(versioned_installs)

        for candidate in common_paths:
            if candidate.exists():
                return str(candidate)

        raise FileNotFoundError(
            "Blender executable was not found. Install Blender or set the BLENDER_PATH environment variable."
        )

    def convert_to_vrm(self, input_path: Path, output_path: Path) -> None:
        if input_path.suffix.lower() == ".vrm":
            raise ValueError("The selected file is already a VRM file.")

        script_path = Path(__file__).with_name("blender_script.py")
        command = [
            self.blender_executable,
            "--background",
            "--python",
            str(script_path),
            "--",
            str(input_path),
            str(output_path),
        ]

        self.logger.info(f"Using Blender executable: {self.blender_executable}")
        self.logger.info("Launching Blender conversion process...")

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        assert process.stdout is not None
        output_lines = []
        for line in process.stdout:
            cleaned = line.rstrip()
            output_lines.append(cleaned)
            self.logger.info(cleaned)

        exit_code = process.wait()
        if exit_code != 0:
            combined_output = "\n".join(output_lines)
            if "VRM export operator not found in Blender" in combined_output:
                raise RuntimeError(
                    "Blender could not find the 'VRM format' add-on. Open Blender 4.4, install or enable the 'VRM format' add-on, then try conversion again."
                )
            raise RuntimeError(f"Blender conversion failed with exit code {exit_code}.")

        if not output_path.exists():
            raise RuntimeError(
                "Blender finished without creating a VRM file. Verify that the 'VRM format' add-on is installed and enabled in Blender."
            )
