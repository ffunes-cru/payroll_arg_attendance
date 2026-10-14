from datetime import datetime, time
import pytz
from odoo import api, fields, models


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    attendance_hours_count = fields.Float(
        string="Horas Reales de Asistencia",
        compute="_compute_attendance_hours",
        help="Suma total de horas registradas en el módulo de Asistencias (hr.attendance) en el período.",
    )

    def _compute_attendance_hours(self):
        attendance_obj = self.env["hr.attendance"]
        for slip in self:
            if not slip.date_from or not slip.date_to or not slip.employee_id:
                slip.attendance_hours_count = 0.0
                continue

            calendar = slip.contract_id.resource_calendar_id or slip.employee_id.resource_calendar_id
            tz = pytz.timezone(calendar.tz or slip.employee_id.tz or "America/Argentina/Cordoba") if calendar else pytz.utc

            tz_start = tz.localize(datetime.combine(slip.date_from, time.min)).astimezone(pytz.utc).replace(tzinfo=None)
            tz_end = tz.localize(datetime.combine(slip.date_to, time.max)).astimezone(pytz.utc).replace(tzinfo=None)

            attendances = attendance_obj.search(
                [
                    ("employee_id", "=", slip.employee_id.id),
                    ("check_in", ">=", tz_start),
                    ("check_in", "<=", tz_end),
                    ("check_out", "!=", False),
                ]
            )
            slip.attendance_hours_count = sum(attendances.mapped("worked_hours"))

    def action_sync_attendance_hours(self):
        """
        Sincroniza las horas de hr.attendance distinguiendo horas normales y extras (50% y 100%).
        """
        for slip in self:
            if not slip.date_from or not slip.date_to or not slip.employee_id:
                continue

            calendar = slip.contract_id.resource_calendar_id or slip.employee_id.resource_calendar_id
            tz = pytz.timezone(calendar.tz or slip.employee_id.tz or "America/Argentina/Cordoba") if calendar else pytz.utc

            tz_start = tz.localize(datetime.combine(slip.date_from, time.min)).astimezone(pytz.utc).replace(tzinfo=None)
            tz_end = tz.localize(datetime.combine(slip.date_to, time.max)).astimezone(pytz.utc).replace(tzinfo=None)

            attendances = self.env["hr.attendance"].search(
                [
                    ("employee_id", "=", slip.employee_id.id),
                    ("check_in", ">=", tz_start),
                    ("check_in", "<=", tz_end),
                    ("check_out", "!=", False),
                ]
            )
            slip.attendance_hours_count = sum(attendances.mapped("worked_hours"))

            if hasattr(slip, "_compute_attendance_hours_breakdown"):
                breakdown = slip._compute_attendance_hours_breakdown(attendances, calendar=calendar, employee=slip.employee_id)
            else:
                breakdown = {
                    "hours_normal": slip.attendance_hours_count,
                    "hours_ext50": 0.0,
                    "hours_ext100": 0.0,
                }

            slip.hours_normal = breakdown["hours_normal"]
            slip.hours_ext50 = breakdown["hours_ext50"]
            slip.hours_ext100 = breakdown["hours_ext100"]

            # Sincronizar input lines en nómina argentina
            if hasattr(slip, "_sync_input_line"):
                if slip.contract_id and slip.contract_id.wage_type == "hourly":
                    slip._sync_input_line("HS_NORM", "Horas Normales Trabajadas", breakdown["hours_normal"])
                if breakdown["hours_ext50"] > 0:
                    slip._sync_input_line("HS_EXT50", "Horas Extras 50%", breakdown["hours_ext50"])
                else:
                    if hasattr(slip, "_remove_input_line"):
                        slip._remove_input_line("HS_EXT50")
                    else:
                        to_del = slip.input_line_ids.filtered(lambda i: i.code == "HS_EXT50")
                        slip.input_line_ids = slip.input_line_ids - to_del
                if breakdown["hours_ext100"] > 0:
                    slip._sync_input_line("HS_EXT100", "Horas Extras 100%", breakdown["hours_ext100"])
                else:
                    if hasattr(slip, "_remove_input_line"):
                        slip._remove_input_line("HS_EXT100")
                    else:
                        to_del = slip.input_line_ids.filtered(lambda i: i.code == "HS_EXT100")
                        slip.input_line_ids = slip.input_line_ids - to_del

            work_hours = breakdown["hours_normal"] if (slip.contract_id and slip.contract_id.wage_type == "hourly") else slip.attendance_hours_count
            work_line = slip.worked_days_line_ids.filtered(lambda w: w.code == "WORK100")
            h_day = calendar.hours_per_day if calendar and calendar.hours_per_day else 8.8
            if work_line:
                work_line.write({
                    "number_of_hours": work_hours,
                    "number_of_days": round(work_hours / h_day, 2),
                })
            elif work_hours > 0:
                slip.write({
                    "worked_days_line_ids": [
                        (
                            0,
                            0,
                            {
                                "name": "Días Trabajados (desde Asistencias)",
                                "sequence": 1,
                                "code": "WORK100",
                                "number_of_days": round(work_hours / h_day, 2),
                                "number_of_hours": work_hours,
                                "contract_id": slip.contract_id.id if slip.contract_id else False,
                            },
                        )
                    ]
                })
            slip.compute_sheet()
        return True
