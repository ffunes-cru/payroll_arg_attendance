"""@file
La documentación del código está al día (mismo verificador que payroll_arg)."""
from pathlib import Path

from odoo.tests import TransactionCase, tagged

from odoo.addons.payroll_arg.tools.documentacion import faltantes

## Carpeta raíz de este módulo.
RAIZ = Path(__file__).resolve().parent.parent


@tagged("post_install", "-at_install")
class TestDocumentacion(TransactionCase):
    """Ver payroll_arg/tools/documentacion.py."""

    def test_codigo_documentado(self):
        """Todo módulo, clase, función y parámetro de Python está documentado."""
        errores = faltantes(RAIZ, ("", "models"))
        self.assertFalse(errores, "Falta documentación (formato Doxygen, ver payroll_arg/docs/recetas.md):\n"
                         + "\n".join(errores))
