"""Small standard-library adapters for local Windows and POSIX runtimes."""
import contextlib
import errno
import os
from pathlib import Path
import signal
import subprocess


def venv_python(root):
    return Path(root) / ('.venv/Scripts/python.exe' if os.name == 'nt' else '.venv/bin/python')


@contextlib.contextmanager
def build_lock(path):
    """Nonblocking process lock, released by the OS on exit; never remove its file."""
    with Path(path).open('a+b') as lock:
        if os.name == 'nt':
            import msvcrt
            lock.seek(0)
            try:
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                if exc.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                    raise
                raise BlockingIOError('Another index build is running / 已有索引任务在运行') from exc
            try:
                yield
            finally:
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)


def child_process_options():
    # Keep the indexing workers separate from terminal Ctrl+C; close() owns shutdown.
    if os.name == 'nt':
        return {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP}
    return {'start_new_session': True}


def stop_process_tree(process):
    """Stop only a child launched by this app, including its PDF parser workers."""
    if process.poll() is not None:
        return
    if os.name == 'nt':
        taskkill = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32/taskkill.exe'
        result = subprocess.run([str(taskkill), '/PID', str(process.pid), '/T', '/F'],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        if result.returncode and process.poll() is None:
            raise RuntimeError('Unable to stop the indexing process tree / 无法停止索引进程')
        process.wait(timeout=10)
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=10)
