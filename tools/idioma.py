"""Language of the installer messages: Spanish when Windows is in Spanish, English otherwise.
Set DBFZ_LANG=es or DBFZ_LANG=en to force one."""
import locale, os

def _spanish():
    forced = os.environ.get('DBFZ_LANG', '').lower()
    if forced: return forced.startswith('es')
    try:
        import ctypes
        return (ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3ff) == 0x0a   # LANG_SPANISH
    except Exception:
        return (locale.getlocale()[0] or '').lower().startswith(('es', 'spanish'))

ES = _spanish()

def t(es, en):
    return es if ES else en
