import logging
import math
from datetime import datetime, time, timedelta

from pytz import UTC, timezone

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


def float_to_time(f):
    decimal, integer = math.modf(f)
    return "{}:{}".format(
        str(int(integer)).zfill(2), str(int(round(decimal * 60))).zfill(2)
    )


def floatime_to_hour_minute(f):
    decimal, integer = math.modf(f)
    return int(integer), int(round(decimal * 60))


def get_first_day_of_week():
    today = datetime.now()
    return (datetime.now() - timedelta(days=today.weekday())).date()


class ShiftType(models.Model):
    _name = "shift.type"
    _description = "shift.type"

    name = fields.Char()
    description = fields.Text()
    active = fields.Boolean(default=True)


class ShiftDayNumber(models.Model):
    _name = "shift.daynumber"
    _description = "shift.daynumber"

    _order = "number asc"

    name = fields.Char()
    number = fields.Integer(
        "Day Number",
        help="From 1 to N, When you will instanciate your planning, Day 1 "
        "will be the start date of the instance, Day 2 the second, "
        "etc...",
    )
    active = fields.Boolean(default=True)


class ShiftPlanning(models.Model):
    _name = "shift.planning"
    _description = "shift.planning"
    _order = "sequence asc"

    sequence = fields.Integer()
    name = fields.Char()
    periodicity = fields.Integer(
        "Periodicity",
        help="""From 1 to N. This number specifies the periodicity for the
        automated generation of a planning. For a weekly planning, the
        periodicity would be 7, because the planning has to be generated
        every seven days.""",
        default=7,
    )
    task_template_ids = fields.One2many("shift.template", "planning_id")

    @api.model
    def _get_next_planning(self, sequence):
        """There can be multiple planning templates defined. When
        generating shifts automatically, one template has to be
        selected. The sequence number of the previously used
        template is stored, so that it can be bumped up in a
        cyclic fashion."""
        next_planning = self.search([("sequence", ">", sequence)])
        if not next_planning:
            return self.search([])[0]
        return next_planning[0]

     
    def _get_next_planning_date(self, date):
        self.ensure_one()
        periodicity = self.periodicity
        if not periodicity:
            raise ValueError(
                """Template periodicity is undefined although it
                should have the default value or a value given by
                the user."""
            )
        return date + timedelta(days=periodicity)

    @api.model
    def _generate_next_planning(self):
        config = self.env["ir.config_parameter"].sudo()
        last_seq = int(config.get_param("shift.last_planning_seq", 0))
        date = fields.Date.from_string(config.get_param("shift.next_planning_date", 0))

        planning = self._get_next_planning(last_seq)
        planning = planning.with_context(visualize_date=date)

        if not planning.task_template_ids:
            _logger.error("Could not generate next planning: no task template defined.")
            return

        planning.task_template_ids.generate_task_day()

        next_date = planning._get_next_planning_date(date)
        config.set_param("shift.last_planning_seq", planning.sequence)
        config.set_param("shift.next_planning_date", next_date)

    @api.model
    def get_future_shifts(
        self,
        end_date,
        start_date=datetime.now(),
        worker_id=None,
        include_cancelled=True,
    ):
        """
        Calculates shifts between start_date and end_date without
        storing them in the database.
        Uses a list of shifts instead of a recordset because
        of issues occuring when copying records.
        :param end_date: Datetime
        :return: shift.shift list
        """
        # Getting existing shifts
        shift_domain = [("start_time", ">", start_date.strftime("%Y-%m-%d %H:%M:%S"))]
        if worker_id:
            shift_domain.append(("worker_id", "=", worker_id.id))
        if not include_cancelled:
            shift_domain.append(("state", "!=", "cancel"))

        existing_shift_list = list(
            self.env["shift.shift"]
            .sudo()
            .search(
                shift_domain,
                order="start_time, task_template_id, task_type_id",
            )
        )

        # Getting parameters
        last_sequence = int(
            self.env["ir.config_parameter"].sudo().get_param("shift.last_planning_seq")
        )

        next_planning = self._get_next_planning(last_sequence)

        next_planning_date = fields.Datetime.from_string(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("shift.next_planning_date", 0)
        )

        next_planning = next_planning.with_context(visualize_date=next_planning_date)

        # The following loop will generate a list of shifts. Each shift
        # is a dictionary. The conversion to a recordset is performed
        # after filtering the new shift to avoid unnecessary
        # computations.
        future_shift_list = []
        while next_planning_date < end_date:
            for shift in next_planning.task_template_ids._prepare_task_day():
                if shift["start_time"] > start_date:
                    future_shift_list.append(shift)
            next_planning_date = next_planning._get_next_planning_date(
                next_planning_date
            )
            last_sequence = next_planning.sequence
            next_planning = self._get_next_planning(last_sequence)
            next_planning = next_planning.with_context(
                visualize_date=next_planning_date
            )

        # Filtering future shifts
        if worker_id:
            filtered_future_shift_list = [
                shift
                for shift in future_shift_list
                if shift["worker_id"] == worker_id.id
            ]
        else:
            filtered_future_shift_list = future_shift_list

        # Converting dictionary to recordset
        shift_list = existing_shift_list + [
            self.env["shift.shift"].new(shift) for shift in filtered_future_shift_list
        ]

        return shift_list


class ShiftTemplate(models.Model):
    _name = "shift.template"
    _description = "shift.template"
    _order = "start_time"

    name = fields.Char(required=True)
    planning_id = fields.Many2one("shift.planning", required=True)
    day_nb_id = fields.Many2one("shift.daynumber", string="Day", required=True)
    task_type_id = fields.Many2one("shift.type", string="Type")
    start_time = fields.Float(required=True)
    end_time = fields.Float(required=True)
    super_coop_id = fields.Many2one(
        "res.users",
        string="Super Cooperative",
        domain=[("partner_id.super", "=", True)],
    )

    duration = fields.Float(help="Duration in Hour")
    worker_nb = fields.Integer(
        string="Number of worker",
        help="Max number of worker for this task",
        default=1,
    )
    worker_ids = fields.Many2many(
        "res.partner",
        string="Recurrent worker assigned",
        domain=[("is_worker", "=", True)],
    )
    remaining_worker = fields.Integer(
        compute="_compute_remaining", store=True, string="Remaining Place"
    )
    active = fields.Boolean(default=True)
    # For Kanban View Only
    color = fields.Integer("Color Index")
    worker_name = fields.Char(compute="_compute_worker_name")
    # For calendar View
    start_date = fields.Datetime(compute="_compute_fake_date", search="_search_dummy")
    end_date = fields.Datetime(compute="_compute_fake_date", search="_search_dummy")

    def _get_utc_date(self, day, hour, minute):
        """Combine day number, hours and minutes to save
        corresponding UTC datetime in database.
        """
        context_tz = timezone(self._context.get("tz") or self.env.user.tz)
        day_local_time = datetime.combine(day, time(hour=hour, minute=minute))
        day_local_time = context_tz.localize(day_local_time)
        day_utc_time = day_local_time.astimezone(UTC)
        # Return naïve datetime so as to be saved in database
        return day_utc_time.replace(tzinfo=None)

    @api.depends("start_time", "end_time")
    def _compute_fake_date(self):
        today = self._context.get("visualize_date", get_first_day_of_week())
        for rec in self:
            # Find the day of this task template 'rec'.
            day = today + timedelta(days=rec.day_nb_id.number - 1)
            # Compute the beginning and ending time according to the
            # context timezone.
            h_begin, m_begin = floatime_to_hour_minute(rec.start_time)
            h_end, m_end = floatime_to_hour_minute(rec.end_time)
            rec.start_date = self._get_utc_date(day, h_begin, m_begin)
            rec.end_date = self._get_utc_date(day, h_end, m_end)

    def _search_dummy(self, operator, value):
        return []

    @api.depends("worker_ids", "worker_nb")
    def _compute_remaining(self):
        for rec in self:
            rec.remaining_worker = rec.worker_nb - len(rec.worker_ids)

    @api.depends("worker_ids")
    def _compute_worker_name(self):
        for rec in self:
            rec.worker_name = ",".join(rec.worker_ids.mapped("display_name"))

    @api.constrains("worker_nb", "worker_ids")
    def _nb_worker_max(self):
        for rec in self:
            if len(rec.worker_ids) > rec.worker_nb:
                raise UserError(
                    _(
                        "You cannot assign more workers than the maximal "
                        "number defined on template. "
                    )
                )

    @api.onchange("start_time", "end_time")
    def _get_duration(self):
        if self.start_time and self.end_time:
            self.duration = self.end_time - self.start_time

    @api.onchange("duration")
    def _set_duration(self):
        if self.start_time:
            self.end_time = self.start_time + self.duration

    def _prepare_task_day(self):
        """
        Generates a list of dict objects containing the informations
        for the shifts to generate based on the template data
        """
        tasks = []
        for rec in self:
            for i in range(0, rec.worker_nb):
                worker_id = rec.worker_ids[i] if len(rec.worker_ids) > i else False
                # remove worker in holiday and temporary exempted
                if worker_id and worker_id.cooperative_status_ids:
                    status = worker_id.cooperative_status_ids[0]
                    if (
                        status.holiday_start_time
                        and status.holiday_end_time
                        and status.holiday_start_time <= rec.start_date.date()
                        and status.holiday_end_time >= rec.end_date.date()
                    ):
                        worker_id = False
                    if (
                        status.temporary_exempt_start_date
                        and status.temporary_exempt_end_date
                        and status.temporary_exempt_start_date <= rec.start_date.date()
                        and status.temporary_exempt_end_date >= rec.end_date.date()
                    ):
                        worker_id = False
                tasks.append(
                    {
                        "name": "[%s] %s %s (%s - %s) [%s]"
                        % (
                            rec.start_date.date(),
                            rec.planning_id.name,
                            rec.day_nb_id.name,
                            float_to_time(rec.start_time),
                            float_to_time(rec.end_time),
                            i,
                        ),
                        "task_template_id": rec.id,
                        "task_type_id": rec.task_type_id.id,
                        "super_coop_id": rec.super_coop_id.id,
                        "worker_id": worker_id and worker_id.id or False,
                        "is_regular": True if worker_id else False,
                        "start_time": rec.start_date,
                        "end_time": rec.end_date,
                        "state": "open",
                    }
                )

        return tasks

     
    def get_task_day(self):
        """
        Creates the shifts according to the template without saving
        them into the database.
        To adapt the behaviour, function _prepare_task_day()
        should be overwritten.
        """
        tasks = self.env["shift.shift"]
        task_list = self._prepare_task_day()
        for task in task_list:
            tasks |= tasks.new(task)
        return tasks

     
    def generate_task_day(self):
        """
        Creates the shifts according to the template and saves
        them into the database.
        To adapt the behaviour, function _prepare_task_day()
        should be overwritten.
        """
        tasks = self.env["shift.shift"]
        task_list = self._prepare_task_day()
        for task in task_list:
            tasks |= tasks.create(task)
        return tasks

    @api.onchange("worker_ids")
    def check_for_multiple_shifts(self):
        original_ids = {worker.id for worker in self._origin.worker_ids}

        warnings = []
        for worker in self.worker_ids:
            if worker.id not in original_ids:
                shifts = [
                    shift.name
                    for shift in worker.subscribed_shift_ids
                    if shift.id != self.id
                ]
                if shifts:
                    warnings.append(
                        worker.name + _(" is already assigned to ") + ", ".join(shifts)
                    )

        if warnings:
            return {
                "warning": {
                    "title": _("Warning"),
                    "message": "\n".join(warnings),
                }
            }

    def write(self, vals):
        """
        Overwrite write() function to apply changes to already created shift.
        """
        saved_vals = {}
        for rec in self:
            saved_vals[rec] = rec.worker_ids
        result = super().write(vals)
        for rec in self:
            rec._update_shifts_on_worker_change(
                prev_worker_ids=saved_vals[rec],
                cur_worker_ids=rec.worker_ids,
            )
        return result

    def _update_shifts_on_worker_change(self, prev_worker_ids, cur_worker_ids):
        """
        Subscribe or Unsubscribe worker to already generated shifts
        """
        self.ensure_one()
        shift_cls = self.env["shift.shift"]
        removed_workers = prev_worker_ids - cur_worker_ids
        added_workers = cur_worker_ids - prev_worker_ids
        if removed_workers:
            shift_cls.unsubscribe_from_today(
                worker_ids=removed_workers,
                task_tmpl_ids=self,
                now=datetime.now(),
            )
        if added_workers:
            shift_cls.subscribe_from_today(
                worker_ids=added_workers,
                task_tmpl_ids=self,
                now=datetime.now(),
            )
