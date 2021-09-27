import shutil


def disk_usage():
    """Get the amount of total, used and free bytes for the disk
    that stores the current directory"""
    res = shutil.disk_usage("./")
    return {
        "totalBytes": res.total,
        "usedBytes": res.used,
        "freeBytes": res.free,
    }
