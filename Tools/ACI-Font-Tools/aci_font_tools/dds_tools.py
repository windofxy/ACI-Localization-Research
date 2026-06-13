from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from PIL import Image


def get_texconv_path() -> Path:
    return Path(__file__).resolve().parents[1] / "thirdparty" / "texconv.exe"


def save_image_as_game_dds(image: Image.Image, output_path: str | Path) -> Path:
    texconv_path = get_texconv_path()
    if not texconv_path.is_file():
        raise FileNotFoundError(f"texconv.exe was not found: {texconv_path}")

    target_path = Path(output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="aci_font_tools_") as temp_dir_text:
        temp_dir = Path(temp_dir_text)
        temp_png_path = temp_dir / f"{target_path.stem}.png"
        image.save(temp_png_path)

        command = [
            str(texconv_path),
            "-nologo",
            "-y",
            "-ft",
            "dds",
            "-f",
            "DXT5",
            "-m",
            "1",
            "-dx9",
            "-o",
            str(target_path.parent),
            str(temp_png_path),
        ]
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            output = "\n".join(value for value in [completed.stdout.strip(), completed.stderr.strip()] if value)
            raise RuntimeError(f"texconv failed while creating DDS:\n{output}".rstrip())

        generated_path = target_path.parent / f"{temp_png_path.stem}.dds"
        if not generated_path.is_file():
            generated_candidates = sorted(target_path.parent.glob(f"{temp_png_path.stem}.*"))
            raise FileNotFoundError(
                "texconv did not produce the expected DDS file. "
                f"Looked for {generated_path} and found {generated_candidates!r}"
            )

        if generated_path != target_path:
            if target_path.exists():
                target_path.unlink()
            generated_path.replace(target_path)

    return target_path


def build_game_dds_bytes(image: Image.Image) -> bytes:
    with tempfile.TemporaryDirectory(prefix="aci_font_tools_dds_") as temp_dir_text:
        temp_dir = Path(temp_dir_text)
        dds_path = temp_dir / "atlas.dds"
        save_image_as_game_dds(image, dds_path)
        return dds_path.read_bytes()
