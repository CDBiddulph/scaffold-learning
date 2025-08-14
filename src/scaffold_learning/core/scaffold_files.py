"""Utilities for saving scaffold files."""

import shutil
from pathlib import Path
from scaffold_learning.core.data_structures import ScaffoldResult
from scaffold_learning.core.xml_utils import write_xml_file


def save_scaffold(scaffold_dir: Path, result: ScaffoldResult) -> None:
    """Save scaffold files to a directory.

    Args:
        scaffold_dir: Directory to save scaffold files to
        result: ScaffoldResult containing code and metadata

    Raises:
        OSError: If scaffold cannot be saved
    """
    scaffold_dir.mkdir(parents=True, exist_ok=True)

    # Write scaffold.py
    (scaffold_dir / "scaffold.py").write_text(result.code)

    # Write metadata.xml
    write_xml_file(result.metadata.to_dict(), scaffold_dir / "metadata.xml", "metadata")
