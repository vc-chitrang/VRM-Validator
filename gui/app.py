import json
import importlib.util
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from converter.blender_runner import BlenderRunner
from gui.components import ActionButtons, FileSelector, LogPanel, ReportPanel
from utils.logger import QueueLogger
from validator.report_generator import format_validation_report, validation_report_to_dict
from validator.rig_checker import validate_model_file


class AvatarPipelineApp:
    SUPPORTED_FILE_TYPES = [("3D Models", "*.fbx *.obj *.glb *.gltf *.vrm")]

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Avatar Pipeline Tool")
        self.root.geometry("800x600")
        self.root.minsize(720, 520)

        self.log_queue: "queue.Queue[str]" = queue.Queue()
        self.ui_logger = QueueLogger(self.log_queue)

        self.selected_file: Path | None = None
        self.last_report: dict | None = None
        self.last_report_text = ""
        self.is_valid_model = False
        self.is_busy = False

        self._configure_style()
        self._build_layout()
        self._poll_log_queue()
        self._refresh_button_state()
        self.root.after(250, self._show_startup_dependency_hint)

    def _configure_style(self) -> None:
        self.root.configure(bg="#1e1f22")
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(".", background="#1e1f22", foreground="#f2f2f2")
        style.configure("TFrame", background="#1e1f22")
        style.configure("TLabel", background="#1e1f22", foreground="#f2f2f2")
        style.configure("TLabelframe", background="#1e1f22", foreground="#f2f2f2")
        style.configure("TLabelframe.Label", background="#1e1f22", foreground="#f2f2f2")
        style.configure("TButton", padding=6)
        style.configure("TEntry", fieldbackground="#2b2d31", foreground="#f2f2f2")
        style.configure(
            "Pipeline.Horizontal.TProgressbar",
            troughcolor="#2b2d31",
            background="#4aa3ff",
            bordercolor="#1e1f22",
            lightcolor="#4aa3ff",
            darkcolor="#4aa3ff",
        )

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(3, weight=1)
        self.root.rowconfigure(4, weight=1)

        self.title_label = ttk.Label(
            self.root,
            text="Avatar Pipeline Tool",
            font=("Segoe UI", 18, "bold"),
        )
        self.title_label.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 8))

        self.file_selector = FileSelector(self.root, browse_callback=self.on_browse_file)
        self.file_selector.grid(row=1, column=0, sticky="ew", padx=16, pady=8)

        self.action_buttons = ActionButtons(
            self.root,
            validate_callback=self.on_validate_clicked,
            convert_callback=self.on_convert_clicked,
            save_report_callback=self.on_save_report_clicked,
        )
        self.action_buttons.grid(row=2, column=0, sticky="w", padx=16, pady=8)

        self.report_panel = ReportPanel(self.root)
        self.report_panel.grid(row=3, column=0, sticky="nsew", padx=16, pady=8)

        self.log_panel = LogPanel(self.root)
        self.log_panel.grid(row=4, column=0, sticky="nsew", padx=16, pady=8)

        progress_frame = ttk.Frame(self.root)
        progress_frame.grid(row=5, column=0, sticky="ew", padx=16, pady=(0, 16))
        progress_frame.columnconfigure(0, weight=1)

        self.status_var = tk.StringVar(value="Select a model file to begin.")
        self.status_label = ttk.Label(progress_frame, textvariable=self.status_var)
        self.status_label.grid(row=0, column=0, sticky="w", pady=(0, 4))

        self.progress = ttk.Progressbar(
            progress_frame,
            style="Pipeline.Horizontal.TProgressbar",
            mode="indeterminate",
        )
        self.progress.grid(row=1, column=0, sticky="ew")

    def _refresh_button_state(self) -> None:
        self.action_buttons.set_busy(self.is_busy)
        self.action_buttons.set_convert_enabled((not self.is_busy) and self.is_valid_model)
        self.action_buttons.set_save_enabled((not self.is_busy) and self.last_report is not None)

    def _set_busy(self, busy: bool, status: str) -> None:
        self.is_busy = busy
        self.status_var.set(status)
        if busy:
            self.progress.start(10)
        else:
            self.progress.stop()
        self._refresh_button_state()

    def _poll_log_queue(self) -> None:
        while True:
            try:
                line = self.log_queue.get_nowait()
            except queue.Empty:
                break
            else:
                self.log_panel.append(line)
        self.root.after(100, self._poll_log_queue)

    def _get_missing_validation_dependencies(self) -> list[str]:
        packages = []
        for package_name in ("trimesh", "pygltflib"):
            if importlib.util.find_spec(package_name) is None:
                packages.append(package_name)
        return packages

    def _show_startup_dependency_hint(self) -> None:
        missing = self._get_missing_validation_dependencies()
        if not missing:
            return

        package_list = ", ".join(missing)
        self.log_panel.append(
            f"Validation dependencies missing: {package_list}. Install them with: pip install {' '.join(missing)}"
        )
        self.status_var.set("Some validation features are unavailable until optional packages are installed.")

    def on_browse_file(self) -> None:
        selected = filedialog.askopenfilename(filetypes=self.SUPPORTED_FILE_TYPES)
        if not selected:
            return

        self.selected_file = Path(selected)
        self.file_selector.set_path(str(self.selected_file))
        self.last_report = None
        self.last_report_text = ""
        self.is_valid_model = False
        self.report_panel.set_text("")
        self.status_var.set("Model selected. Ready for validation.")
        self.log_panel.append(f"Selected file: {self.selected_file}")
        self._refresh_button_state()

    def on_validate_clicked(self) -> None:
        if not self.selected_file:
            messagebox.showwarning("No File Selected", "Please select a 3D model file first.")
            return

        self.log_panel.clear()
        self.report_panel.set_text("")
        self._set_busy(True, "Validating model...")

        thread = threading.Thread(target=self._run_validation, daemon=True)
        thread.start()

    def _run_validation(self) -> None:
        try:
            self.ui_logger.info(f"Starting validation for: {self.selected_file}")
            report = validate_model_file(self.selected_file, self.ui_logger)
            report_text = format_validation_report(report)

            self.last_report = validation_report_to_dict(report)
            self.last_report_text = report_text
            self.is_valid_model = report.is_valid

            self.root.after(0, lambda: self.report_panel.set_text(report_text))
            if report.is_valid:
                final_status = "Validation passed. Model is ready for VRM conversion."
            elif report.blocked_by_environment:
                final_status = "Validation is blocked by missing Python packages. Install them and try again."
            else:
                final_status = "Validation failed. Review the report before converting."
            self.ui_logger.info(final_status)
            self.root.after(0, lambda: self._set_busy(False, final_status))
            if report.blocked_by_environment:
                missing = ", ".join(report.missing_dependencies)
                command = f"pip install {' '.join(report.missing_dependencies)}"
                self.root.after(
                    0,
                    lambda: messagebox.showwarning(
                        "Missing Validation Dependencies",
                        f"Validation could not finish because these packages are missing: {missing}\n\nInstall them with:\n{command}",
                    ),
                )
        except Exception as exc:
            self.is_valid_model = False
            self.ui_logger.exception("Validation failed unexpectedly", exc)
            self.root.after(0, lambda: self._set_busy(False, "Validation failed due to an unexpected error."))
            self.root.after(0, lambda: messagebox.showerror("Validation Error", str(exc)))

    def on_convert_clicked(self) -> None:
        if not self.selected_file:
            messagebox.showwarning("No File Selected", "Please select a 3D model file first.")
            return

        if not self.is_valid_model:
            messagebox.showwarning("Model Not Validated", "Please validate a compatible model before converting.")
            return

        default_output = self.selected_file.with_suffix(".vrm")
        output_path = filedialog.asksaveasfilename(
            title="Save VRM File",
            defaultextension=".vrm",
            initialfile=default_output.name,
            filetypes=[("VRM Files", "*.vrm")],
        )
        if not output_path:
            return

        self._set_busy(True, "Converting model to VRM...")
        thread = threading.Thread(target=self._run_conversion, args=(Path(output_path),), daemon=True)
        thread.start()

    def _run_conversion(self, output_path: Path) -> None:
        try:
            self.ui_logger.info(f"Starting conversion to: {output_path}")
            runner = BlenderRunner(self.ui_logger)
            runner.convert_to_vrm(self.selected_file, output_path)
            success_message = f"Conversion completed successfully: {output_path}"
            self.ui_logger.info(success_message)
            self.root.after(0, lambda: self._set_busy(False, success_message))
            self.root.after(0, lambda: messagebox.showinfo("Conversion Complete", success_message))
        except Exception as exc:
            self.ui_logger.exception("Conversion failed", exc)
            self.root.after(0, lambda: self._set_busy(False, "Conversion failed. Check the logs for details."))
            self.root.after(0, lambda: messagebox.showerror("Conversion Error", str(exc)))

    def on_save_report_clicked(self) -> None:
        if not self.last_report:
            messagebox.showwarning("No Report", "Run validation before saving a report.")
            return

        save_path = filedialog.asksaveasfilename(
            title="Save Validation Report",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")],
        )
        if not save_path:
            return

        with open(save_path, "w", encoding="utf-8") as report_file:
            json.dump(self.last_report, report_file, indent=2)

        self.status_var.set("Validation report saved.")
        self.log_panel.append(f"Validation report saved to: {save_path}")


def main() -> None:
    root = tk.Tk()
    app = AvatarPipelineApp(root)
    root.mainloop()
