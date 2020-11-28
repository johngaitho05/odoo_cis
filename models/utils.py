import os
import string
from collections import OrderedDict
from datetime import datetime
from decimal import Decimal
from xml.dom import minidom
from xml.parsers.expat import ExpatError
import pytz

tz = pytz.timezone("Africa/Kigali")


def _special(amount): return str(format(amount, ".2f"))


def _null(v): return 0 if type(v) in (int, float, Decimal) else ""


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


def get_client_message(response):
    try:
        if not response:
            return "None"
        if type(response) == dict:
            return response["status"] == "E" and response["description"]
        dom = minidom.parseString(response)
        has_error = dom.getElementsByTagName('status')[0].firstChild.data == "E"
        msg = dom.getElementsByTagName('description')[0].firstChild.data
        return has_error and msg

    except (AssertionError, ExpatError, ValueError, KeyError):
        return False


def cleaned_value(s):
    s = str(s)
    return s.translate({ord(c): None for c in string.whitespace})


class Miner:
    # def get_pos_receipt_data(self, order, is_copy=False):
    #     rtype = "C" if is_copy else "N"
    #     receipt_dt = order.create_date.astimezone(tz)
    #     request_dt = datetime.now(tz)
    #
    #     def trans_type(x): return "R" if x < 0 else "S"
    #
    #     data = {
    #         "tin": order.company_id.vat,
    #         "invId": (is_copy and order.receipt_number + order.copies_count) or order.receipt_number,
    #         "mrcNo": order.company_id.mrc,
    #         "bcncId": order.partner_id and order.partner_id.vat,
    #         "bcncPhone": order.partner_id.phone if order.partner_id else "",
    #         "refId": order.account_move.id if order.account_move else "",
    #         "transTyCd": trans_type(order.amount_total),
    #         "rcptTyCd": rtype,
    #         "validDt": datetime.strftime(receipt_dt, "%Y-%m-%d %H:%M:%S"),
    #         "rcptDt": datetime.strftime(receipt_dt, "%d%m%Y%H%M%S"),
    #         "journal": order.sale_journal.name,
    #         "regusrId": order.create_uid.id,
    #         "regusrNm": order.create_uid.name,
    #         "regDt": datetime.strftime(request_dt, "%Y-%m-%d %H:%M:%S"),
    #         "callbackUrl": f"{request.httprequest.host_url}cis/send-receipt-callback",
    #         "totTax": _special(order.amount_tax or 0),
    #         "totAmt": _special(order.amount_total or 0),
    #     }
    #
    #     tax_details = self.get_tax_details(order.lines, order.company_id, order.partner_id,
    #                                        is_refund=(trans_type == "R"), model='pos.order.line')
    #     print(tax_details)
    #     data.update({key: amt for key, amt in tax_details.items()})
    #     return data
    #
    # def get_pos_receiptitem_data(self, order):
    #     data = []
    #     for line in order.lines:
    #         sub_data = {
    #             "invId": order.receipt_number,
    #             "mrcNo": order.company_id.mrc,
    #             "bhfId": "",
    #             "itemSeq": line.product_id.sequence,
    #             "itemClsCd": line.product_id.pos_categ_id.id,
    #             "itemCd": line.product_id.barcode,
    #             "itemNm": line.product_id.display_name,
    #             "bcncId": order.partner_id and order.partner_id.vat,
    #             "pkgUnitCd": line.product_id.uom_po_id.id,
    #             "pkgQty": line.product_id.incoming_qty or 0,
    #             "qtyUnitCd": line.product_id.uom_name,
    #             "qty": line.qty or 0,
    #             "untpc": _special(line.price_unit or 0),
    #             "splpc": _special(line.product_id.standard_price or 0),
    #             "dcRate": _special(line.discount or 0),
    #             "dcAmt": _special((line.discount or 0.0) / 100 * line.price_subtotal),
    #             "taxablAmt": _special(line.price_subtotal or 0),
    #             "taxTyCd": tuple([tax.name for tax in line.tax_ids]),
    #             "tax": _special((line.price_subtotal_incl - line.price_subtotal) or 0),
    #             "totAmt": _special(line.price_subtotal_incl or 0),
    #         }
    #         sub_data = {k: (v or _null(v)) for k, v in sub_data.items()}
    #         data.append(sub_data)
    #     return data

    def get_purchase_data(self, invoice):
        def valid_date(date): return datetime.strftime(date, "%Y-%m-%d %H:%M:%S")

        def get_cancel_date():
            return invoice.state == 'cancel' and valid_date(alt_dt)

        dt = invoice.create_date.astimezone(tz)
        alt_dt = invoice.write_date.astimezone(tz)
        inv_status_codes = {'no': '01', 'to_invoice': '02', 'invoiced': '03', 'not_paid': '06', 'in_payment': '07',
                            'paid': '08'}
        inv_status = invoice.invoice_payment_state
        inv_code = inv_status in inv_status_codes and inv_status_codes[inv_status] or "01"
        data = {
            "invId": invoice and invoice.id,
            "tin": invoice.company_id.vat,
            "bcncId": invoice.partner_id.vat,
            "mrcNo": invoice.company_id.mrc,
            "bhfId": "",
            "sdcId": invoice.company_id.sdc_id,
            "bcncNm": invoice.partner_id.name,
            "bcncSdcId": invoice.partner_id.sdc_id,
            "bcncMrcNo": invoice.partner_id.mrc,
            "refId": invoice.ref,
            "regTyCd": "M",
            "invStatusCd": inv_code,
            "ocde": datetime.strftime(dt, "%Y%m%d"),
            "validDt": valid_date(dt),
            "cancelReqDt": get_cancel_date(),
            "cancelDt": get_cancel_date(),
            "refundDt": invoice.state == 'cancel' and valid_date(alt_dt),
            "cancelTyCd": "",
            "totTax": _special(invoice.amount_tax),
            "totAmt": _special(invoice.amount_total),
            "totSplpc": _special(invoice.amount_total),
            "regusrId": invoice.activity_user_id.id or invoice.user_id.id,
            "regDt": datetime.strftime(dt, "%Y%m%d%H%M%S"),
            "remark": invoice.narration,
            "payTyCd": "02",  # FIX ME:  get the real code dynamically
        }
        data = {k: (v or _null(v)) for k, v in data.items()}
        tax_details = Miner().get_tax_details(invoice.invoice_line_ids, invoice.company_id, invoice.partner_id,
                                              is_refund=(invoice.type == 'in_refund'))
        data.update(tax_details)

        return data

    def get_purchaseitem_data(self, line):
        invoice = line.move_id
        company = line.company_id

        def get_supplier_info(seller_ids, vendor):
            for seller in seller_ids:
                if seller == vendor:
                    return {"product_code": seller.product_code, "categ_code": seller.categ_code,
                            "product_name": seller.product_name}
            return

        def _compute_tax():
            tax_amt = 0
            for tax in line.tax_ids:
                computed = \
                    tax.compute_all(price_unit=line.price_unit, currency=company.currency_id,
                                    partner=invoice.partner_id,
                                    quantity=line.quantity,
                                    is_refund=line.price_total < 0,
                                    product=line.product_id)[
                        'taxes']
                tax_amt += computed[0]["amount"]
            return tax_amt

        seller_info = get_supplier_info(line.product_id.seller_ids, line.partner_id)
        data = {
            "invId": invoice.id,
            "refId": line.ref,
            "itemSeq": line.sequence,
            "itemClsCd": line.product_id.pos_categ_id.id,
            "itemCd": line.product_id.barcode or line.product_id.id,
            "itemNm": line.product_id.name,
            "bcncId": line.partner_id.vat,
            "bhfId": "",
            "bcncItemClsCd": seller_info and seller_info["categ_code"],
            "bcncItemCd": seller_info and seller_info["product_code"],
            "bcncItemNm": seller_info and seller_info["product_name"],
            "pkgUnitCd": line.product_id.uom_po_id.id,
            "pkgQty": _special(line.product_id.incoming_qty or 0),
            "qtyUnitCd": (line.product_id.packaging_ids and line.product_id.packaging_ids[0].id) or "KG",
            "qty": _special(line.quantity),
            "expirDt": "",  # line.product_id.life_time and line.product_id.life_time.date,
            "untpc": _special(line.price_unit),
            "splpc": _special(line.product_id.standard_price),
            "dcRate": _special(line.discount),
            "dcAmt": _special((line.discount or 0.0) / 100 * line.price_subtotal),
            "taxablAmt": _special(line.tax_base_amount),
            "taxTyCd": line.tax_ids and line.tax_ids[0].name,
            "tax": _special(_compute_tax()),
            "totAmt": _special(line.price_total),
            "regTyCd": "M"  # FIX ME: clarify what this is and change it's value
        }
        return {k: (v or _null(v)) for k, v in data.items()}

        # data = [_get_item(line) for line in invoice.line_ids]
        # return data

    def get_tax_details(self, lines, company, vendor, is_refund=False):
        tax_amounts = {}
        for line in lines:
            quantity = line.quantity
            tax_ids = line.tax_ids
            for tax in tax_ids:
                computed = tax.compute_all(price_unit=line.price_unit, currency=company.currency_id, partner=vendor,
                                           quantity=quantity, is_refund=is_refund, product=line.product_id)[
                    'taxes']
                if computed:
                    agg_amounts = {'rate': tax.amount}
                    computed_amounts = computed[0]
                    key = computed_amounts['name']
                    prev_amounts = tax_amounts[key] if key in tax_amounts else {"amount": 0.0, "base": 0.0}
                    agg_amounts.update(
                        {k: v + prev_amounts[k] for k, v in computed_amounts.items() if k in prev_amounts})
                    tax_amounts.update({key: agg_amounts})
        sequence = 'ABCD'
        rates = taxables = taxes = {}
        tax_amounts = list(OrderedDict(sorted(tax_amounts.items())).values())
        count = 0
        for i in range(len(tax_amounts)):
            obj = tax_amounts[i]
            rates.update({f'taxRate{sequence[i]}': obj["rate"]})
            taxables.update({f'totTaxablAmt{sequence[i]}': obj["base"]})
            taxes.update({f'totTax{sequence[i]}': obj["amount"]})
            count += 1
        for i in range(count, len(sequence)):
            rates.update({f'taxRate{sequence[i]}': 0})
            taxables.update({f'totTaxablAmt{sequence[i]}': 0})
            taxes.update({f'totTax{sequence[i]}': 0})
        result = {**rates, **taxables, **taxes}
        return {k: _special(v) for k, v in result.items()}

    def get_sale_receipt_data(self, invoice):
        rtype = (invoice.copies_count and "C") or "N"

        data = {
            "invId": invoice.receipt_number + invoice.copies_count,
            "mrcNo": invoice.company_id.mrc,
            "bcncId": invoice.partner_id.vat,
            "bcncPhone": invoice.partner_id.phone,
            "refId": invoice.ref if invoice.type == 'out_refund' else 0,
            "transTyCd": (invoice.type == 'out_refund' and "R") or "S",
            "rcptTyCd": rtype,
            "journal": invoice.journal_id.name,
            "regusrId": invoice.create_uid.id,
            "regusrNm": invoice.create_uid.name,
            "totTax": _special(invoice.amount_tax or 0),
            "totAmt": _special(invoice.amount_total or 0),
            "totNumItem": len(invoice.invoice_line_ids),
            "payTyCd": "02",  # FIX ME:  get the real code dynamically
        }
        data = {k: (v or _null(v)) for k, v in data.items()}
        tax_details = self.get_tax_details(invoice.invoice_line_ids, invoice.company_id, invoice.partner_id,
                                           invoice.amount_total < 0)

        return {**data, **tax_details}

    def get_sale_receiptitem_data(self, line):
        invoice = line.move_id

        def _compute_tax(lyne):
            tax_amt = 0
            for tax in lyne.tax_ids:
                computed = \
                    tax.compute_all(price_unit=lyne.price_unit,
                                    currency=invoice.company_id.currency_id,
                                    partner=invoice.partner_id,
                                    quantity=lyne.quantity,
                                    is_refund=lyne.price_total < 0,
                                    product=lyne.product_id)[
                        'taxes']
                tax_amt += computed[0]["amount"]
            return tax_amt

        data = {
            "invId": invoice.receipt_number,
            "mrcNo": invoice.company_id.mrc,
            "bhfId": "",
            "itemSeq": line.product_id.sequence,
            "itemClsCd": line.product_id.pos_categ_id.id,
            "itemCd": line.product_id.id,
            "itemNm": line.product_id.name,
            "bcncId": invoice.partner_id and invoice.partner_id.vat,
            "pkgUnitCd": line.product_id.uom_po_id.id,
            "pkgQty": line.product_id.incoming_qty or 0,
            "qtyUnitCd": (line.product_id.packaging_ids and line.product_id.packaging_ids[0].id) or "KG",
            "qty": line.quantity or 0,
            "untpc": _special(line.price_unit or 0),
            "splpc": _special(line.product_id.standard_price or 0),
            "dcRate": _special(line.discount or 0),
            "dcAmt": _special((line.discount or 0.0) / 100 * line.price_subtotal),
            "taxablAmt": _special(line.price_subtotal or 0),
            "taxTyCd": tuple([tax.name for tax in line.tax_ids]),
            "tax": _special(_compute_tax(line)),
            "totAmt": _special(line.price_total or 0),
        }

        return {k: (v or _null(v)) for k, v in data.items()}

    def get_item_data(self, product):
        product_types = ['consu', 'service']
        template = product.product_tmpl_id
        regdt = template.create_date
        updt = template.write_date
        country = (template.seller_ids and template.seller_ids[
            0].company_id.country_id) or product.company_id.country_id
        data = {
            'itemClsCd': template.categ_id.id,
            'itemCd': product.id or product.default_code,
            'itemNm': product.name or template.name,
            'itemTyCd': product_types.index(template.type) if template.type in product_types else 3,
            "itemStd": "",
            'orgplceCd': (country and (country.code or country.name)) or "RW",
            'pkgUnitCd': product.uom_po_id.id,
            'qtyUnitCd': (product.packaging_ids and product.packaging_ids[0].id) or "KG",
            'adiInfo': template.description,
            'initlWhUntpc': template.price,
            'initlQty': template.qty_available,
            'avgWhUntpc': template.lst_price or template.price,
            'dfltDlUntpc': template.list_price or template.price,
            'taxTyCd': template.taxes_id[0].name if template.taxes_id else 'A',
            'rm': template.description_pickingin,
            'useYn': "Y" if template.type == product_types[0] else "N",
            'regusrId': template.create_uid.id,
            'regDt': datetime.strftime(regdt.astimezone(tz), "%Y%m%d%H%M%S"),
            'updusrId': template.write_uid and template.write_uid.id,
            "updDt": updt and datetime.strftime(updt.astimezone(tz), "%Y%m%d%H%M%S"),
            'safetyQty': template.reordering_min_qty or 0,
            'useBarcode': (template.barcode and "Y") or "N",
            "changeYn": (updt and "Y") or "N",
            "useAdiYn": "Y",
        }

        return {k: (v or _null(v)) for k, v in data.items()}

    def get_import_item_data(self, line):
        invoice = line.move_id
        data = {
            "actionCd": "ACT",
            "operationCd": invoice.id,
            "dclrtDateKey": datetime.strftime(line.date, '%Y%m%d'),
            "itemSeq": line.product_id.id,
            "approvalStatusCd": (invoice.state == 'cancel' and 4) or 3,
            "remark": invoice.narration,
        }
        return {k: (v or _null(v)) for k, v in data.items()}

    def get_inventory_data(self, product):
        template = product.product_tmpl_id
        qty = template.qty_available
        data = {
            "tin": product.company_id.vat,
            "bhfId": "",
            'itemClsCd': template.categ_id.id,
            'itemCd': product.id or product.default_code,
            'qty': (qty > 0 and qty) or 0,
            'updDt': datetime.strftime(template.write_date.astimezone(tz), "%Y%m%d%H%M%S")
        }
        return {k: (v or _null(v)) for k, v in data.items()}
