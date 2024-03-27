import functools
import logging

from hoverset.data.i18n import register_translator, _translator, set_locale
from hoverset.data.utils import get_resource_path
from hoverset.data.preferences import open_raw_shelve
import studio

app_name = "studio"
locale_dir = get_resource_path(studio, "resources/locale")
register_translator(app_name, locale_dir)

# set locale hack
try:
    with open_raw_shelve("formation", "hoverset", "config") as pref:
        locale = pref["locale"]["language"]
        set_locale(locale)
except Exception as e:
    logging.error(e)


_ = functools.partial(_translator, app_name)
