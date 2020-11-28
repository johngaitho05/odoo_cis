# -*- coding: utf-8 -*-
import json
import os
from threading import Thread
from xml.dom import minidom
from .utils import success_response
from .api_calls import Messenger
import pytz
from odoo import http

tz = pytz.timezone('Africa/Kigali')


# def get_responses_dir():
#     directory = os.path.join(BASE_DIR, 'vsdc_responses')
#     if not os.path.isdir(directory):
#         os.mkdir(directory)
#     return directory


def delete_file(path, *args):
    if os.path.isfile(path):
        os.remove(path)


class CisController(http.Controller):

    def get_client_response(self, response, receipt_number):
        dom = minidom.parseString(response)
        status = dom.getElementsByTagName('status')[0].firstChild.data
        message = dom.getElementsByTagName("description")[0].firstChild.data
        if status != "P":
            return {"code": 1, "message": f"VSDC responded with an error message: {message}"}
        return {"code": 0, "message": "waiting for VSDC response", "rnum": receipt_number}

    def send_receipt_copy(self, order):
        # try:
        move = order.account_move
        move.copies_count += 1
        data = move.send_receipt
        company = move.company_id
        response = Messenger(company, data).send_receipt()
        if success_response(response):
            return {"code": 0, "stamp": response,"client": order.partner_id.vat}
        return {"code": 1, "message": response}

    # except:
    #     pass
    # return {"code": 1, "message": "Unable to fetch stamp for the reprint"}

    # @http.route('/cis/send-receipt-callback', type='http', auth='public', website=False, csrf=False)
    # def receive_receipt_response(self):
    #     response = http.request.httprequest.data
    #     try:
    #         response = response.decode("ISO-8859-1")
    #         dom = minidom.parseString(response)
    #         name = f'receipt-{dom.getElementsByTagName("RNumber")[0].firstChild.data}.xml'
    #
    #         with open(f'{get_responses_dir()}/{name}', 'w+') as f:
    #             dom.writexml(f)
    #     except:
    #         pass
    #     return "OK"

    @http.route('/cis/get-receipt-stamp', type='json', auth='public', website=False, csrf=False)
    def get_receipt_stamp(self, **kwargs):
        uid = kwargs.get("order_uid")
        orders = http.request.env['pos.order'].sudo().search([("pos_reference", "=ilike", f'%{uid}')])
        try:
            assert len(orders) == 1
            order = orders[0]
            is_copy = kwargs.get("is_copy")
            receipt_number = order.account_move.receipt_number
            if is_copy:
                return self.send_receipt_copy(order)
            try:
                with open('vsdc_responses.json', 'r') as f:
                    data = json.load(f)
                    return {"code": 0, "stamp": data[f'stamp-{receipt_number}'], "client": order.partner_id.vat}
            except (FileNotFoundError, KeyError):
                return {"code": 1, "message": 'Unable to retrieve VSDC response'}
            # t = Thread(target=self.clear_junk, args=(receipt_number,))
            # t.start()
        except AssertionError:
            return {"code": 1, "message": " An error occured while contacting VSDC"}

    def clear_junk(self, receipt_number, *args):
        file = 'vsdc_responses.json'
        cleaner = Thread(target=delete_file, args=(file,))
        cleaner.start()
        return {"code": 0, "message": "OK"}
