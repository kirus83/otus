#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import re
from abc import ABCMeta, abstractmethod


class Fields:
    class AbstractField(metaclass=ABCMeta):

        def __init__(self, required=False, nullable=False):
            self.required = required
            self.nullable = nullable

        @abstractmethod
        def validate_field(self, value):
            """
            Return result of parsed value or raise exception with ValueError
            """

    class CharField(AbstractField):
        def validate_field(self, value):
            if not isinstance(value, str):
                raise ValueError("Field value must be a string")
            return value

    class ArgumentsField(AbstractField):
        def validate_field(self, value):
            if not isinstance(value, dict):
                raise ValueError("Field value must be a dictionary")
            return value

    class EmailField(AbstractField):
        def validate_field(self, value):
            if not re.match(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)", str(value)):
                raise ValueError("Field value must be a correctly email")
            return value

    class PhoneField(AbstractField):
        def validate_field(self, value):
            if not re.match(r"(^7[\d]{10}$)", str(value)):
                raise ValueError("Field value must be a correctly phone number")
            return value

    class DateField(AbstractField):
        def validate_field(self, value):
            try:
                value = datetime.datetime.strptime(value, "%d.%m.%Y")
            except Exception:
                raise ValueError("Field value must be a correctly date")
            return value

    class BirthDayField(DateField):
        def validate_field(self, value):
            birthdaylimit = 70
            value = super(BirthDayField, self).validate_field(value)
            if datetime.datetime.now().year - value.year > birthdaylimit:
                raise ValueError("Field value must be no more then 70 y.o.")
            return value

    class GenderField(AbstractField):
        def validate_field(self, value):
            if value not in GENDERS.values():
                raise ValueError("Field value must be correctly gender")
            return value

    class ClientIDsField(AbstractField):
        def validate_field(self, value):
            if not isinstance(value, list):
                raise ValueError("Field value must be list of client ids")
            if not all(isinstance(item, int) for item in value):
                raise ValueError("List value of client ids must be integer")
            return value
