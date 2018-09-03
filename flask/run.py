from app import create_app, run_watcher

import threading
import time

app = create_app()

if __name__ == '__main__':
    watcher_thread = threading.Thread(target=run_watcher)
    watcher_thread.start()
    app.run(debug=True, host='0.0.0.0')
    watcher_thread.join()

