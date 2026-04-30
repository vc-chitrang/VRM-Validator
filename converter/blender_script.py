import sys
from pathlib import Path


def clear_scene(bpy) -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    # Clean up orphaned data blocks so imports start from a predictable scene.
    if hasattr(bpy.ops.outliner, "orphans_purge"):
        try:
            bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
        except Exception:
            pass


def ensure_vrm_addon_enabled() -> None:
    import addon_utils
    import bpy

    candidate_modules = (
        "bl_ext.blender_org.vrm",
        "vrm",
        "io_scene_vrm",
    )
    for module_name in candidate_modules:
        try:
            _default_enabled, loaded = addon_utils.check(module_name)
        except Exception:
            continue

        if not loaded:
            try:
                addon_utils.enable(module_name, default_set=False, persistent=False)
            except Exception:
                continue

        if hasattr(bpy.ops.export_scene, "vrm"):
            print(f"VRM add-on loaded via module: {module_name}")
            return

    raise RuntimeError(
        "VRM export operator not found in Blender. Install or enable the 'VRM format' add-on in Blender before converting."
    )


def import_model(bpy, input_path: Path) -> None:
    suffix = input_path.suffix.lower()

    if suffix == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(input_path))
    elif suffix == ".obj":
        bpy.ops.wm.obj_import(filepath=str(input_path))
    elif suffix in {".glb", ".gltf"}:
        bpy.ops.import_scene.gltf(filepath=str(input_path))
    else:
        raise ValueError(f"Unsupported input format for Blender conversion: {suffix}")


def export_vrm(bpy, output_path: Path) -> None:
    # The VRM export operator is provided by the official VRM Add-on for Blender.
    if hasattr(bpy.ops.export_scene, "vrm"):
        result = bpy.ops.export_scene.vrm(filepath=str(output_path))
        if result != {"FINISHED"}:
            raise RuntimeError(f"VRM export did not finish successfully: {result}")
        return

    raise RuntimeError(
        "VRM export operator not found in Blender. Install or enable the 'VRM format' add-on in Blender before converting."
    )


def main():
    if "--" not in sys.argv:
        raise RuntimeError("Expected Blender arguments after '--'.")

    raw_args = sys.argv[sys.argv.index("--") + 1 :]
    if len(raw_args) != 2:
        raise RuntimeError("Expected input and output file paths.")

    input_path = Path(raw_args[0]).resolve()
    output_path = Path(raw_args[1]).resolve()

    import bpy

    ensure_vrm_addon_enabled()
    clear_scene(bpy)
    import_model(bpy, input_path)
    export_vrm(bpy, output_path)
    print(f"VRM export completed: {output_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
