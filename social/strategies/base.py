import time
import random
import hashlib

from social.utils import setting_name
from social.store import OpenIdStore


class BaseTemplateStrategy(object):
    def __init__(self, strategy):
        self.strategy = strategy

    def render(self, tpl=None, html=None, context=None):
        if not tpl and not html:
            raise ValueError('Missing template or html parameters')
        context = context or {}
        if tpl:
            return self.render_template(tpl, context)
        else:
            return self.render_string(html, context)

    def render_template(self, tpl, context):
        raise NotImplementedError('Implement in subclass')

    def render_string(self, html, context):
        raise NotImplementedError('Implement in subclass')


class BaseStrategy(object):
    ALLOWED_CHARS = 'abcdefghijklmnopqrstuvwxyz' \
                    'ABCDEFGHIJKLMNOPQRSTUVWXYZ' \
                    '0123456789'

    def __init__(self, backend=None, storage=None, request=None, tpl=None,
                 backends=None, *args, **kwargs):
        tpl = tpl or BaseTemplateStrategy
        if not isinstance(tpl, BaseTemplateStrategy):
            tpl = tpl(self)
        self.tpl = tpl
        self.request = request
        self.storage = storage
        self.backends = backends
        if backend:
            self.backend_name = backend.name
            self.backend = backend(strategy=self, *args, **kwargs)
        else:
            self.backend_name = None
            self.backend = backend

    def setting(self, name, default=None):
        names = (setting_name(self.backend_name, name),
                 setting_name(name),
                 name)
        for name in names:
            try:
                return self.get_setting(name)
            except (AttributeError, KeyError):
                pass
        return default

    def start(self):
        # Clean any partial pipeline info before starting the process
        self.clean_partial_pipeline()
        if self.backend.uses_redirect():
            return self.redirect(self.backend.auth_url())
        else:
            return self.html(self.backend.auth_html())

    def complete(self, *args, **kwargs):
        return self.backend.auth_complete(*args, **kwargs)

    def continue_pipeline(self, *args, **kwargs):
        return self.backend.continue_pipeline(*args, **kwargs)

    def disconnect(self, user, association_id=None):
        self.storage.user.disconnect(name=self.backend.name, user=user,
                                     association_id=association_id)

    def authenticate(self, *args, **kwargs):
        kwargs['strategy'] = self
        kwargs['storage'] = self.storage
        kwargs['backend'] = self.backend
        return self.backend.authenticate(*args, **kwargs)

    def create_user(self, *args, **kwargs):
        return self.storage.user.create_user(*args, **kwargs)

    def get_user(self, *args, **kwargs):
        return self.storage.user.get_user(*args, **kwargs)

    def session_setdefault(self, name, value):
        self.session_set(name, value)
        return self.session_get(name)

    def to_session(self, next, backend, *args, **kwargs):
        return {
            'next': next,
            'backend': backend.name,
            'args': args,
            'kwargs': kwargs
        }

    def from_session(self, session):
        return session['next'], session['backend'], \
               session['args'], session['kwargs']

    def clean_partial_pipeline(self):
        self.session_pop('partial_pipeline')

    def openid_store(self):
        return OpenIdStore(self)

    def get_pipeline(self):
        return self.setting('PIPELINE', (
            'social.pipeline.social_auth.social_user',
            'social.pipeline.user.get_username',
            'social.pipeline.user.create_user',
            'social.pipeline.social_auth.associate_user',
            'social.pipeline.social_auth.load_extra_data',
            'social.pipeline.user.user_details'
       ))

    def random_string(self, length=12, chars=ALLOWED_CHARS):
        # Implementation borrowed from django 1.4
        try:
            random.SystemRandom()
        except NotImplementedError:
            key = self.setting('SECRET_KEY', '')
            seed = '%s%s%s' % (random.getstate(), time.time(), key)
            random.seed(hashlib.sha256(seed.encode()).digest())
        return ''.join([random.choice(chars) for i in range(length)])

    def is_integrity_error(self, exception):
        return self.storage.is_integrity_error(exception)

    # Implement the following methods on strategies sub-classes

    def redirect(self, url):
        """Return a response redirect to the given URL"""
        raise NotImplementedError('Implement in subclass')

    def get_setting(self, name):
        """Return value for given setting name"""
        raise NotImplementedError('Implement in subclass')

    def html(self, content):
        """Return HTTP response with given content"""
        raise NotImplementedError('Implement in subclass')

    def render_html(self, tpl=None, html=None, context=None):
        """Render given template or raw html with given context"""
        return self.tpl.render(tpl, html, context)

    def request_data(self, merge=True):
        """Return current request data (POST or GET)"""
        raise NotImplementedError('Implement in subclass')

    def request_host(self):
        """Return current host value"""
        raise NotImplementedError('Implement in subclass')

    def session_get(self, name, default=None):
        """Return session value for given key"""
        raise NotImplementedError('Implement in subclass')

    def session_set(self, name, value):
        """Set session value for given key"""
        raise NotImplementedError('Implement in subclass')

    def session_pop(self, name):
        """Pop session value for given key"""
        raise NotImplementedError('Implement in subclass')

    def build_absolute_uri(self, path=None):
        """Build absolute URI with given (optional) path"""
        raise NotImplementedError('Implement in subclass')

    def is_response(self, value):
        raise NotImplementedError('Implement in subclass')
