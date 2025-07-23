import datetime

def build_result_json(offset, obstacles, warnings, image_base64=None):
    result = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "status": "success",
        "data": {
            "offset": offset,
            "obstacles": obstacles,
            "warnings": warnings
        }
    }
    if image_base64:
        result["data"]["image_base64"] = image_base64
    return result


def build_error_json(message: str, code: int = 400, details: str = None):
    error_response = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "status": "error",
        "error": {
            "code": code,
            "message": message
        }
    }
    if details:
        error_response["error"]["details"] = details
    return error_response
