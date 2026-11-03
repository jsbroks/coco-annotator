import os
import subprocess
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_worker_tasks_import_like_celery():
    """`celery -A workers worker` only has the backend folder on sys.path
    while it loads the app; task modules are imported afterwards."""
    code = (
        "import os, sys\n"
        "sys.path.insert(0, os.getcwd())\n"
        "import workers\n"
        "sys.path.remove(os.getcwd())\n"
        "import workers.tasks\n"
        "print('ok')\n"
    )
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    # -I: isolated mode, so neither the cwd nor PYTHONPATH is on sys.path
    result = subprocess.run([sys.executable, "-I", "-c", code], cwd=BACKEND,
                            env=env, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr[-2000:]
    assert result.stdout.strip().endswith("ok")
