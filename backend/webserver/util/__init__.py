

import time
import logging


def profile(func):
    def wrap(*args, **kwargs):
        started_at = time.time()
        result = func(*args, **kwargs)
        diff = time.time() - started_at
        if isinstance(result, dict):
            result['time_ms'] = int(diff * 1000)
        return result

    return wrap