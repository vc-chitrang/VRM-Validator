from datetime import datetime


class QueueLogger:
    def __init__(self, output_queue):
        self.output_queue = output_queue

    def _write(self, level: str, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.output_queue.put(f"[{timestamp}] {level.upper():<7} {message}")

    def info(self, message: str) -> None:
        self._write("info", message)

    def warning(self, message: str) -> None:
        self._write("warning", message)

    def error(self, message: str) -> None:
        self._write("error", message)

    def exception(self, message: str, exc: Exception) -> None:
        self._write("error", f"{message}: {exc}")
