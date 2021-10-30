#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
from fields import Fields
import hashlib
import json
import logging
import scoring
import uuid
from abc import ABCMeta, abstractmethod
from builtins import isinstance
from http.server import HTTPServer, BaseHTTPRequestHandler
from optparse import OptionParser

SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}


class RequestAttributes(type):

    def __init__(cls, name, bases, dct):
        super(RequestAttributes, cls).__init__(name, bases, dct)
        cls.fields = []
        for key, attribute in dct.items():
            if isinstance(attribute, Fields.AbstractField):
                attribute.name = key
                cls.fields.append(attribute)


class Request(metaclass=RequestAttributes):
    empty_values_tuple = (None, '', [], {}, ())

    def __init__(self, request):
        self._errors = []
        self._has_errors = True
        self.request = request

    @staticmethod
    def format_error_string(field, message):
        return "{}: {}".format(field.name, message)

    def check_fields(self):
        for field in self.fields:
            value = None
            if field.name not in self.request or self.request[field.name] in self.empty_values_tuple:
                if field.required:
                    self._errors.append(self.format_error_string(field, "Field is required."))
            else:
                value = self.request[field.name]
            if value in self.empty_values_tuple and not field.nullable:
                self._errors.append(self.format_error_string(field, "Field not be nullable."))
            try:
                if value not in self.empty_values_tuple:
                    value = field.validate_field(value)
                    setattr(self, field.name, value)
            except ValueError as e:
                self._errors.append(self.format_error_string(field, e))
        return self._errors

    def get_fields_with_value(self):
        fields = []
        for field in self.fields:
            if field.name in self.request not in self.empty_values_tuple:
                fields.append(field.name)
        return fields

    def is_valid(self):
        if self._has_errors:
            self._has_errors = not self.check_fields()
        return self._has_errors

    def error_msg(self):
        return ", ".join(self._errors)


class ClientsInterestsRequest(Request):
    client_ids = Fields.ClientIDsField(required=True)
    date = Fields.DateField(required=False, nullable=True)


class OnlineScoreRequest(Request):
    _couples = (
        ("phone", "email"),
        ("first_name", "last_name"),
        ("gender", "birthday"),
    )

    first_name = Fields.CharField(required=False, nullable=True)
    last_name = Fields.CharField(required=False, nullable=True)
    email = Fields.EmailField(required=False, nullable=True)
    phone = Fields.PhoneField(required=False, nullable=True)
    birthday = Fields.BirthDayField(required=False, nullable=True)
    gender = Fields.GenderField(required=False, nullable=True)

    def check_fields(self):
        self._errors = super(OnlineScoreRequest, self).check_fields()
        fields_with_value = set(self.get_fields_with_value())
        result = any([fields_with_value.issuperset(couple) for couple in self._couples])
        if not result:
            self._errors.append(
                "Couples {} should be not empty".format(" or ".join(str(couple) for couple in self._couples)))
        return self._errors


class MethodRequest(Request):
    account = Fields.CharField(required=False, nullable=True)
    login = Fields.CharField(required=True, nullable=True)
    token = Fields.CharField(required=True, nullable=True)
    arguments = Fields.ArgumentsField(required=True, nullable=True)
    method = Fields.CharField(required=True, nullable=False)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN


class AbstractRequestHandler(metaclass=ABCMeta):

    def __init__(self, request, ctx):
        self.request = request
        self.ctx = ctx

    @abstractmethod
    def init_request(self, field_data):
        """
        Create request element
        """

    @abstractmethod
    def processing_handler(self, request_type):
        """
        OnlineScoreRequestHandler or ClientsInterestsRequestHandler for processing the request
        """

    def start_processing(self, field_data):
        request_type = self.init_request(field_data)
        if not request_type.is_valid():
            return request_type.error_msg(), INVALID_REQUEST
        return self.processing_handler(request_type)


class OnlineScoreRequestHandler(AbstractRequestHandler):
    def init_request(self, field_data):
        return OnlineScoreRequest(field_data)

    def processing_handler(self, request_type):
        self.ctx["has"] = request_type.get_fields_with_value()
        if self.request.is_admin:
            return {"score": 42}, OK
        return {"score": scoring.get_score(None, self.request.arguments.get("phone"),
                                           self.request.arguments.get("email"), self.request.request.get("birthday"),
                                           self.request.request.get("gender"), self.request.request.get("first_name"),
                                           self.request.request.get("last_name"))}, OK


class ClientsInterestsRequestHandler(AbstractRequestHandler):
    def init_request(self, field_data):
        return ClientsInterestsRequest(field_data)

    def processing_handler(self, request_type):
        response = {i: scoring.get_interests(None, None) for i in request_type.client_ids}
        self.ctx["nclients"] = len(request_type.client_ids)
        return response, OK


def check_auth(request):
    if request.is_admin:
        digest = hashlib.sha512(
            datetime.datetime.now().strftime("%Y%m%d%H").encode("utf-8") + ADMIN_SALT.encode("utf-8")).hexdigest()
    else:
        digest = hashlib.sha512(
            request.account.encode("utf-8") + request.login.encode("utf-8") + SALT.encode("utf-8")).hexdigest()
    if digest == request.token:
        return True
    return False


def method_handler(request, ctx):
    handlers = {
        "online_score": OnlineScoreRequestHandler,
        "clients_interests": ClientsInterestsRequestHandler
    }
    request = MethodRequest(request["body"])
    if not request.is_valid():
        return request.error_msg(), INVALID_REQUEST
    if request.method not in handlers:
        return None, NOT_FOUND
    if not check_auth(request):
        return None, FORBIDDEN
    if not isinstance(request.arguments, dict):
        return "Arguments must be a dictionary", INVALID_REQUEST

    return handlers[request.method](request, ctx).start_processing(request.arguments)


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler
    }

    def get_request_id(self, headers):
        return headers.get("HTTP_X_REQUEST_ID", uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers["Content-Length"]))
            request = json.loads(data_string)
        except:
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))
            if path in self.router:
                try:
                    response, code = self.router[path]({"body": request, "headers": self.headers}, context)
                except Exception as e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r).encode("utf-8"))
        return


if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO,
                        format="[%(asctime)s] %(levelname).1s %(message)s", datefmt="%Y.%m.%d %H:%M:%S")
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
