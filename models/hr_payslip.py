from datetime import datetime, time

import pytz

from odoo import api, fields, models

DEFAULT_TZ = "America/Argentina/Cordoba"


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    attendance_hours_count = fields.Float(
        string="Horas Reales de Asistencia",
        compute="_compute_attendance_hours",
        help="Suma total de horas registradas en Asistencias (hr.attendance) en el período.",
    )

    @api.model
    def _get_period_attendances(self, contract, date_from, date_to):
        employee = contract.employee_id
        cal = contract.resource_calendar_id or employee.resource_calendar_id
        tz = pytz.timezone(cal.tz or employee.tz or DEFAULT_TZ) if cal else pytz.utc
        tz_start = tz.localize(datetime.combine(date_from, time.min)).astimezone(pytz.utc).replace(tzinfo=None)
        tz_end = tz.localize(datetime.combine(date_to, time.max)).astimezone(pytz.utc).replace(tzinfo=None)
        return self.env["hr.attendance"].search([
            ("employee_id", "=", employee.id),
            ("check_in", ">=", tz_start),
            ("check_in", "<=", tz_end),
            ("check_out", "!=", False),
        ])

    @api.depends("contract_id", "date_from", "date_to")
    def _compute_attendance_hours(self):
        for slip in self:
            if not (slip.contract_id and slip.date_from and slip.date_to):
                slip.attendance_hours_count = 0.0
                continue
            attendances = slip._get_period_attendances(slip.contract_id, slip.date_from, slip.date_to)
            slip.attendance_hours_count = sum(attendances.mapped("worked_hours"))

    @api.model
    def _get_period_input_amounts(self, contract, date_from, date_to, run):
        """Jornalizados con fichadas en el período: horas normales y extras desde Asistencias
        en lugar del calendario."""
        vals = super()._get_period_input_amounts(contract, date_from, date_to, run)
        if contract.wage_type != "hourly" or "HS_NORM" not in vals:
            return vals
        attendances = self._get_period_attendances(contract, date_from, date_to)
        if attendances:
            breakdown = self._compute_attendance_hours_breakdown(attendances, contract)
            if sum(breakdown.values()) > 0.1:
                vals.update(breakdown)
        return vals

    @api.model
    def _compute_attendance_hours_breakdown(self, attendances, contract):
        """Desglosa las horas de asistencia en normales, extras 50% y extras 100% usando el
        motor de horas extras de Odoo (hr.attendance.overtime.line).

        - 100%: líneas con amount_rate >= 2 o reglas de días no laborables.
        - 50%: el resto de las horas extras.
        - Normales: horas trabajadas menos horas extras.

        :return: {"HS_NORM": h, "HS_EXT50": h, "HS_EXT100": h}
        """
        employee = contract.employee_id
        validation_mode = employee.company_id.attendance_overtime_validation
        tot_worked = sum(att.worked_hours for att in attendances if att.worked_hours > 0)
        tot_ext50 = 0.0
        tot_ext100 = 0.0

        ot_lines = attendances.mapped("linked_overtime_ids")
        if not ot_lines:
            dates = [d for d in attendances.mapped("date") if d]
            ot_lines = self.env["hr.attendance.overtime.line"].search([
                ("employee_id", "=", employee.id),
                ("date", ">=", min(dates)),
                ("date", "<=", max(dates)),
            ]) if dates else ot_lines
        if ot_lines:
            for line in ot_lines:
                if line.status == "refused":
                    continue
                if validation_mode == "by_manager" and line.status != "approved":
                    continue
                duration = line.duration or line.manual_duration or 0.0
                if duration <= 0:
                    continue
                is_100 = (line.amount_rate or 1.0) >= 2.0 or "non_work_days" in line.rule_ids.mapped("timing_type")
                if is_100:
                    tot_ext100 += duration
                else:
                    tot_ext50 += duration
        else:
            # Asistencias sin líneas de horas extras generadas: sábado/domingo al 100%
            cal = contract.resource_calendar_id
            tz = pytz.timezone(cal.tz or employee.tz or DEFAULT_TZ)
            for att in attendances:
                ot_h = (att.validated_overtime_hours if validation_mode == "by_manager" else att.overtime_hours) or 0.0
                if ot_h > 0:
                    local_in = pytz.utc.localize(att.check_in).astimezone(tz)
                    if local_in.weekday() in (5, 6):
                        tot_ext100 += ot_h
                    else:
                        tot_ext50 += ot_h

        return {
            "HS_NORM": round(max(0.0, tot_worked - tot_ext50 - tot_ext100), 2),
            "HS_EXT50": round(tot_ext50, 2),
            "HS_EXT100": round(tot_ext100, 2),
        }
