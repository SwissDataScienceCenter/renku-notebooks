from functools import wraps
from flask import make_response, jsonify, current_app
from flask_apispec import marshal_with

from .schemas import DefaultResponseSchema, FailedParsing


def validate_response_with(schema_dict):
    def decorator(f):
        # add failed parsing response to dict
        schema_dict.update({422: FailedParsing()})
        # decorate with marshal_with for swagger docs
        f_decorated = f
        for status_code in schema_dict.keys():
            f_decorated = marshal_with(schema_dict[status_code], code=status_code)(
                f_decorated
            )
        if "default" not in schema_dict.keys():
            f_decorated = marshal_with(DefaultResponseSchema(), code="default")(
                f_decorated
            )
        if 302 not in schema_dict.keys():
            f_decorated = marshal_with(None, code=302)(f_decorated)
            schema_dict.update({302: None})

        @wraps(f_decorated)
        def wrapper(*args, **kwargs):
            res = make_response(f_decorated(*args, **kwargs))
            res_json = res.get_json()
            # determine the schema to use based on return code
            if res.status_code in schema_dict.keys():
                schema = schema_dict[res.status_code]
            else:
                schema = DefaultResponseSchema()
            # validate with the selected schema and return response
            if schema is not None:
                val_res = schema.validate(data=res_json, many=False)
                if val_res == {}:
                    return res
                else:
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
