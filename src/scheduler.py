# scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler

_scheduler = None

def start_scheduler():
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
        _scheduler.start()

def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)

def schedule_job(job_id, func, trigger, trigger_args):
    start_scheduler()
    if trigger['type'] == 'interval':
        return _scheduler.add_job(func, 'interval', seconds=trigger.get('seconds',60), id=job_id, args=trigger_args, replace_existing=True)
    elif trigger['type'] == 'cron':
        return _scheduler.add_job(func, 'cron', id=job_id, **trigger.get('cron',{}), args=trigger_args, replace_existing=True)
    else:
        raise ValueError("Unsupported trigger type")
