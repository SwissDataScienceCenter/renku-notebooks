from functools import wraps
from flask import make_response, jsonify, current_app
from flask_apispec import marshal_with

from .schemas import DefaultResponseSchema, FailedParsing


def validate_response_with(schema_dict):
    def decorator(f):
        # add failed parsing response to dict
        if 422 not in schema_dict.keys():
            schema_dict.update(
                {422: {"schema": FailedParsing(), "description": "Invalid request."}}
            )
        # add redicrect response to dict
        if 302 not in schema_dict.keys():
            schema_dict.update({302: {"schema": None, "description": "Redirect."}})
        # add default response to dict
        if "default" not in schema_dict.keys():
            schema_dict.update(
                {
                    "default": {
                        "schema": DefaultResponseSchema(),
                        "description": "Default response.",
                    }
                }
            )
        # decorate with marshal_with for swagger docs
        f_decorated = f
        for status_code in schema_dict.keys():
            f_decorated = marshal_with(**schema_dict[status_code], code=status_code)(
                f_decorated
            )

        @wraps(f_decorated)
        def wrapper(*args, **kwargs):
            res = make_response(f_decorated(*args, **kwargs))
            res_json = res.get_json()
            # determine the schema to use based on return code
            if res.status_code in schema_dict.keys():
                schema = schema_dict[res.status_code]["schema"]
            else:
                schema = schema_dict["default"]["schema"]
            # validate with the selected schema and return response
            # if the decorator received a parameter with schema=None then skip validation
            if schema is not None:
                val_res = schema.validate(data=res_json, many=False)
                if val_res == {}:  # no validation errors
                    return make_response(
                        jsonify(schema.load(res_json)), res.status_code
                    )
                else:  # validation errors are present
                    current_app.logger.error(
                        f"The response validation produced errors:\n{val_res}"
                    )
                    return make_response(
                        jsonify(
                            {
                                "messages": {
                                    "error": "The endpoint returned values that violated "
                                    "or did not match any response schema."
                                }
                            }
                        ),
                        500,
                    )
            return res

        return wrapper

    return decorator
