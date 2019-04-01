
from celery import shared_task


@shared_task
def long_task(n):

    print(f"This task will take {n} seconds")
    import time

    for i in range(n):
        print(i)
        time.sleep(1)
    
    return n