from concurrent.futures import ThreadPoolExecutor
import traceback

class ExceptionLoggingThreadPoolExecutor(ThreadPoolExecutor):
    def __init__(self, max_workers, thread_name_prefix=None, logger=None):
        super().__init__(max_workers=max_workers,
                         thread_name_prefix=thread_name_prefix)
        self.logger = logger

    def submit(self, fn, *args, **kwargs):
        return super().submit(self.exception_logger, fn, *args, **kwargs)

    def exception_logger(self, fn, *args, **kwargs): 
        """
        Waits for future's result and logs any thrown exception
        """
        try:
            fn(*args, **kwargs)
        except Exception:
            msg = (f"[{self._thread_name_prefix}]"
                   f"{traceback.format_exc()}")
            if self.logger:
                self.logger.error(msg)
            else:
                print(msg, flush=True)