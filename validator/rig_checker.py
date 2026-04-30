from dataclasses import dataclass, field
from pathlib import Path

from validator.blendshape_checker import check_blendshapes
from validator.model_loader import load_model_metadata
from validator.pose_checker import check_pose


@dataclass
class ValidationReport:
    file_path: str
    is_valid: bool
    summary: str
    blocked_by_environment: bool = False
    checks: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    missing_dependencies: list[str] = field(default_factory=list)


REQUIRED_HUMANOID_BONES = {
    "hips",
    "spine",
    "chest",
    "neck",
    "head",
    "leftupperarm",
    "leftlowerarm",
    "lefthand",
    "rightupperarm",
    "rightlowerarm",
    "righthand",
    "leftupperleg",
    "leftlowerleg",
    "leftfoot",
    "rightupperleg",
    "rightlowerleg",
    "rightfoot",
}


def _check_geometry(metadata: dict, logger) -> dict:
    if not metadata.get("geometry_check_available", True):
        logger.warning("Geometry validation could not run because trimesh is missing.")
        return {
            "passed": False,
            "details": [
                "Geometry validation could not run because the optional dependency 'trimesh' is not installed.",
                "Install the missing package, then run validation again.",
            ],
            "warnings": ["geometry_check_blocked"],
            "blocked": True,
        }

    if not metadata.get("geometry_check_supported", True):
        file_size_bytes = metadata.get("file_size_bytes", 0)
        if file_size_bytes <= 0:
            logger.error("The model file is empty.")
            return {
                "passed": False,
                "details": ["The model file is empty."],
                "warnings": ["geometry_file_empty"],
                "blocked": False,
            }

        logger.warning("Geometry validation is limited for this format because the current loader does not support it.")
        return {
            "passed": True,
            "details": [
                "Automatic geometry inspection is not supported for this format by the current Python loader.",
                f"The file exists and is non-empty ({file_size_bytes} bytes), so geometry validation is treated as best effort.",
            ],
            "warnings": ["geometry_best_effort_only"],
            "blocked": False,
        }

    if not metadata.get("geometry_loaded"):
        logger.error("Unable to load mesh geometry.")
        return {
            "passed": False,
            "details": ["The model geometry could not be loaded."],
            "warnings": ["geometry_unavailable"],
            "blocked": False,
        }

    vertex_count = metadata.get("vertex_count", 0)
    face_count = metadata.get("face_count", 0)
    if vertex_count <= 0 or face_count <= 0:
        logger.error("Model geometry is empty.")
        return {
            "passed": False,
            "details": ["The model does not contain usable vertices or faces."],
            "warnings": ["geometry_empty"],
            "blocked": False,
        }

    logger.info("Geometry validation passed.")
    return {
        "passed": True,
        "details": [f"Loaded geometry with {vertex_count} vertices and {face_count} faces."],
        "warnings": [],
        "blocked": False,
    }


def _check_rig(metadata: dict, logger) -> dict:
    gltf = metadata.get("gltf")
    suffix = metadata.get("suffix")

    if suffix in {".glb", ".gltf", ".vrm"} and not metadata.get("gltf_check_available", True):
        logger.warning("Rig validation could not run because pygltflib is missing.")
        return {
            "passed": False,
            "details": [
                "Rig validation could not run because the optional dependency 'pygltflib' is not installed.",
                "Install the missing package, then run validation again.",
            ],
            "warnings": ["rig_check_blocked"],
            "blocked": True,
        }

    if suffix not in {".glb", ".gltf", ".vrm"} or gltf is None:
        logger.warning("Rig validation is limited for this file type.")
        return {
            "passed": True,
            "details": [
                "Detailed humanoid rig inspection is only available for glTF/VRM files.",
                "Validation will continue using geometry-only checks for this format.",
            ],
            "warnings": ["rig_best_effort_only"],
            "blocked": False,
        }

    skins = gltf.skins or []
    nodes = gltf.nodes or []
    node_names = {((node.name or "") if node else "").replace(" ", "").lower() for node in nodes}

    if not skins:
        logger.error("No skin data found in the model.")
        return {
            "passed": False,
            "details": ["The model does not contain skinning information."],
            "warnings": ["skins_missing"],
            "blocked": False,
        }

    missing_bones = sorted(bone for bone in REQUIRED_HUMANOID_BONES if bone not in node_names)
    if missing_bones:
        logger.error(f"Missing required bones: {', '.join(missing_bones)}")
        return {
            "passed": False,
            "details": [f"Missing required humanoid bones: {', '.join(missing_bones)}"],
            "warnings": ["required_bones_missing"],
            "blocked": False,
        }

    logger.info("Rig validation passed with required humanoid bones present.")
    return {
        "passed": True,
        "details": [
            f"Detected {len(skins)} skin set(s).",
            "All required humanoid bones were found in the node hierarchy.",
        ],
        "warnings": [],
        "blocked": False,
    }


def validate_model_file(file_path: Path, logger) -> ValidationReport:
    if not file_path.exists():
        raise FileNotFoundError(f"Selected file does not exist: {file_path}")

    metadata = load_model_metadata(file_path, logger)

    checks = {
        "geometry": _check_geometry(metadata, logger),
        "rig": _check_rig(metadata, logger),
        "pose": check_pose(metadata, logger),
        "blendshapes": check_blendshapes(metadata, logger),
    }

    warnings = list(metadata.get("warnings", []))
    errors = []
    blocked_by_environment = False

    for name, check in checks.items():
        warnings.extend(check.get("warnings", []))
        if not check.get("passed", False):
            errors.append(name)
        if check.get("blocked", False):
            blocked_by_environment = True

    is_valid = all(check["passed"] for check in checks.values())
    if is_valid:
        summary = "Model passed all validation checks and is ready for VRM conversion."
    elif blocked_by_environment:
        summary = "Validation could not complete because required Python packages are missing."
    else:
        summary = "Model failed one or more validation checks."

    return ValidationReport(
        file_path=str(file_path),
        is_valid=is_valid,
        summary=summary,
        blocked_by_environment=blocked_by_environment,
        checks=checks,
        warnings=warnings,
        errors=errors,
        missing_dependencies=sorted(set(metadata.get("missing_dependencies", []))),
    )
