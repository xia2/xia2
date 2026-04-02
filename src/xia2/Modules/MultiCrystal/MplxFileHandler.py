from __future__ import annotations

import contextlib
import logging
import os
import pathlib

logger = logging.getLogger("xia2.Handlers.Files")


class _MultiplexFileHandler:
    def __init__(self):
        self._temporary_files = []
        self._data_files = []
        self._log_files = []

    def cleanup(self, base_path):
        base_path = pathlib.Path(base_path).resolve()

        for f in self._temporary_files:
            try:
                pathlib.Path.unlink(f)
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
            except Exception as e:
                logger.debug(f"Failed to move: {f} ({e})")

        for f in self._data_files:
            target = data_path / f.name
            try:
                f.rename(target)
            except Exception as e:
                logger.debug(f"Failed to move {f} ({e})")

    def record_data_file(self, filename):
        data_file = pathlib.Path(filename).resolve()
        if data_file not in self._data_files:
            assert data_file.exists(), f"Required file {data_file} not found."
            self._data_files.append(data_file)

    def record_log_file(self, filename):
        log_file = pathlib.Path(filename).resolve()
        if log_file not in self._log_files:
            if not os.getenv("PYTEST_CURRENT_TEST"):
                # Tests fails when do below all the time because only creates 1 multiplex log for entire test
                assert log_file.exists(), f"Required file {log_file} not found."
            self._log_files.append(log_file)

    def record_temp_file(self, filename):
        temp_file = pathlib.Path(filename).resolve()
        if temp_file not in self._temporary_files:
            assert temp_file.exists(), f"Temporary file {temp_file} not found."
            self._temporary_files.append(temp_file)


MultiplexFileHandler = _MultiplexFileHandler()


@contextlib.contextmanager
def cleanup(base_path):
    try:
        yield
    finally:
        MultiplexFileHandler.cleanup(base_path)
