import json
import string
import pytz
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

tz = pytz.timezone('Africa/Kigali')

endpoint = "http://143.110.160.225/"


def cleaned_value(s):
    s = str(s)
    return s.translate({ord(c): None for c in string.whitespace})


def get_token(company):
    headers = {"Content-Type": 'application/json'}
    data = json.dumps({"username": company.mrc, "password": company.sdc_access_key})
    if data:
        url = f"{endpoint}/accounts/api/token/"
        response = requests.post(url, data=data, headers=headers,verify=False)
        if response.status_code == 200:
            return response.json()
    return


# def get_request_xml(template, data):
#     if template:
#         file = os.path.join(BASE_DIR, f'templates/{template}')
#         if not os.path.isfile(file):
#             return
#         dom = minidom.parse(file)
#         is_valid_element = lambda child: type(child) == minidom.Element
#         if data:
#             tags = [dom.getElementsByTagName('tin')[0]]
#             wrapper = dom.getElementsByTagName('data')[0]
#             tags += [child for child in wrapper.childNodes if is_valid_element(child)]
#             for tag in tags:
#                 key = tag.tagName
#                 if key in data:
#                     tag.firstChild.data = data[key]
#         return dom.toxml(encoding="ISO-8859-1")
#     return


class Messenger:
    def __init__(self, company, data=None, method='post', url=endpoint):
        self.company = company
        self.method = method
        self.url = url
        self.data = data
        self.template = None

    # def send_xml(self):
    #     token = get_token(self.company)
    #     if token:
    #         access_token = token['access']
    #         xml_data = get_request_xml(self.template, self.data)
    #         if xml_data:
    #             headers = {'Content-Type': 'text/xml;charset=ISO-8859-1', "Authorization": "Bearer %s" % access_token}
    #             r = requests.request(self.method, self.url, data=xml_data, headers=headers)
    #             if r.status_code == 200:
    #                 return r.content.decode("ISO-8859-1")
    #     return

    def send(self, cmd):
        token = get_token(self.company)
        if token and self.data:
            data = json.dumps({"cmd": cmd, "tin": self.company.vat or "", "data": self.data})
            access_token = token['access']
            headers = {'Content-Type': 'application/json', "Authorization": "Bearer %s" % access_token}
            r = requests.request(self.method, self.url, data=data, headers=headers)
            print(r.json())
            return r.status_code == 200 and r.json() or None
        return

    # def send_purchase(self):
    #     return self.send("SEND_PURCHASE")

    def send_receipt(self):
        print("sending receipt with...", self.data)
        return self.send("SEND_RECEIPT")

    def recv_receipt(self, receipt_number):
        return self.send("RECV_RECEIPT")

    def counters_request(self):
        return self.send("COUNTERS_REQUEST")

    def signature_request(self):
        return self.send("SIGNATURE_REQUEST")

    def date_time_request(self):
        return self.send("DATE_TIME_REQUEST")

    def id_request(self):
        return self.send("ID_REQUEST")

    def send_invoice(self):
        return self.send("EJ_DATA")

    def status_request(self):
        return self.send("STATUS_REQUEST")

    def send_receiptitem(self):
        return self.send("SEND_RECEIPTITEM")
