import json

import pytz
from odoo import models, fields, _, api
from odoo.addons.odoo_cis.controllers.api_calls import Messenger
from .utils import Miner, success_response, get_client_message
from odoo.exceptions import UserError

tz = pytz.timezone("Africa/Kigali")


def is_sales_invoice(invoice):
    return invoice and (invoice.type == ('out_invoice' or 'out_refund' or 'out_receipt'))


def is_purchase_invoice(invoice):
    return invoice and (invoice.type == ('in_invoice' or 'in_refund' or 'in_receipt'))


class ResPartner(models.Model):
    _inherit = "res.partner"

    sdc_id = fields.Char(string="SDC ID")
    mrc = fields.Char(string="MRC", unique=True)


class ResCompany(models.Model):
    _inherit = "res.company"

    sdc_id = fields.Char(string="SDC ID")
    mrc = fields.Char(string="MRC", unique=True)
    sdc_access_key = fields.Char(string="SDC Access Key")
    default_customer = fields.Many2one('res.partner', 'Default Customer')


class SupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    categ_code = fields.Char('Vendor product category',
                             help="This vendor's product category code will be used when printing a request for quotation. Keep empty to use the internal one.")


class AccountMove(models.Model):
    _inherit = "account.move"

    receipt_number = fields.Integer(readonly=True, default=0, String="Receipt ID", copy=False)
    copies_count = fields.Integer(readonly=True, string="Receipt Reprint Count")
    send_purchase = fields.Binary(compute="_send_purchase")
    send_receipt = fields.Binary(compute='_send_receipt')

    def _send_receipt(self):
        for invoice in self:
            data = {}
            if is_sales_invoice(invoice):
                data = Miner().get_sale_receipt_data(invoice)
            invoice.send_receipt = data

    def _send_purchase(self):
        for invoice in self:
            data = {}
            if is_purchase_invoice(invoice):
                data = Miner().get_purchase_data(invoice)
            invoice.send_purchase = data

    @api.model
    def create(self, values, *args, **kwargs):
        sales_invoices = self.env["account.move"].search(
            ['|', ('type', '=', 'out_invoice'), ('type', '=', 'out_refund')],
            order="id desc")
        receipt_number = sales_invoices and (sales_invoices[0].receipt_number + sales_invoices[0].copies_count + 1) or 1
        print("receipt_number", receipt_number)
        invoice = super(AccountMove, self).create(values, *args, **kwargs)
        if is_sales_invoice(invoice):
            invoice.receipt_number = receipt_number
            res = Messenger(invoice.company_id, invoice.send_receipt).send_receipt()
            try:
                assert success_response(res)
                key = f'stamp-{receipt_number}'
                try:
                    with open("vsdc_responses.json", "r") as f:
                        data = json.load(f)
                    data[key] = res

                    with open("vsdc_responses.json", "w") as f:
                        json.dump(data, f)

                except FileNotFoundError:
                    data = {key: res}
                    with open("vsdc_responses.json", "w+") as f:
                        json.dump(data, f)
            except AssertionError:
                invoice.unlink()
                raise UserError(_(f"Unexpected VSDC response {get_client_message(res)}"))
            except:
                invoice.unlink()
                raise UserError(_("Unable to connect to VSDC"))
        return invoice


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    send_purchaseitem = fields.Binary(compute="_send_purchaseitem")
    send_receiptitem = fields.Binary(compute='_send_receiptitem')
    send_import_item = fields.Binary(compute='_send_import_item')

    def _send_receiptitem(self):
        for line in self:
            data = {}
            if is_sales_invoice(line.move_id):
                data = Miner().get_sale_receiptitem_data(line)
            line.send_receiptitem = data

    def _send_purchaseitem(self):
        for line in self:
            data = {}
            if is_purchase_invoice(line.move_id):
                data = Miner().get_purchaseitem_data(line)
            line.send_purchaseitem = data

    def _send_import_item(self):
        for line in self:
            data = {}
            if is_purchase_invoice(line.move_id):
                buyer_country = line.company_id.country_id
                seller_country = line.partner_id.country_id
                if (buyer_country and seller_country) and (buyer_country != seller_country):
                    data = Miner().get_import_item_data(line)
            line.send_import_item = data


class ProductProduct(models.Model):
    _inherit = 'product.product'

    send_inventory = fields.Binary(compute="_send_inventory")
    send_item = fields.Binary(compute="_send_item")

    def _send_inventory(self):
        for product in self:
            print(product.company_id.name)
            data = Miner().get_inventory_data(product)
            product.send_inventory = data

    def _send_item(self):
        for product in self:
            print(product.company_id.country_id)
            data = Miner().get_item_data(product)
            product.send_item = data

# class PurchaseOrder(models.Model):
#     _inherit = "purchase.order"
#
#     send_purchase = fields.Binary(compute="_send_purchase")
#     send_item = fields.Binary(compute="_send_item")
#
#     @api.depends('invoice_ids', 'company_id', 'partner_id', 'name', 'order_line', 'activity_user_id', )
#     def _send_purchase(self):
#         for order in self:
#             data = Miner().get_purchase_data(order)
#             order.send_purchase = data
#
#     def _send_item(self):
#         for order in self:
#             data = Miner().get_purchaseitem_data(order)
#             order.send_item = data

# def _send_import_item(self):
#     for order in self:
#         data = {
#             "operationCd": "1141093",
#             "dclrtDateKey":
#         }

# class PosOrder(models.Model):
#     _inherit = 'pos.order'
#
#     receipt_number = fields.Integer(readonly=True, String="Receipt ID", copy=False)
#     copies_count = fields.Integer(readonly=True, default=0, string="Receipt Reprint Count")
#
#     # Sending receipt data before saving a POS order
#     @api.model
#     def create(self, values):
# orders = self.env["pos.order"].search([], order="id desc")
# last_number = orders and (orders[0].receipt_number + orders[0].copies_count) + 1 or 1
# order = super(PosOrder, self).create(values)
# order.receipt_number = last_number
# miner = Miner()
# receipt = miner.get_pos_receipt_data(order)
# receipt_items = miner.get_pos_receiptitem_data(order)
# company = order.company_id
# try:
#     response1 = Request(company, receipt).send_receipt()
#     response2 = Request(company, {"receipt_items": receipt_items}).send_receiptitem()
#     if not (success_response(response1) and success_response(response2)):
#         order.unlink()
#         error = get_client_message(response1) or get_client_message(response2) or "None"
#         raise UserError(_(f"Unexpected response from VSDC: {error}"))
# except:
#     raise UserError(_(f"Unable to connect to the VSDC"))
# return order
