from flask import jsonify

def api_response(data=None, success=True, error=None, meta=None, status_code=200):
    """
    Standard envelope format:
    {
      "success": bool,
      "data": ...,
      "error": { "code": "...", "message": "...", "details": ... } or None,
      "meta": { ... } or None
    }
    """
    body = {
        "success": success,
        "data": data,
        "error": error,
    }
    if meta is not None:
        body["meta"] = meta
    return jsonify(body), status_code

def api_error(code, message, details=None, status_code=400):
    err = {
        "code": code,
        "message": message,
    }
    if details is not None:
        err["details"] = details
    return api_response(data=None, success=False, error=err, status_code=status_code)

