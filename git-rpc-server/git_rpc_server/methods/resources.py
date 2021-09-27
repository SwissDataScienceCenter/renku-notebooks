import shutil


def disk_usage():
    res = shutil.disk_usage("./")
    return {
        "totalBytes": res.total,
        "usedBytes": res.used,
        "freeBytes": res.free,
    }
