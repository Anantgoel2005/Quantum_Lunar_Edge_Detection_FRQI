"""Atomic live status writes shared by the detector and local viewer."""
import json
import time
from pathlib import Path


def write_json_atomic(path,value):
    path = Path(path)
    temporary = path.with_name(path.name+'.pending')
    temporary.write_text(json.dumps(value,separators=(',',':')),encoding='utf-8')
    for attempt in range(10):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 9:
                raise
            time.sleep(0.01)
