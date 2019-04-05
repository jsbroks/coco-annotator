
from celery import shared_task
from database import TaskModel

from ..socket import create_socket


@shared_task
def long_task(n, task_id):

    task = TaskModel.objects.get(id=task_id)
    task.update(status="PROGRESS")

    socketio = create_socket()

    print(f"This task will take {n} seconds")
    import time

    for i in range(n):
        print(i)
        time.sleep(1)
        socketio.emit('test', i)
    
    return n


__all__ = ["long_task"]