"""
    Forms
    ~~~~~
"""
from flask_wtf import Form
from wtforms import BooleanField
from wtforms import TextField
from wtforms import TextAreaField
from wtforms import PasswordField
from wtforms.validators import InputRequired
from wtforms.validators import ValidationError

from wiki.core import Processors
from wiki.web import current_wiki
from wiki.web import current_users
from wiki.web import get_app_routes_leading_elements


class URLForm(Form):
    url = TextField('', [InputRequired()])

    def validate_url(form, field):
        sanitized_url = Processors.clean_url(field.data)
        system_urls_lead_parts = get_app_routes_leading_elements()
        # Disallow create already used urls.
        # NOTE I'm not sure whether Windows slashes do not need to be
        # sanitized later. At least space to underscore is necessary to check
        # now - or maybe in the Wiki object itself.
        # Leading url part (before slash) must not equals to system urls
        # leading parts (/create/, /edit/ and so on).
        if (current_wiki.exists(sanitized_url) or
                sanitized_url.split('/')[0] in system_urls_lead_parts):
            raise ValidationError(
                'The URL "%s" exists already.' % sanitized_url)

    def clean_url(self, url):
        return Processors.clean_url(url)


class SearchForm(Form):
    term = TextField('', [InputRequired()])
    ignore_case = BooleanField(
        description='Ignore Case',
        # FIXME: default is not correctly populated
        default=True)


class EditorForm(Form):
    title = TextField('', [InputRequired()])
    body = TextAreaField('', [InputRequired()])
    tags = TextField('')


class LoginForm(Form):
    name = TextField('', [InputRequired()])
    password = PasswordField('', [InputRequired()])

    def validate_name(form, field):
        user = current_users.get_user(field.data)
        if not user:
            raise ValidationError('This username does not exist.')

    def validate_password(form, field):
        user = current_users.get_user(form.name.data)
        if not user:
            return
        if not user.check_password(field.data):
            raise ValidationError('Username and password do not match.')
