def check_blendshapes(metadata: dict, logger) -> dict:
    gltf = metadata.get("gltf")
    suffix = metadata.get("suffix")

    if suffix in {".glb", ".gltf", ".vrm"} and not metadata.get("gltf_check_available", True):
        logger.warning("Blendshape validation could not run because pygltflib is missing.")
        return {
            "passed": False,
            "details": [
                "Blendshape validation could not run because the optional dependency 'pygltflib' is not installed.",
                "Install the missing package, then run validation again.",
            ],
            "warnings": ["blendshape_check_blocked"],
            "blocked": True,
        }

    if suffix not in {".glb", ".gltf", ".vrm"} or gltf is None:
        logger.warning("Blendshape validation is limited for this file type.")
        return {
            "passed": True,
            "details": [
                "Automatic blendshape inspection is only available for glTF/VRM content.",
                "Validation will continue without failing this check.",
            ],
            "warnings": ["blendshape_best_effort_only"],
            "blocked": False,
        }

    target_count = 0
    target_names = []
    for mesh in gltf.meshes or []:
        extras = mesh.extras if isinstance(mesh.extras, dict) else {}
        target_names.extend(extras.get("targetNames", []))
        for primitive in mesh.primitives or []:
            if primitive.targets:
                target_count += len(primitive.targets)

    if target_count > 0 or target_names:
        detail = f"Detected {max(target_count, len(target_names))} blendshape targets."
        logger.info(detail)
        return {"passed": True, "details": [detail], "warnings": [], "blocked": False}

    logger.warning("No blendshape targets detected in the model.")
    return {
        "passed": False,
        "details": ["No blendshape or morph target data was detected."],
        "warnings": ["blendshapes_missing"],
        "blocked": False,
    }
