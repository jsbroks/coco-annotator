
from celery import shared_task


@shared_task
def long_task(n):

    print(f"this task will take {n} seconds")
    import time

    for i in range(n):
        print(i)
        time.sleep(n)
    
    return n