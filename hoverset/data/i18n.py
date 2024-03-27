import gettext
import functools

from hoverset.data.utils import get_resource_path

app_name = "hoverset"
locale_dir = get_resource_path('hoverset.data', "locale")

_translators_core = {}
_translators = {}


def set_locale(locale):
    for appname, localedir in _translators_core.values():
        translator = gettext.translation(appname, localedir, fallback=True, languages=[locale])
        _translators[appname] = translator


def register_translator(appname, localedir):
    global _translators
    _translators_core[appname] = (appname, localedir)


def _translator(appname, message):
    if appname not in _translators:
        return message
    return _translators[appname].gettext(message)


register_translator(app_name, locale_dir)
set_locale("en")

_ = functools.partial(_translator, app_name)
