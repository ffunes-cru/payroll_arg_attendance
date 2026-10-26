from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAttendanceInputs(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ref = cls.env.ref
        cls.employee = cls.env["hr.employee"].create({
            "name": "Operario Fichadas",
            "cct_id": ref("payroll_arg.afip_cct_uom").id,
            "contract_date_start": "2024-01-01",
            "date_version": "2024-01-01",
            "resource_calendar_id": ref("payroll_arg.resource_calendar_jornal_44h").id,
            "tz": "America/Argentina/Cordoba",
            "wage": 4500.0,
            "wage_type": "hourly",
            "schedule_pay": "bi-weekly",
            "struct_id": ref("payroll_arg.structure_jornal_quincenal_arg").id,
        })
        cls.contract = cls.employee.version_id

    def _amounts(self):
        run = self.env["hr.payslip.run"].create({
            "name": "Q1", "tipo_liquidacion": "1° Quincena", "date_start": "2026-09-01", "date_end": "2026-09-15",
        })
        return self.env["hr.payslip"]._get_period_input_amounts(
            self.contract, run.date_start, run.date_end, run
        )

    def test_without_attendances_uses_calendar(self):
        self.assertEqual(self._amounts()["HS_NORM"], 88.0)

    def test_attendances_replace_calendar_hours(self):
        # Lunes 7 y martes 8 de septiembre, 08:00-12:00 hora local (UTC-3)
        self.env["hr.attendance"].create([
            {"employee_id": self.employee.id, "check_in": "2026-09-07 11:00:00", "check_out": "2026-09-07 15:00:00"},
            {"employee_id": self.employee.id, "check_in": "2026-09-08 11:00:00", "check_out": "2026-09-08 15:00:00"},
        ])
        amounts = self._amounts()
        self.assertAlmostEqual(amounts["HS_NORM"] + amounts["HS_EXT50"] + amounts["HS_EXT100"], 8.0, places=2)
        self.assertEqual(amounts["HS_EXT100"], 0.0)
