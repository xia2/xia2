from __future__ import annotations

import contextlib
import logging
import pathlib

logger = logging.getLogger("xia2.Handlers.Files")


class _MultiplexFileHandler:
    def __init__(self):
        # Files which will always be deleted
        self._temporary_files: list[pathlib.Path] = []

        # Files which have the option to be deleted based on phil param cleanup
        self._optional_files: list[pathlib.Path] = []

        # Final files output to DataFiles (mtz, sca, mmcif)
        self._data_files: list[pathlib.Path] = []

        # Overall multiplex log files output to LogFiles (does not include logs of individual steps)
        self._log_files: list[pathlib.Path] = []

        self.delete_optional_files = False

    def set_cleanup(self, cleanup: bool):
        self.delete_optional_files = cleanup

    def cleanup(self, base_path):
        base_path = pathlib.Path(base_path).resolve()

        for f in self._temporary_files:
            if base_path in f.parents:
                try:
                    f.unlink()
                    logger.debug(f"Deleted: {f}")
                except FileNotFoundError as e:
                    logger.debug(f"Failed to delete: {f} ({e})")

        if self.delete_optional_files:
            for f in self._optional_files:
                if base_path in f.parents:
                    try:
                        f.unlink()
                        logger.debug(f"Deleted: {f}")
                    except FileNotFoundError as e:
                        logger.debug(f"Failed to delete: {f} ({e})")

        data_path = base_path / "DataFiles"
        data_path.mkdir(exist_ok=True)
        log_path = base_path / "LogFiles"
        log_path.mkdir(exist_ok=True)

        for f in self._log_files:
            target = log_path / f.name
            try:
                f.rename(target)
            except FileNotFoundError as e:
                logger.debug(f"Failed to move: {f} ({e})")

        for f in self._data_files:
            target = data_path / f.name
            try:
                f.rename(target)
            except FileNotFoundError as e:
                logger.debug(f"Failed to move {f} ({e})")

    def record_data_file(self, filename):
        data_file = pathlib.Path(filename).resolve()
        if data_file not in self._data_files:
            assert data_file.exists(), f"Required file {data_file} not found."
            self._data_files.append(data_file)

    def record_log_file(self, filename):
        log_file = pathlib.Path(filename).resolve()
        if log_file not in self._log_files:
            assert log_file.exists(), f"Required file {log_file} not found."
            self._log_files.append(log_file)

    def record_temp_file(self, filename):
        temp_file = pathlib.Path(filename).resolve()
        if temp_file not in self._temporary_files:
            assert temp_file.exists(), f"Temporary file {temp_file} not found."
            self._temporary_files.append(temp_file)

    def record_optional_file(self, filename):
        optional_file = pathlib.Path(filename).resolve()
        if optional_file not in self._optional_files:
            assert optional_file.exists(), f"Optional file {optional_file} not found."
            self._optional_files.append(optional_file)


MultiplexFileHandler = _MultiplexFileHandler()


@contextlib.contextmanager
def cleanup(base_path):
    try:
        yield
    finally:
        MultiplexFileHandler.cleanup(base_path)
