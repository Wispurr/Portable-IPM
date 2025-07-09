import datetime

def build_result_json(offset, obstacles, warnings):
    return {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "status": "success",
        "data": {
            "offset": offset,
            "obstacles": obstacles,
            "warnings": warnings
        }
    }

def build_error_json(message: str):
    return {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "status": "error",
        "error": message
    }