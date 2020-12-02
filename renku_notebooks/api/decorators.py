from functools import wraps
from flask import make_response, jsonify, current_app


def validate_response_with(schema_dict):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            res = make_response(f(*args, **kwargs))
            res_json = res.get_json()
            if res.status_code in schema_dict.keys():
                val_res = schema_dict[res.status_code].validate(
                    data=res_json, many=False
                )
                if val_res == {}:
                    return res
                else:
                    current_app.logger.error(
                        f"The response validation produced errors:\n{val_res}"
                    )
            return make_response(
                jsonify(
                    {
                        "messages": [
                            "The endpoint returned values that violated "
                            "or did not match any response schema."
                        ]
                    }
                ),
                500,
            )

        return wrapper

    return decorator
