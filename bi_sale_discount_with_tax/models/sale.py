# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import odoo.addons.decimal_precision as dp
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
from odoo.tools import float_is_zero, float_compare


class sale_order(models.Model):
    _inherit = 'sale.order'

    @api.depends('discount_amount','discount_method','discount_type')
    def _calculate_discount(self):
        res=0.0
        discount = 0.0
        for self_obj in self:
            if self_obj.discount_method == 'fix':
                discount = self_obj.discount_amount
                res = discount
            elif self_obj.discount_method == 'per':
                discount = self_obj.amount_untaxed * (self_obj.discount_amount/ 100)
                res = discount
            else:
                res = discount
        return res


    @api.depends('order_line','order_line.price_total','order_line.price_subtotal',\
        'order_line.product_uom_qty','discount_amount',\
        'discount_method','discount_type' ,'order_line.discount_amount',\
        'order_line.discount_method','order_line.discount_amt')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        self.discount_amt = 0.0
        res_config= self.env['res.config.settings'].search([],order="id desc", limit=1)
        cur_obj = self.env['res.currency']
        for order in self:                      
            applied_discount = line_discount = sums = order_discount =  amount_untaxed = amount_tax = amount_after_discount =  0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
                applied_discount += line.discount_amt if line.discount_method == 'per' else (line.discount_amt * line.product_uom_qty)
    
                if line.discount_method == 'fix':
                    line_discount += line.discount_amount
                elif line.discount_method == 'per':
                    line_discount += line.price_subtotal * (line.discount_amount/ 100)            

            if res_config:
                if res_config.tax_discount_policy == 'tax':
                    if order.discount_type == 'line':
                        order.discount_amt = 0.00
                        order.update({
                            'amount_untaxed': amount_untaxed,
                            'amount_tax': amount_tax,
                            'amount_total': amount_untaxed + amount_tax - line_discount,
                            'discount_amt_line' : line_discount,
                        })

                    elif order.discount_type == 'global':
                        order.discount_amt_line = 0.00
                        
                        if order.discount_method == 'per':
                            order_discount = amount_untaxed * (order.discount_amount / 100)  
                            order.update({
                                'amount_untaxed': amount_untaxed,
                                'amount_tax': amount_tax,
                                'amount_total': amount_untaxed + amount_tax - order_discount,
                                'discount_amt' : order_discount,
                            })
                        elif order.discount_method == 'fix':
                            order_discount = order.discount_amount
                            order.update({
                                'amount_untaxed': amount_untaxed,
                                'amount_tax': amount_tax,
                                'amount_total': amount_untaxed + amount_tax - order_discount,
                                'discount_amt' : order_discount,
                            })
                        else:
                            order.update({
                                'amount_untaxed': amount_untaxed,
                                'amount_tax': amount_tax,
                                'amount_total': amount_untaxed + amount_tax ,
                            })
                    else:
                        order.update({
                            'amount_untaxed': amount_untaxed,
                            'amount_tax': amount_tax,
                            'amount_total': amount_untaxed + amount_tax ,
                            })
            if order.tax_discount_policy == True:
                if order.discount_type == 'line':
                    order.discount_amt = 0.00 
                    order.update({
                        'amount_untaxed': amount_untaxed,
                        'amount_tax': amount_tax,
                        'amount_total': amount_untaxed + amount_tax - applied_discount,
                        'discount_amt_line' : applied_discount,
                    })
                elif order.discount_type == 'global':
                    order.discount_amt_line = 0.00
                    if order.discount_method == 'per':
                        order_discount = amount_untaxed * (order.discount_amount / 100)
                        if order.order_line:
                            for line in order.order_line:
                                if line.tax_id:
                                    final_discount = 0.0
                                    try:
                                        final_discount = ((order.discount_amount*line.price_subtotal)/100.0)
                                    except ZeroDivisionError:
                                        pass
                                    discount = line.price_subtotal - final_discount
                                    taxes = line.tax_id.compute_all(discount, \
                                                        order.currency_id,1.0, product=line.product_id, \
                                                        partner=order.partner_id)
                                    sums += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                        order.update({
                            'amount_untaxed': amount_untaxed,
                            'amount_tax': sums,
                            'amount_total': amount_untaxed + sums - order_discount,
                            'discount_amt' : order_discount,  
                        })
                    elif order.discount_method == 'fix':
                        order_discount = order.discount_amount
                        if order.order_line:
                            for line in order.order_line:
                                if line.tax_id:
                                    final_discount = 0.0
                                    try:
                                        final_discount = ((order.discount_amount*line.price_subtotal)/amount_untaxed)
                                    except ZeroDivisionError:
                                        pass
                                    discount = line.price_subtotal - final_discount
                                    taxes = line.tax_id.compute_all(discount, \
                                                        order.currency_id,1.0, product=line.product_id, \
                                                        partner=order.partner_id)
                                    sums += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                        order.update({
                            'amount_untaxed': amount_untaxed,
                            'amount_tax': sums,
                            'amount_total': amount_untaxed + sums - order_discount,
                            'discount_amt' : order_discount,
                        })
                    else:
                        order.update({
                            'amount_untaxed': amount_untaxed,
                            'amount_tax': amount_tax,
                            'amount_total': amount_untaxed + amount_tax ,
                        })
                else:
                    order.update({
                        'amount_untaxed': amount_untaxed,
                        'amount_tax': amount_tax,
                        'amount_total': amount_untaxed + amount_tax ,
                        })
            else:
                order.update({
                        'amount_untaxed': amount_untaxed,
                        'amount_tax': amount_tax,
                        'amount_total': amount_untaxed + amount_tax ,
                        })         

    tax_discount_policy = fields.Boolean(default=True,related="company_id.tax_discount_policy")
    discount_method = fields.Selection([('fix', 'Fixed'), ('per', 'Percentage')], 'Discount Method')
    discount_amount = fields.Float('Discount Amount')
    discount_amt = fields.Monetary(compute='_amount_all', string='- Total Discount', digits='Discount', store=True, readonly=True)
    discount_type = fields.Selection([('line', 'Order Line'), ('global', 'Global')],string='Discount Applies to',default='global')
    discount_amt_line = fields.Float(compute='_amount_all', string='- Total Discount', digits='Line Discount', store=True, readonly=True)
    def _prepare_invoice(self):
        res = super(sale_order,self)._prepare_invoice()
        res.update({'discount_method': self.discount_method,
                'discount_amount': self.discount_amount,
                'discount_amt': self.discount_amt,
                'discount_type': self.discount_type,
                'discount_amt_line' : self.discount_amt_line,
                })
        return res



class sale_order_line(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id','discount_method','discount_amount')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            discount_price = 0.0
            disc_price = 0.0
            res_config= self.env['res.config.settings'].search([],order="id desc", limit=1)
            if self.env.company.tax_discount_policy == True:
            # if line.tax_discount_policy == True:
                if line.order_id.discount_type == 'line':
                    if line.discount_method == 'fix':
                        price = (line.price_unit * line.product_uom_qty) - line.discount_amount
                        taxes = line.tax_id.compute_all(price, line.order_id.currency_id, 1, product=line.product_id, partner=line.order_id.partner_shipping_id)
                        discount_price = line.price_unit - line.discount_amount
                        line.update({
                            'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                            'price_total': taxes['total_included'] + line.discount_amount,
                            'price_subtotal': taxes['total_excluded'] + line.discount_amount,
                            'discount_amt' : line.discount_amount,
                            'discount_unit_price':discount_price,
                            'discount_subtotal': discount_price * line.product_uom_qty
                        })
                    elif line.discount_method == 'per':
                        price_x = 0.0
                        price = (line.price_unit * line.product_uom_qty) * (1 - (line.discount_amount or 0.0) / 100.0)
                        price_x = ((line.price_unit * line.product_uom_qty) - (line.price_unit * line.product_uom_qty) * (1 - (line.discount_amount or 0.0) / 100.0))
                        taxes = line.tax_id.compute_all(price, line.order_id.currency_id, 1, product=line.product_id, partner=line.order_id.partner_shipping_id)
                        discount_price = (line.discount_amount/100) * line.price_unit
                        disc_price = line.price_unit - discount_price
                        line.update({
                            'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                            'price_total': taxes['total_included'] + price_x,
                            'price_subtotal': taxes['total_excluded'] + price_x,
                            'discount_amt' : price_x,
                            'discount_unit_price':disc_price,
                            'discount_subtotal': disc_price * line.product_uom_qty
                        })
                    else:
                        price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                        taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_shipping_id)
                        line.update({
                            'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                            'price_total': taxes['total_included'],
                            'price_subtotal': taxes['total_excluded'],
                        })
                else:
                    price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                    taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_shipping_id)
                    line.update({
                        'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                        'price_total': taxes['total_included'],
                        'price_subtotal': taxes['total_excluded'],
                    })
            if res_config:
                if res_config.tax_discount_policy == 'tax':
                    if line.order_id.discount_type == 'line':
                        price_x = 0.0
                        price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                        taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_shipping_id)

                        if line.discount_method == 'fix':
                            price_x = (taxes['total_included']) - ( taxes['total_included'] - line.discount_amount)
                        elif line.discount_method == 'per':
                            price_x = (taxes['total_included']) - (taxes['total_included'] * (1 - (line.discount_amount or 0.0) / 100.0))
                        else:
                            price_x = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                
                        line.update({
                            'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                            'price_total': taxes['total_included'],
                            'price_subtotal': taxes['total_excluded'],
                            'discount_amt' : price_x,
                        })
                    else:
                        price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                        taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_shipping_id)
                        line.update({
                            'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                            'price_total': taxes['total_included'],
                            'price_subtotal': taxes['total_excluded'],
                        })
                else:
                    price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                    taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_shipping_id)
                    
                    line.update({
                        'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                        'price_total': taxes['total_included'],
                        'price_subtotal': taxes['total_excluded'],
                    })
            else:
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_shipping_id)
                
                line.update({
                    'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                    'price_total': taxes['total_included'],
                    'price_subtotal': taxes['total_excluded'],
                })

    tax_discount_policy = fields.Boolean(default=True,related="company_id.tax_discount_policy")
    is_apply_on_discount_amount =  fields.Boolean("Tax Apply After Discount")
    discount_method = fields.Selection([('fix', 'Fixed'), ('per', 'Percentage')], 'Discount Method', default="fix")
    discount_type = fields.Selection(related='order_id.discount_type', string="Discount Applies to")
    discount_amount = fields.Float('Discount Amount')
    discount_amt = fields.Float('Discount Final Amount')
    discount_unit_price = fields.Float(string='Discount Unit Price')
    discount_subtotal = fields.Float(string='Discount Subtotal')




    @api.onchange('product_uom', 'product_uom_qty')
    def product_uom_change(self):
        if not self.product_uom or not self.product_id:
            self.price_unit = 0.0
            return
        if self.order_id.pricelist_id and self.order_id.partner_id:
            product = self.product_id.with_context(
                lang=self.order_id.partner_id.lang,
                partner=self.order_id.partner_id,
                quantity=self.product_uom_qty,
                date=self.order_id.date_order,
                pricelist=self.order_id.pricelist_id.id,
                uom=self.product_uom.id,
                fiscal_position=self.env.context.get('fiscal_position')
            )
            if not self.price_unit:
                self.price_unit = self.env['account.tax']._fix_tax_included_price_company(self._get_display_price(product), product.taxes_id, self.tax_id, self.company_id)


    @api.onchange('discount_unit_price')
    def validate_discount(self):
        for rec in self:
            if rec.discount_method:
                if rec.discount_unit_price > rec.price_unit:
                    rec.discount_unit_price = rec.discount_subtotal/rec.product_uom_qty if rec.product_uom_qty else 0
                    return {'warning' : {
                            'title': _("Warning"),
                            'message': _("Discount Unit Price should be less than Unit price !!")}}
                if rec.discount_method == 'fix':
                    rec.discount_amount = rec.price_unit - rec.discount_unit_price
                elif rec.discount_method == 'per':
                    rec.discount_amount = ((rec.price_unit - rec.discount_unit_price)*100)/rec.price_unit



    def _prepare_invoice_line(self):
        res = super(sale_order_line,self)._prepare_invoice_line()
        res.update({'discount': self.discount,
                    'discount_method':self.discount_method,
                    'discount_amount':self.discount_amount,
                    'discount_amt' : self.discount_amt,
                    'discount_unit_price':self.discount_unit_price})
        return res

class ResCompany(models.Model):
    _inherit='res.company'

    
    tax_discount_policy = fields.Boolean(default=True)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    tax_discount_policy = fields.Boolean(string='Discount Applies On',default=True,related="company_id.tax_discount_policy" ,readonly=False)

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('bi_sale_discount_with_tax.tax_discount_policy', self.tax_discount_policy)
    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update({
            'tax_discount_policy':bool(self.env['ir.config_parameter'].sudo().get_param('bi_sale_discount_with_tax.tax_discount_policy')),
            })
        return res

