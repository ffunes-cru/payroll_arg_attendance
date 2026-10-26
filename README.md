# Nómina Argentina: Asistencias (Odoo 19)

Complemento de `payroll_arg`: los jornalizados con fichadas (`hr.attendance`) en el período cobran las
**horas fichadas** en lugar de las del calendario.

- `HS_NORM` = horas fichadas − horas extras.
- `HS_EXT50` / `HS_EXT100` = horas extras del motor de Odoo (`hr.attendance.overtime.line`): al 100% las
  de reglas con recargo ≥ 2 o de días no laborables; el resto al 50%. Con validación por responsable,
  sólo las aprobadas (`manual_duration`).
- Sin líneas de horas extras: las horas extra de cada fichada van al 100% en sábado o domingo y al 50%
  el resto de los días.
- Sin fichadas en el período quedan las horas del calendario (88 por quincena).
- Trae el conjunto de reglas *Convenio Argentina (Jornales LCT)*: exceso de jornada al 50%, días no
  laborables al 100%. Al pasar un contrato a jornalizado se le asigna.

**Autor:** Franco Funes · **Licencia:** [AGPL-3](LICENSE) · **Depende de:** `payroll_arg`,
`hr_attendance`, `hr_holidays`, `resource`.

Problemas conocidos (A1 a A3: extras pendientes pagadas como normales, sábado y feriado trabajado,
topes): ver `payroll_arg/docs/revision.md`. Documentación general: `payroll_arg/README.md`.

```bash
.venv/bin/python odoo-bin -d <base_de_prueba> -u payroll_arg_attendance \
    --test-tags /payroll_arg_attendance --stop-after-init --http-port=8092
```
