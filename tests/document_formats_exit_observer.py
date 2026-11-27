"""Read-only exit observation after callers fully enroll owned processes.

Actions/enrollment still use the strict shared argv/exe identity checks. Exit
polling never signals a process and never equates a denial with termination.
"""


def waiting_for_owned_exit(stamp):
    import psutil
    assert set(stamp)=={'pid','created','argv','exe'}
    assert isinstance(stamp['argv'],list) and isinstance(stamp['exe'],str)
    try:
        process=psutil.Process(stamp['pid'])
        created=process.create_time()
    except psutil.ZombieProcess:return True  # Creation identity unconfirmed.
    except psutil.NoSuchProcess:return False
    except psutil.AccessDenied:return True
    assert created==stamp['created'],'task process creation identity changed'
    try:
        return process.is_running() and process.status()!=psutil.STATUS_ZOMBIE
    except (psutil.NoSuchProcess,psutil.ZombieProcess):return False
    except psutil.AccessDenied:return True
