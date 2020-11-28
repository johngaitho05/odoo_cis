odoo.define("odoo_cis.pos", function(require) {
    "use strict";

    var Screens = require('point_of_sale.screens');
    var pos_reprint = require('pos_reprint.pos_reprint');
    var core = require('web.core');
    var framework = require("web.framework")
    var pos_models = require('point_of_sale.models');
    var QWeb = core.qweb;
    var _t = core._t;

    var module = require('point_of_sale.models');

    var models = module.PosModel.prototype.models;

    for(var i=0; i<models.length; i++){

        var model=models[i];

        if(model.model === 'res.company'){
            model.fields.push('default_customer','mrc');

        }
        if(model.model === 'account.tax'){
            model.fields.push('description');
        }

    }
    Screens.PaymentScreenWidget.include({
        validate_order: function(force_validation) {
            let self = this
            let order = this.pos.get_order()
            if (!order.get_client()){
                this.gui.show_popup('confirm',{
                    'title': _t('Please select the Customer'),
                    'body': _t('You need to select the customer before you can invoice an order.'),
                    confirm: function(){
                        self.gui.show_screen('clientlist', null, false);
                    },
                });

            }else
            if (this.order_is_valid(force_validation)) {
                order.set_to_invoice(true)
                this.finalize_validation();
            }
        },


    })
    Screens.ActionpadWidget.include({
        renderElement: function() {
            var self = this;
            this._super();
            this.$('.pay').click(function(){
                self.set_default_client()
                var order = self.pos.get_order();
                var has_valid_product_lot = _.every(order.orderlines.models, function(line){
                    return line.has_valid_product_lot();
                });
                if(!has_valid_product_lot){
                    self.gui.show_popup('confirm',{
                        'title': _t('Empty Serial/Lot Number'),
                        'body':  _t('One or more product(s) required serial/lot number.'),
                        confirm: function(){
                            self.gui.show_screen('payment');
                        },
                    });
                }else{
                    self.gui.show_screen('payment');
                }
            });
            this.$('.set-customer').click(function(){
                self.gui.show_screen('clientlist');
            });
        },
        set_default_client: function() {
            let client = this.pos.company.default_customer
            let order = this.pos.get_order()
            if (order && client && !order.get_client()) {
                client = this.pos.db.get_partner_by_id(client[0])
                order.set_client(client)
            }
        }
    })
    pos_reprint.ReprintReceiptScreenWidget.include({
        show: function(){
            this.gui.show_screen('receipt',{"reprint":true});
        },
    });

    Screens.ReceiptScreenWidget.include({
        stamp: null,
        show: async function(){
            let self = this;
            let copy=false,refund=false;
            let _super = this._super.bind(this);
            if(this.is_reprint()){
                copy = true
            }
            this.stamp = await this.get_stamp(copy)
            if(this.stamp){
                _super()
                this.render_change();
                this.render_receipt();
                this.handle_auto_print();
            }
        },

        generate_receipt_QR_code:function(value){
            let qr;
            let element = document.getElementById('receipt-qr-code');
            if(element){
                qr = new QRious({
                    element: element,
                    size: 70,
                    value: value
                });
            }
        },
        clear_junk: function(receipt_number){
            const ajax = require("web.ajax");
            ajax.jsonRpc(
                '/cis/clear-junk',
                "call", {"receipt_number":receipt_number},
            ).catch(function(error) {
                if(error){
                    if(error){
                        console.log(error)
                    }
                }
            });
        },
        render_receipt: function() {
            let stamp = this.stamp
            let receipt_data = this.get_receipt_render_env()
            let receipt = receipt_data.receipt
            console.log("receipt",receipt)
            receipt["stamp"] = stamp.stamp
            receipt["client"] = stamp.client
            receipt["is_refund"] = stamp && stamp.stamp.RLabel.indexOf('R') !== -1
            receipt["is_copy"] = stamp && stamp.stamp.RLabel.indexOf('C') !== -1
            receipt.company["mrc"] = this.pos.company.mrc
            this.$('.pos-receipt-container').html(QWeb.render('OrderReceipt', receipt_data));
            if (!this.is_reprint()){
                let qr_value  = `${stamp["date"]}#${stamp["time"]}#${stamp["snum"]}#${stamp["rnum"]}#${stamp["internaldata"]}#${stamp["signature"]}`
                this.generate_receipt_QR_code(qr_value)
            }
            this.pos["last_receipt_render_env"] = receipt_data
            // this.clear_junk(stamp.rnum)
        },
        is_reprint:function(){
            try {
                let order = this.pos.get_order()
                let reprint = order.screen_data["params"]["reprint"]
                return !!reprint;
            } catch(e){
                return false
            }
        },
        get_receipt_render_env:function(){
            if(this.is_reprint()){
                return  this.pos.last_receipt_render_env
            }else{
                let order = this.pos.get_order();
                return {
                    widget: this,
                    pos: this.pos,
                    order: order,
                    receipt: order.export_for_printing(),
                    orderlines: order.get_orderlines(),
                    paymentlines: order.get_paymentlines(),
                };
            }
        },

        get_stamp: function(is_copy=false){
            let self = this;
            let order, order_uid
            if(this.is_reprint()){
                order = this.pos.last_receipt_render_env.order
            }else{
                order = this.pos.get_order()
            }
            order_uid = order.uid
            return  self._get_stamp(order_uid, is_copy);
        },
        _get_stamp:function(order_uid, is_copy){
            var self = this;
            const ajax = require("web.ajax");
            return new Promise((resolve, reject)=>{
                self.update_receipt_status("Processing receipt...","connecting")
                resolve(
                    ajax.jsonRpc(
                        '/cis/get-receipt-stamp',
                        "call", {"order_uid":order_uid,"is_copy":is_copy},
                    ).then(function(data) {
                        let code =data["code"]
                        if(code === 0){
                            $("#receipt-status-tracker").addClass("hidden");
                            self.update_receipt_status("Processing receipt...","connected")
                            return {stamp: self.export_stamp_for_printing(data["stamp"]),client:data["client"]}

                        } else{
                            self.update_receipt_status(data["message"],"error")
                        }
                    }).catch(function(error) {
                        if(error){
                            console.error(error)
                        }
                    })
                )
                reject("an error occured while retrieving VSDC response")
            })

        },
        //TODO update me to display feedback to user
        update_receipt_status:function(status_text,state){
            console.log(status_text)
            if (['connected', 'connecting', 'error', 'disconnected'].indexOf(state) === -1) {
                console.error(state, ' is not a known connection state.');
            }
            if (state === "connecting"){
                framework.blockUI();
            }else{
                framework.unblockUI();
            }
        },
        get_dashed_string: function(str, n) {
            let dashed = "";
            let i,len;

            for(i = 0, len = str.length; i < len; i += n) {
                if (dashed.length){
                    dashed+= `-${str.substr(i, n)}`
                }else{
                    dashed  = str.substr(i, n)
                }
            }

            return dashed
        },
        export_stamp_for_printing: function(data) {
            for (const [key, value] of Object.entries(data)) {
                if(key === 'signature' || key === 'internalData'){
                    data[key] = this.get_dashed_string(value,4)
                }
            }
            return data
        }
    })

    pos_models.Orderline.extend({
        get_tax_base: function () {
            return this.get_all_prices().taxableAmt;
        },
        get_all_prices: function(){
            var self = this;

            var price_unit = this.get_unit_price() * (1.0 - (this.get_discount() / 100.0));
            var taxtotal = 0;
            var taxable = 0;
            var product =  this.get_product();
            var taxes_ids = product.taxes_id;
            var taxes =  this.pos.taxes;
            var taxdetail = {};
            var product_taxes = [];

            _(taxes_ids).each(function(el){
                var tax = _.detect(taxes, function(t){
                    return t.id === el;
                });
                product_taxes.push.apply(product_taxes, self._map_tax_fiscal_position(tax));
            });
            product_taxes = _.uniq(product_taxes, function(tax) { return tax.id; });

            var all_taxes = this.compute_all(product_taxes, price_unit, this.get_quantity(), this.pos.currency.rounding);
            var all_taxes_before_discount = this.compute_all(product_taxes, this.get_unit_price(), this.get_quantity(), this.pos.currency.rounding);
            _(all_taxes.taxes).each(function(tax) {
                taxtotal += tax.amount;
                taxdetail[tax.id] = tax.amount;
                taxable  += tax.base
            });
            return {
                "priceWithTax": all_taxes.total_included,
                "priceWithoutTax": all_taxes.total_excluded,
                "priceSumTaxVoid": all_taxes.total_void,
                "priceWithTaxBeforeDiscount": all_taxes_before_discount.total_included,
                "tax": taxtotal,
                "taxDetails": taxdetail,
                "taxableAmt":taxable,
            };
        },
    })
    pos_models.Order.extend({
        get_tax_details: function(){
            var details = {};
            var fulldetails = [];

            this.orderlines.each(function(line){
                var ldetails = line.get_tax_details();
                var base_amt = line.get_tax_base()
                for(var id in ldetails){
                    if(ldetails.hasOwnProperty(id)){
                        let amt = ldetails[id]
                        if (details[id]){
                            details[id].amount += amt;
                            details[id].base += base_amt;
                        }else{
                            details[id] = {amount:amt,base:base_amt}
                        }
                    }
                }
            });

            for(var id in details){
                if(details.hasOwnProperty(id)){
                    fulldetails.push({amount: details[id].amount, tax: this.pos.taxes_by_id[id], name: this.pos.taxes_by_id[id].name,description:this.pos.taxes_by_id[id].description, base:details[id].base});
                }
            }
            console.log("fulldetails:",fulldetails)
            return fulldetails;
        },
    })
})
