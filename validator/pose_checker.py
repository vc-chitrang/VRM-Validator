RECOMMENDED_POSE_KEYWORDS = {"tpose", "t-pose", "a-pose", "apose", "rest", "bind"}


def check_pose(metadata: dict, logger) -> dict:
    suffix = metadata.get("suffix")
    gltf = metadata.get("gltf")

    if suffix in {".glb", ".gltf", ".vrm"} and not metadata.get("gltf_check_available", True):
        logger.warning("Pose validation could not run because pygltflib is missing.")
        return {
            "passed": False,
            "details": [
                "Pose validation could not run because the optional dependency 'pygltflib' is not installed.",
                "Install the missing package, then run validation again.",
            ],
            "warnings": ["pose_check_blocked"],
            "blocked": True,
        }

    if suffix not in {".glb", ".gltf", ".vrm"} or gltf is None:
        logger.warning("Pose validation is limited for this file type. Manual review may still be needed.")
        return {
            "passed": True,
            "details": [
                "Automatic pose validation is limited for this format.",
                "Assuming rest pose compatibility because no skeletal pose data was available.",
            ],
            "warnings": ["pose_best_effort_only"],
            "blocked": False,
        }

    node_names = [((node.name or "") if node else "").lower() for node in gltf.nodes or []]
    matched = [name for name in node_names if any(keyword in name for keyword in RECOMMENDED_POSE_KEYWORDS)]

    if matched:
        logger.info(f"Pose hints found in node names: {', '.join(matched[:5])}")
        return {
            "passed": True,
            "details": ["Pose indicators suggest the model includes a rest, A-pose, or T-pose skeleton."],
            "warnings": [],
            "blocked": False,
        }

    logger.warning("No clear rest-pose indicators were found in node names.")
    return {
        "passed": False,
        "details": [
            "No clear A-pose or T-pose indicators were found in the skeleton metadata.",
            "Manual confirmation is recommended before VRM export.",
        ],
        "warnings": ["pose_indicator_missing"],
        "blocked": False,
    }
