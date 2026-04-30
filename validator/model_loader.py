from pathlib import Path


def load_model_metadata(file_path: Path, logger):
    suffix = file_path.suffix.lower()
    metadata = {
        "path": str(file_path),
        "suffix": suffix,
        "geometry_loaded": False,
        "geometry_check_available": True,
        "geometry_check_supported": True,
        "vertex_count": 0,
        "face_count": 0,
        "file_size_bytes": 0,
        "scene_present": False,
        "gltf": None,
        "gltf_check_available": True,
        "missing_dependencies": [],
        "warnings": [],
    }
    metadata["file_size_bytes"] = file_path.stat().st_size

    try:
        import trimesh
    except ImportError:
        logger.warning("trimesh is not installed. Geometry checks will be limited.")
        metadata["warnings"].append("trimesh_missing")
        metadata["missing_dependencies"].append("trimesh")
        metadata["geometry_check_available"] = False
        trimesh = None

    if trimesh is not None:
        try:
            loaded = trimesh.load(str(file_path), force="scene")
            metadata["geometry_loaded"] = True
            metadata["scene_present"] = True

            geometries = getattr(loaded, "geometry", {})
            for geometry in geometries.values():
                metadata["vertex_count"] += len(getattr(geometry, "vertices", []))
                metadata["face_count"] += len(getattr(geometry, "faces", []))

            logger.info(
                f"Geometry loaded successfully. Vertices: {metadata['vertex_count']}, Faces: {metadata['face_count']}"
            )
        except Exception as exc:
            logger.warning(f"Geometry loading failed: {exc}")
            metadata["warnings"].append(f"geometry_load_failed:{exc}")
            if "not supported" in str(exc).lower():
                metadata["geometry_check_supported"] = False
                metadata["warnings"].append("geometry_format_not_supported")

    if suffix in {".glb", ".gltf", ".vrm"}:
        try:
            from pygltflib import GLTF2

            gltf = GLTF2().load(str(file_path))
            metadata["gltf"] = gltf
            logger.info("GLTF/VRM metadata loaded successfully.")
        except ImportError:
            logger.warning("pygltflib is not installed. Skeleton and blendshape checks will be limited.")
            metadata["warnings"].append("pygltflib_missing")
            metadata["missing_dependencies"].append("pygltflib")
            metadata["gltf_check_available"] = False
        except Exception as exc:
            logger.warning(f"GLTF metadata loading failed: {exc}")
            metadata["warnings"].append(f"gltf_load_failed:{exc}")
    else:
        logger.info("Non-glTF model selected. Bone and blendshape checks will use best-effort validation.")

    return metadata
