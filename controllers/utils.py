import string
from xml.dom import minidom
from xml.parsers.expat import ExpatError


def cleaned_value(s):
    s = str(s)
    return s.translate({ord(c): None for c in string.whitespace})


def success_response(response):
    if not response:
        return
    try:
        if type(response) == dict:
            assert response["status"] == "P"
            return True
        else:
            dom = minidom.parseString(response)
            status = dom.getElementsByTagName('status')
            val = status and cleaned_value(status[0].firstChild.data)
        return val == 'P'
    except (AssertionError, ExpatError, ValueError, KeyError):
        return False
