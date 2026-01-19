import json
import fcntl
import os

def load_json_secure(file_path):
    lock_path = file_path + ".lock"
    if not os.path.exists(lock_path):
        open(lock_path, 'a').close()

    with open(lock_path, "w") as lockfile:
        fcntl.flock(lockfile, fcntl.LOCK_SH)
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
        finally:
            fcntl.flock(lockfile, fcntl.LOCK_UN)
 
def save_json_secure(file_path, data):
    lock_path = file_path + ".lock"
    
    with open(lock_path, "w") as lockfile:
        fcntl.flock(lockfile, fcntl.LOCK_EX)
        try:
            temp_path = file_path + ".tmp"
            with open(temp_path, "w") as f:
                json.dump(data, f, indent=4)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, file_path)
            
        finally:
            fcntl.flock(lockfile, fcntl.LOCK_UN)
