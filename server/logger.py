# logger.py
import json
import time
import os
import sys

# Select correct file-lock system based on OS
WINDOWS = os.name == "nt"

if WINDOWS:
    import msvcrt
else:
    import fcntl


class SharedLogger:
    """
    Cross-platform shared logger:
    - Uses fcntl on Linux/Mac
    - Uses msvcrt on Windows
    """

    def __init__(self, logfile_path: str):
        self.logfile_path = logfile_path

        # Create directories automatically (shared/logs/)
        folder = os.path.dirname(logfile_path)
        if folder:
            os.makedirs(folder, exist_ok=True)

    def lock(self, file):
        """Lock file depending on OS."""
        if WINDOWS:
            msvcrt.locking(file.fileno(), msvcrt.LK_LOCK, 1)
        else:
            fcntl.flock(file, fcntl.LOCK_EX)

    def unlock(self, file):
        """Unlock file depending on OS."""
        if WINDOWS:
            try:
                msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)
            except:
                pass
        else:
            fcntl.flock(file, fcntl.LOCK_UN)

    def log(self, record: dict):
        """
        Append a JSON record to the shared log with a mutex.
        """
        record["logged_at"] = time.time()
        line = json.dumps(record, ensure_ascii=False)

        with open(self.logfile_path, "a", encoding="utf-8") as f:
            # lock file safely
            self.lock(f)

            f.write(line + "\n")
            f.flush()

            # unlock
            self.unlock(f)
