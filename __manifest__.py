{
    "name": "Nómina Argentina: Sincronización de Asistencias y Horas Extras",
    "version": "19.0.1.0.0",
    "category": "Payroll",
    "summary": "Sincronización de fichadas reales de hr.attendance y cálculo legal de horas extras para jornales",
    "author": "Artimezoft / Antigravity",
    "license": "LGPL-3",
    "depends": [
        "payroll_arg",
        "hr_attendance",
        "hr_holidays",
        "resource",
    ],
    "data": [
        "data/overtime_ruleset_data.xml",
        "views/hr_payslip_views.xml",
        "views/hr_payslip_run_views.xml",
    ],
    "application": False,
    "installable": True,
}
