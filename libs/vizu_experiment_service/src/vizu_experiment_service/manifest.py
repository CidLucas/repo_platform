# vizu_experiment_service/manifest.py
"""Manifest loading and validation."""

from pathlib import Path

import yaml
from vizu_models import ExperimentManifest


class ManifestLoader:
    """Loads and validates experiment manifests from YAML files."""

    @staticmethod
    def load_from_file(path: str | Path) -> ExperimentManifest:
        """
        Load an experiment manifest from a YAML file.

        Args:
            path: Path to the YAML manifest file

        Returns:
            Validated ExperimentManifest

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the manifest is invalid
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Manifest file not found: {path}")

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return ExperimentManifest(**data)

    @staticmethod
    def load_from_dict(data: dict) -> ExperimentManifest:
        """
        Load an experiment manifest from a dictionary.

        Args:
            data: Dictionary with manifest data

        Returns:
            Validated ExperimentManifest
        """
        return ExperimentManifest(**data)

    @staticmethod
    def load_from_yaml_string(yaml_string: str) -> ExperimentManifest:
        """
        Load an experiment manifest from a YAML string.

        Args:
            yaml_string: YAML-formatted string

        Returns:
            Validated ExperimentManifest
        """
        data = yaml.safe_load(yaml_string)
        return ExperimentManifest(**data)

    @staticmethod
    def save_to_file(manifest: ExperimentManifest, path: str | Path) -> None:
        """
        Save a manifest to a YAML file.

        Args:
            manifest: The manifest to save
            path: Destination path
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(
                manifest.model_dump(mode="json", exclude_none=True),
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )
