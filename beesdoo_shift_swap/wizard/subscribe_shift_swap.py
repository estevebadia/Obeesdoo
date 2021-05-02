from odoo import api, _, fields, models
from datetime import datetime, timedelta
from odoo.exceptions import UserError


class SubscribeShiftSwap(models.TransientModel) :
    _name = 'beesdoo.shift.subscribe.shift.swap'
    _description = 'Subscribe swap shift'

    worker_id = fields.Many2one(
        "res.partner",
        default=lambda self: self.env["res.partner"].browse(
            self._context.get("active_id")
        ),
        required=True,
        string="Cooperator",
    )


    @api.depends('exchanged_timeslot_id')
    def _get_available_timeslot(self):
        for record in self:
            if not record.exchanged_timeslot_id :
                record.available_timeslots = False
            else :
                timeslots = self.env["beesdoo.shift.subscribed_underpopulated_shift"].display_underpopulated_shift(record.exchanged_timeslot_id)
                #record.available_timeslots = timeslots
                temp = self.env["beesdoo.shift.timeslots_date"]
                for rec in timeslots :
                    template=rec.template_id
                    date = rec.date
                    temp |= record.available_timeslots.create({
                        'template_id' : template.id,
                        'date' : date
                    })
                record.available_timeslots = temp


    exchanged_timeslot_id = fields.Many2one(
        'beesdoo.shift.timeslots_date',
        string='Unwanted Shift',
        #domain="[('template_id.worker_id.ids','=',worker_id.id)]"
    )

    available_timeslots = fields.Many2many(
        comodel_name='beesdoo.shift.timeslots_date',
        relation='available_timeslot',
        compute='_get_available_timeslot',
    )

    comfirmed_timeslot_id = fields.Many2one(
        'beesdoo.shift.timeslots_date',
        string='Underpopulated Shift',
        domain="[('id','in',available_timeslots.ids)]"
    )

    def _check(self, group="beesdoo_shift.group_shift_management"):
        self.ensure_one()
        if not self.env.user.has_group(group):
            raise UserError(
                _("You don't have the required access for this operation.")
            )
        if (
            self.worker_id == self.env.user.partner_id
            and not self.env.user.has_group(
                "beesdoo_shift.group_cooperative_admin"
            )
        ):
            raise UserError(_("You cannot perform this operation on yourself"))
        return self.with_context(real_uid=self._uid)

    #TODO : check si il a pas fais un échange 2mois avant
    def has_already_done_exchange(self):
        worker_id = self.worker_id
        cur_date = datetime.now()
        limit_date = cur_date - timedelta(2*28)
        swaps = self.env["beesdoo.shift.subscribed_underpopulated_shift"].search([
            ("date","<=",cur_date),
            ("date", ">=",limit_date ),
        ])
        for swap in swaps :
            if swap.worker_id == worker_id :
                return True
            return False


    def make_change(self):
        self = self._check()
        if self.has_already_done_exchange() :
            raise UserError (_("You already swap your shift in the last 2months"))
        data = {
            "date" : datetime.now(),
            "worker_id" : self.worker_id,
            "exchanged_timeslot_id" : self.exchanged_timeslot_id,
            "comfirmed_timeslot_id" : self.comfirmed_timeslot_id,
        }
        record = self.env["beesdoo.shift.subscribed_underpopulated_shift"].sudo().create(data)
        if record.is_shift_exchanged_already_generated() :
            record.unsubscribe_shift()
        if record.is_shift_comfirmed_already_generated() :
            record.subscribe_shift()





'''
    @api.onchange('comfirmed_timeslot_id')
    def onchange_get_available_timeslot(self):
        available_timeslot = []
        my_shift = self.exchanged_timeslot_id
        my_possibility = self.env["beesdoo.shift.subscribed_underpopulated_shift"].display_underpopulated_shift(my_shift)
        for timeslot in my_possibility :
            #TODO : mettre 50 (pourcentage que l'on ne veut pas dépasser) en paramètre systeme
            if timeslot[1] <= 50 :
                available_timeslot.append(timeslot[0])

        return {
            'value' : {
                'available_timeslots' : available_timeslot,
            }
        }

'''




