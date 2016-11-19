import os
import re

from flask import current_app
from flask import Flask
from flask import g
from flask_login import LoginManager
from werkzeug.local import LocalProxy

from wiki.core import Wiki
from wiki.wikigit import WikiGit
from wiki.web.user import UserManager


class WikiError(Exception):
    pass

def get_wiki():
    ENGINE = Wiki if not current_app.config.get('USE_GIT') else WikiGit
    wiki = getattr(g, '_wiki', None)
    if wiki is None:
        wiki = g._wiki = ENGINE(current_app.config['CONTENT_DIR'])
    return wiki

current_wiki = LocalProxy(get_wiki)

def get_users():
    users = getattr(g, '_users', None)
    if users is None:
        users = g._users = UserManager(current_app.config['CONTENT_DIR'])
    return users

current_users = LocalProxy(get_users)


def create_app(directory):
    app = Flask(__name__)
    app.config['CONTENT_DIR'] = directory
    app.config['TITLE'] = u'wiki'
    try:
        app.config.from_pyfile(
            os.path.join(app.config.get('CONTENT_DIR'), 'config.py')
        )
    except IOError:
        msg = "You need to place a config.py in your content directory."
        raise WikiError(msg)

    loginmanager.init_app(app)

    from wiki.web.routes import bp
    app.register_blueprint(bp)

    return app


loginmanager = LoginManager()
loginmanager.login_view = 'wiki.user_login'

@loginmanager.user_loader
def load_user(name):
    return current_users.get_user(name)


def get_app_routes_leading_elements():
    """
    Return set of leading url parts (string between first two slashes),
    which does not contains flask regex inside, and was registred using
    @app.route() decorator. Root url ('/') is ommited.
    """
    # get list of rules registred using @app.route()
    urls = [rule.rule for rule in current_app.url_map.iter_rules()]
    # tranform urls into strings between first two slashes
    urls = map(lambda url: url.split('/')[1], urls)
    # return set of those which does not contains '<' or '>' char
    # (as @app.route('/<path:url>/') will create)
    return set(filter(lambda elem: elem and re.match('[^<>]', elem), urls))
