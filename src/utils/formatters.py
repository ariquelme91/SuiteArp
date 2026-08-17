"""
Funciones de formato para la aplicación.
"""


def format_peso_chileno(valor: float, decimales: int = 0) -> str:
    """
    Formatea un valor como pesos chilenos (formato: $1.234.567).

    Args:
        valor: Valor a formatear
        decimales: Número de decimales (default 0)

    Returns:
        String formateado como peso chileno
    """
    if decimales == 0:
        # Formato sin decimales: $1.234.567
        return f"${valor:,.0f}".replace(",", ".")
    else:
        # Formato con decimales: $1.234.567,89
        # Primero formatea con comas
        formateado = f"${valor:,.{decimales}f}"
        # Reemplaza comas por puntos (separador de miles) excepto el último separador decimal
        partes = formateado.rsplit(",", 1)
        if len(partes) == 2:
            return partes[0].replace(",", ".") + "," + partes[1]
        return formateado.replace(",", ".")
