# -*- coding: utf-8 -*-
from odoo import http

from datetime import datetime, timedelta
from itertools import groupby

from pytz import timezone, utc

from odoo import http
from odoo.fields import Datetime
from odoo.http import request

#from Obeesdoo.beesdoo_shift.models.planning import float_to_time
from Obeesdoo.beesdoo_website_shift.controllers.main import WebsiteShiftController

class WebsiteShiftSwapController(WebsiteShiftController):

    def shift_to_timeslot(self,my_shift):
        list_shift = []
        list_shift.append(my_shift)
        my_timeslot = request.env["beesdoo.shift.template.dated"].sudo().swap_shift_to_timeslot(list_shift)
        return my_timeslot

    def new_timeslot(self,template_id,date):
        timeslot = request.env["beesdoo.shift.template.dated"].new()
        timeslot.template_id = template_id
        timeslot.date = date
        return timeslot

    @http.route("/my/shift/swaping/<int:template_id>/<string:date>", website=True)
    def swaping_shift(self,template_id,date):
        user = request.env["res.users"].browse(request.uid)
        # Get the shift
        now = datetime.now()
        shift_date = datetime.strptime(date,'%Y-%m-%d %H:%M:%S')
        request.session['template_id'] = template_id
        request.session['date'] = date
        delta = shift_date - now
        if delta.days <= 28 :
            return request.redirect("/my/shift/underpopulated/swap")
        else :
            return request.redirect('/my/shift/possible/match')




    @http.route("/my/shift/underpopulated/swap" )
    def get_underpopulated_shift(self):
        """
        Personal page for swaping your shifts
        :return:
        """
        template_id = request.session['template_id']
        date = request.session['date']
        my_timeslot = self.new_timeslot(template_id,date)
        my_available_shift = (
            request.env["beesdoo.shift.subscribed_underpopulated_shift"]
            .sudo()
            .get_underpopulated_shift(my_timeslot)
        )
        return request.render("beesdoo_website_shift_swap.website_shift_swap_swap_underpopulated",
            {
                "underpopulated_shift" : my_available_shift
            }
        )

    @http.route("/my/shift/underpopulated/swap/subscribe/<int:template_wanted>/<string:date_wanted>", website=True)
    def subscribe_to_underpopulated_swap(self,template_wanted,date_wanted):
        user = request.env["res.users"].browse(request.uid)
        template_id = request.session['template_id']
        date = request.session['date']
        my_timeslot = request.env["beesdoo.shift.template.dated"].sudo().create({
            "template_id":template_id,
            "date":date,
            "store": True,
        })

        timeslot_wanted = request.env["beesdoo.shift.template.dated"].sudo().create({
            "template_id":template_wanted,
            "date":date_wanted,
            "store":True,
        })
        data = {
            "date": datetime.date(datetime.now()),
            "worker_id": user.id,
            "exchanged_timeslot_id": my_timeslot.id,
            "confirmed_timeslot_id": timeslot_wanted.id,
        }
        record = request.env["beesdoo.shift.subscribed_underpopulated_shift"].sudo().create(data)
        if record._compute_exchanged_already_generated() :
            record.unsubscribe_shift()
        if record._conpute_comfirmed_already_generated() :
            record.subscribe_shift()
        return request.render(
            "beesdoo_website_shift.my_shift_regular_worker",
            self.my_shift_regular_worker(),
        )

    '''@http.route("/my/shift/subscribe/shift/request/<int:template_id>/<string:date>")
    def validate_exchange_request(self,template_id,date):
        user = request.env["res.users"].browse(request.uid)
        template_id = request.session['template_id']
        date = request.session['date']
        my_timeslot = request.env["beesdoo.shift.template.dated"].sudo().create({
            "template_id": template_id,
            "date": date,
            "store": True,
        })'''

    @http.route("/my/shift/possible/shift")
    def get_possible_shift(self):
        template_id = request.session['template_id']
        date = request.session['date']
        my_timeslot = self.new_timeslot(template_id, date)
        possible_timeslot = request.env["beesdoo.shift.template.dated"].sudo().display_timeslot(my_timeslot)

        return request.render ("beesdoo_website_shift_swap.website_shift_swap_possible_timeslot",
                {
                    "possible_timeslot": possible_timeslot
               })

    @http.route("/my/shift/subscribe/request/", website=True)
    def subscribe_request(self):
        user = request.env["res.users"].browse(request.uid)
        template_id = request.session['template_id']
        date = request.session['date']
        my_timeslot = request.env["beesdoo.shift.template.dated"].sudo().create({
            "template_id": template_id,
            "date": date,
            "store": True,
        })
        selected_list = request.httprequest.form.getlist('timeslot')
        asked_timeslots = request.env["beesdoo.shift.template.dated"]
        for rec in selected_list :
            data = {
                "date":rec.date,
                "template_id":rec.template_id,
                "store":True,
            }
            asked_timeslots |= rec.create(data)
            self.env["beesdoo.shift.template.dated"].check_possibility_to_exchange(rec,
                                                                                   user)
        data = {
            "request_date": datetime.date(datetime.now()),
            "worker_id": user.id,
            "exchanged_timeslot_id": my_timeslot.id,
            "asked_timeslot_ids": [(6, False, asked_timeslots.ids)],
            "status": 'no_match',
        }
        request.env["beesdoo.shift.exchange_request"].sudo().create(data)
        return request.render(
            "beesdoo_website_shift.my_shift_regular_worker",
            self.my_shift_regular_worker(),
        )

    @http.route("/my/shift/matching/request")
    def my_match(self):
        # Get current user
        cur_user = request.env["res.users"].browse(request.uid)
        my_exchanges = request.env["beesdoo.shift.exchange_request"].sudo().search([
            ('worker_id','=',cur_user.id)
        ])
        matchs = request.env["beesdoo.shift.exchange_request"]
        for exchange in my_exchanges :
            matchs |= request.env["beesdoo.shift.exchange_request"].matching_request(exchange.asked_timeslot_ids,exchange.exchanged_timeslot_id)

        return request.render("beesdoo_website_shift_swap.website_shift_swap_matching_request",
                              {
                                  "matching_request":matchs
                              })

    @http.route("/my/shift/possible/match")
    def get_possible_match(self):
        template_id = request.session['template_id']
        date = request.session['date']
        my_timeslot = self.new_timeslot(template_id, date)
        possible_match = (
            request.env["beesdoo.shift.exchange_request"]
                .sudo()
                .get_possible_match(my_timeslot)
        )
        return request.render("beesdoo_website_shift_swap.website_shift_swap_possible_match",
                              {
                                  "possible_matches":possible_match,
                              })



    '''def my_shift_next_shifts(self):
        data = super(WebsiteShiftController,self).my_shift_next_shifts()
        my_shifts = data["subscribed_shifts"]
        request.session['my_shifts'] = []
        for rec in my_shifts:
            request.session['my_shifts'].append(rec)
        return data'''
