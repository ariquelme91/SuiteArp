#!/usr/bin/env python3
"""Genera un PDF único a partir de la documentación en Markdown.

Convierte DOCUMENTACION.md y MIGRACION.md en un solo documento con portada,
índice y numeración de páginas, pensado para imprimir o entregar a quien
tome el proyecto.

Uso:
    python generar_pdf_docs.py [-o salida.pdf]

Sobre las fuentes: se usan Calibri y Consolas de Windows porque las fuentes
base de reportlab no traen los caracteres de dibujo de cajas (U+2500…) que
forman los diagramas de la documentación, y saldrían como recuadros negros.
"""

import argparse
import io
import re
import sys
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, CondPageBreak, Frame, HRFlowable, KeepTogether,
    NextPageTemplate, PageBreak, PageTemplate, Paragraph, Preformatted,
    Spacer, Table, TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

RAIZ = Path(__file__).resolve().parent

DOCUMENTOS = [
    ("DOCUMENTACION.md", "Documentación técnica"),
    ("MIGRACION.md", "Guía de migración y respaldo"),
]

# Paleta: tinta azulada, acento marino y un rojo contenido para avisos.
TINTA = colors.HexColor("#16202E")
TINTA_SUAVE = colors.HexColor("#3D4C5F")
GRIS = colors.HexColor("#61728A")
ACENTO = colors.HexColor("#1F4E78")
AVISO = colors.HexColor("#B23A36")
LINEA = colors.HexColor("#D6DFEA")
FONDO_COD = colors.HexColor("#F2F5F9")
FONDO_CAB = colors.HexColor("#E9EEF5")

ANCHO_UTIL = A4[0] - 42 * mm

# Emoji y símbolos que las fuentes disponibles no dibujan.
REEMPLAZOS = {
    "\u2705": "Sí",       # marca de verificación
    "\u274c": "No",       # cruz
    "\u26a0\ufe0f": "",   # aviso (el bloque ya se destaca solo)
    "\u26a0": "",
    "\U0001f9ee": "", "\U0001f4ca": "", "\U0001f4dd": "",
    "\U0001f4b0": "", "\u2699\ufe0f": "", "\u2699": "",
    "\U0001f465": "", "\ufe0f": "",
}


def registrar_fuentes():
    """Registra Calibri y Consolas; avisa y aborta si faltan."""
    fuentes = [
        ("Cuerpo", "calibri.ttf"), ("Cuerpo-Bold", "calibrib.ttf"),
        ("Cuerpo-Italic", "calibrii.ttf"), ("Cuerpo-BoldItalic", "calibriz.ttf"),
        ("Mono", "consola.ttf"), ("Mono-Bold", "consolab.ttf"),
    ]
    for nombre, archivo in fuentes:
        ruta = Path("C:/Windows/Fonts") / archivo
        if not ruta.exists():
            sys.exit(f"Falta la fuente {ruta}. Este script requiere Windows.")
        pdfmetrics.registerFont(TTFont(nombre, str(ruta)))

    pdfmetrics.registerFontFamily(
        "Cuerpo", normal="Cuerpo", bold="Cuerpo-Bold",
        italic="Cuerpo-Italic", boldItalic="Cuerpo-BoldItalic",
    )


def limpiar(texto: str) -> str:
    """Sustituye los caracteres que las fuentes no pueden dibujar."""
    for viejo, nuevo in REEMPLAZOS.items():
        texto = texto.replace(viejo, nuevo)
    return texto


def escapar(texto: str) -> str:
    """Escapa lo que reportlab interpretaría como marcado."""
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(texto: str) -> str:
    """Traduce el Markdown de línea al marcado de reportlab.

    El escapado va primero para que un `<` del texto no se confunda con
    las etiquetas que insertamos después.
    """
    t = escapar(limpiar(texto))
    # Código antes que el resto: su contenido no debe recibir más formato.
    t = re.sub(
        r"`([^`]+)`",
        r'<font name="Mono" size="9" backColor="#EDF1F6">\1</font>',
        t,
    )
    t = re.sub(r"\*\*\*(.+?)\*\*\*", r"<b><i>\1</i></b>", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\w*])\*([^*\n]+?)\*(?![\w*])", r"<i>\1</i>", t)
    t = re.sub(r"~~(.+?)~~", r"<strike>\1</strike>", t)
    t = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<link href="\2" color="#1F4E78">\1</link>',
        t,
    )
    return t


def crear_estilos():
    """Estilos derivados de la paleta, con jerarquía por tamaño y peso."""
    hoja = getSampleStyleSheet()
    e = {}

    e["titulo_portada"] = ParagraphStyle(
        "titulo_portada", parent=hoja["Title"], fontName="Cuerpo-Bold",
        fontSize=32, leading=36, textColor=TINTA, alignment=TA_LEFT, spaceAfter=6,
    )
    e["sub_portada"] = ParagraphStyle(
        "sub_portada", fontName="Cuerpo", fontSize=13, leading=19,
        textColor=TINTA_SUAVE, alignment=TA_LEFT,
    )
    e["meta_portada"] = ParagraphStyle(
        "meta_portada", fontName="Mono", fontSize=9, leading=15, textColor=GRIS,
    )
    e["h1"] = ParagraphStyle(
        "h1", fontName="Cuerpo-Bold", fontSize=21, leading=26,
        textColor=TINTA, spaceBefore=0, spaceAfter=12,
    )
    e["h2"] = ParagraphStyle(
        "h2", fontName="Cuerpo-Bold", fontSize=15, leading=20,
        textColor=ACENTO, spaceBefore=18, spaceAfter=7,
    )
    e["h3"] = ParagraphStyle(
        "h3", fontName="Cuerpo-Bold", fontSize=11.5, leading=16,
        textColor=TINTA, spaceBefore=13, spaceAfter=5,
    )
    e["cuerpo"] = ParagraphStyle(
        "cuerpo", fontName="Cuerpo", fontSize=10, leading=15,
        textColor=TINTA, spaceAfter=8,
    )
    e["lista"] = ParagraphStyle(
        "lista", parent=e["cuerpo"], leftIndent=13, spaceAfter=3.5,
        bulletIndent=3,
        # Sin esto la viñeta se dibuja con Helvetica, que no trae el cuadrado
        # de las casillas y lo pinta como un recuadro negro.
        bulletFontName="Cuerpo", bulletFontSize=9.5,
    )
    e["cita"] = ParagraphStyle(
        "cita", parent=e["cuerpo"], leftIndent=10, textColor=TINTA_SUAVE,
        borderPadding=(0, 0, 0, 8),
    )
    e["codigo"] = ParagraphStyle(
        "codigo", fontName="Mono", fontSize=8.2, leading=11.4, textColor=TINTA,
    )
    e["celda"] = ParagraphStyle(
        "celda", fontName="Cuerpo", fontSize=9, leading=12.5, textColor=TINTA,
    )
    e["celda_cab"] = ParagraphStyle(
        "celda_cab", fontName="Cuerpo-Bold", fontSize=8.4, leading=11.5,
        textColor=GRIS,
    )
    e["toc1"] = ParagraphStyle(
        "toc1", fontName="Cuerpo-Bold", fontSize=11, leading=19, textColor=TINTA,
        spaceBefore=8,
    )
    e["toc2"] = ParagraphStyle(
        "toc2", fontName="Cuerpo", fontSize=10, leading=16, leftIndent=14,
        textColor=TINTA_SUAVE,
    )
    e["toc3"] = ParagraphStyle(
        "toc3", fontName="Cuerpo", fontSize=9, leading=14, leftIndent=30,
        textColor=GRIS,
    )
    e["titulo_toc"] = ParagraphStyle(
        "titulo_toc", fontName="Cuerpo-Bold", fontSize=17, leading=22,
        textColor=TINTA, spaceAfter=14,
    )
    return e


# ----------------------------------------------------------------------
# Conversión de Markdown a flowables
# ----------------------------------------------------------------------

class Conversor:
    def __init__(self, estilos):
        self.e = estilos
        self.contador = 0   # ids únicos para los marcadores del índice

    def convertir(self, lineas):
        salida = []
        i = 0
        while i < len(lineas):
            linea = lineas[i]
            desnuda = linea.strip()

            # Bloque de código
            if desnuda.startswith("```"):
                bloque, i = self._leer_codigo(lineas, i)
                salida.append(self._codigo(bloque))
                continue

            # Tabla
            if desnuda.startswith("|"):
                filas, i = self._leer_tabla(lineas, i)
                if filas:
                    salida.append(self._tabla(filas))
                continue

            # Cita / aviso
            if desnuda.startswith(">"):
                bloque, i = self._leer_cita(lineas, i)
                salida.append(self._cita(bloque))
                continue

            # Regla horizontal
            if desnuda in ("---", "***", "___"):
                salida.append(Spacer(1, 5))
                salida.append(HRFlowable(width="100%", thickness=0.6, color=LINEA))
                salida.append(Spacer(1, 9))
                i += 1
                continue

            # Encabezados
            m = re.match(r"^(#{1,3})\s+(.*)$", desnuda)
            if m:
                salida.append(self._encabezado(len(m.group(1)), m.group(2)))
                i += 1
                continue

            # Listas
            if re.match(r"^[-*]\s+", desnuda) or re.match(r"^\d+\.\s+", desnuda):
                items, i = self._leer_lista(lineas, i)
                salida.extend(items)
                continue

            # Párrafo
            if desnuda:
                bloque, i = self._leer_parrafo(lineas, i)
                salida.append(Paragraph(inline(bloque), self.e["cuerpo"]))
                continue

            i += 1
        return salida

    # --- lectores -----------------------------------------------------

    def _leer_codigo(self, lineas, i):
        i += 1
        bloque = []
        while i < len(lineas) and not lineas[i].strip().startswith("```"):
            bloque.append(lineas[i])
            i += 1
        return bloque, i + 1

    def _leer_tabla(self, lineas, i):
        crudas = []
        while i < len(lineas) and lineas[i].strip().startswith("|"):
            crudas.append(lineas[i].strip())
            i += 1
        filas = []
        for cruda in crudas:
            celdas = [c.strip() for c in cruda.strip("|").split("|")]
            # Fila separadora (---|:--:|---)
            if all(re.fullmatch(r":?-{2,}:?", c) for c in celdas if c):
                continue
            filas.append(celdas)
        return filas, i

    def _leer_cita(self, lineas, i):
        bloque = []
        while i < len(lineas) and lineas[i].strip().startswith(">"):
            bloque.append(lineas[i].strip().lstrip(">").strip())
            i += 1
        return " ".join(x for x in bloque if x), i

    def _leer_parrafo(self, lineas, i):
        bloque = []
        while i < len(lineas):
            d = lineas[i].strip()
            if (not d or d.startswith(("|", ">", "```", "#"))
                    or re.match(r"^[-*]\s+", d) or re.match(r"^\d+\.\s+", d)
                    or d in ("---", "***", "___")):
                break
            bloque.append(d)
            i += 1
        return " ".join(bloque), i

    def _leer_lista(self, lineas, i):
        """Lee una lista completa.

        Se acumulan pares (vineta, texto) y los parrafos se arman al final:
        asi una linea de continuacion no puede hacer perder la vineta del item.
        """
        crudos = []
        while i < len(lineas):
            d = lineas[i].strip()
            if not d:
                # Una linea en blanco corta la lista solo si lo que sigue no lo es.
                siguiente = lineas[i + 1].strip() if i + 1 < len(lineas) else ""
                if not (re.match(r"^[-*]\s+", siguiente)
                        or re.match(r"^\d+\.\s+", siguiente)):
                    i += 1
                    break
                i += 1
                continue

            m_ul = re.match(r"^[-*]\s+(.*)$", d)
            m_ol = re.match(r"^(\d+)\.\s+(.*)$", d)
            if m_ul:
                texto = m_ul.group(1)
                casilla = ""
                if texto.startswith("[ ]"):
                    casilla, texto = "\u25a1", texto[3:].strip()
                elif texto.lower().startswith("[x]"):
                    casilla, texto = "\u25a0", texto[3:].strip()
                crudos.append([casilla or "\u2022", texto])
                i += 1
            elif m_ol:
                crudos.append([f"{m_ol.group(1)}.", m_ol.group(2)])
                i += 1
            elif crudos and lineas[i].startswith(("  ", "\t")):
                crudos[-1][1] += " " + d      # continuacion del item anterior
                i += 1
            else:
                break

        items = [
            Paragraph(inline(texto), self.e["lista"], bulletText=vineta)
            for vineta, texto in crudos
        ]
        items.append(Spacer(1, 6))
        return items, i

    # --- constructores ------------------------------------------------

    def _encabezado(self, nivel, texto):
        texto = limpiar(texto).strip()
        self.contador += 1
        ancla = f"h{self.contador}"
        estilo = self.e[f"h{nivel}"]
        parrafo = Paragraph(f'<a name="{ancla}"/>{inline(texto)}', estilo)
        # Se anota para el índice; el nivel 1 es el título de cada documento.
        parrafo._toc = (nivel - 1, re.sub(r"<[^>]+>", "", inline(texto)), ancla)
        return parrafo

    def _codigo(self, lineas):
        # Se reduce el cuerpo si alguna línea excede el ancho disponible.
        mas_larga = max((len(l) for l in lineas), default=0)
        tam = 8.2
        ancho_car = pdfmetrics.stringWidth("M", "Mono", tam)
        while mas_larga * ancho_car > ANCHO_UTIL - 16 and tam > 5.4:
            tam -= 0.3
            ancho_car = pdfmetrics.stringWidth("M", "Mono", tam)

        estilo = ParagraphStyle(
            "cod", parent=self.e["codigo"], fontSize=tam, leading=tam * 1.38)
        pre = Preformatted("\n".join(limpiar(l) for l in lineas), estilo)

        t = Table([[pre]], colWidths=[ANCHO_UTIL])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), FONDO_COD),
            ("BOX", (0, 0), (-1, -1), 0.5, LINEA),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        return KeepTogether([t, Spacer(1, 9)]) if len(lineas) <= 22 else t

    def _cita(self, texto):
        p = Paragraph(inline(texto), self.e["cita"])
        t = Table([[p]], colWidths=[ANCHO_UTIL])
        t.setStyle(TableStyle([
            ("LINEBEFORE", (0, 0), (0, -1), 2.2, ACENTO),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7F9FC")),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        return KeepTogether([t, Spacer(1, 10)])

    @staticmethod
    def _partes(celda):
        """Parte una celda en tramos (texto, ¿es código?) según los backticks."""
        limpio = re.sub(r"[*\[\]]|\((?:https?|mailto)[^)]*\)", "", limpiar(celda))
        tramos, es_codigo = [], False
        for tramo in limpio.split("`"):
            if tramo:
                tramos.append((tramo, es_codigo))
            es_codigo = not es_codigo
        return tramos

    def _ancho_texto(self, celda):
        """Ancho de la celda completa en una sola línea."""
        return sum(
            pdfmetrics.stringWidth(t, "Mono" if cod else "Cuerpo", 9)
            for t, cod in self._partes(celda)
        ) + 12

    def _ancho_token(self, celda):
        """Ancho de la palabra más larga: la columna no puede bajar de ahí."""
        mayor = 0
        for tramo, cod in self._partes(celda):
            for palabra in tramo.split():
                mayor = max(mayor, pdfmetrics.stringWidth(
                    palabra, "Mono" if cod else "Cuerpo", 9))
        return mayor

    def _tabla(self, filas):
        n = max(len(f) for f in filas)
        filas = [f + [""] * (n - len(f)) for f in filas]

        datos = [[Paragraph(inline(c), self.e["celda_cab"]) for c in filas[0]]]
        for fila in filas[1:]:
            datos.append([Paragraph(inline(c), self.e["celda"]) for c in fila])

        # Ancho proporcional al contenido real. Se mide con las métricas de
        # cada fuente, no contando caracteres: la mono es bastante más ancha
        # que la de cuerpo, y estimarlas igual partía las rutas a la mitad.
        naturales, minimos = [], []
        for col in range(n):
            naturales.append(max(self._ancho_texto(f[col]) for f in filas))
            minimos.append(max(self._ancho_token(f[col]) for f in filas))

        total = sum(naturales) or 1
        anchos = [ANCHO_UTIL * a / total for a in naturales]

        # Ninguna columna debe quedar más angosta que su palabra más larga.
        for c in range(n):
            anchos[c] = max(anchos[c], min(minimos[c] + 12, ANCHO_UTIL / 2))

        exceso = sum(anchos) - ANCHO_UTIL
        while exceso > 0.5:  # recorta desde la columna con más holgura
            c = max(range(n), key=lambda k: anchos[k] - minimos[k])
            recorte = min(exceso, anchos[c] - minimos[c])
            if recorte <= 0:
                break
            anchos[c] -= recorte
            exceso -= recorte

        t = Table(datos, colWidths=anchos, repeatRows=1)
        estilo = [
            ("BACKGROUND", (0, 0), (-1, 0), FONDO_CAB),
            ("LINEBELOW", (0, 0), (-1, 0), 0.7, colors.HexColor("#C3CFDD")),
            ("GRID", (0, 0), (-1, -1), 0.4, LINEA),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
        for r in range(1, len(datos)):
            if r % 2 == 0:
                estilo.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor("#FAFBFD")))
        t.setStyle(TableStyle(estilo))
        return KeepTogether([t, Spacer(1, 11)]) if len(datos) <= 12 else t


# ----------------------------------------------------------------------
# Documento
# ----------------------------------------------------------------------

class Documento(BaseDocTemplate):
    """Plantilla que alimenta el índice y numera las páginas."""

    def __init__(self, ruta, **kw):
        super().__init__(ruta, pagesize=A4,
                         leftMargin=21 * mm, rightMargin=21 * mm,
                         topMargin=20 * mm, bottomMargin=18 * mm, **kw)
        marco = Frame(self.leftMargin, self.bottomMargin,
                      self.width, self.height, id="normal")
        self.addPageTemplates([
            PageTemplate(id="portada", frames=[marco]),
            PageTemplate(id="contenido", frames=[marco], onPage=self._pie),
        ])

    def _pie(self, canvas, doc):
        canvas.saveState()
        canvas.setFont("Cuerpo", 8)
        canvas.setFillColor(GRIS)
        canvas.drawString(self.leftMargin, 12 * mm, "Suite ARP IA")
        canvas.drawRightString(A4[0] - self.rightMargin, 12 * mm, str(doc.page))
        canvas.setStrokeColor(LINEA)
        canvas.setLineWidth(0.5)
        canvas.line(self.leftMargin, 15 * mm, A4[0] - self.rightMargin, 15 * mm)
        canvas.restoreState()

    def afterFlowable(self, flowable):
        """Registra los encabezados marcados para el índice."""
        toc = getattr(flowable, "_toc", None)
        if toc:
            nivel, texto, ancla = toc
            self.canv.bookmarkPage(ancla)
            self.notify("TOCEntry", (nivel, texto, self.page, ancla))


def construir(salida: Path) -> Path:
    registrar_fuentes()
    e = crear_estilos()
    doc = Documento(str(salida), title="Suite ARP IA — Documentación",
                    author="Dercorp", subject="Sistema de compensaciones")

    hoy = datetime.now().strftime("%d-%m-%Y")
    historia = []

    # --- Portada ---
    historia += [
        Spacer(1, 58 * mm),
        Paragraph("Suite ARP IA", e["titulo_portada"]),
        HRFlowable(width="34%", thickness=2.4, color=ACENTO,
                   spaceBefore=7, spaceAfter=15, hAlign="LEFT"),
        Paragraph("Documentación técnica y guía de migración", e["sub_portada"]),
        Spacer(1, 52 * mm),
        Paragraph(
            f"Sistema de compensaciones · Dercorp<br/>"
            f"suitearia.streamlit.app<br/>"
            f"github.com/ariquelme91/SuiteArp<br/><br/>"
            f"Generado el {hoy}",
            e["meta_portada"],
        ),
        NextPageTemplate("contenido"),
        PageBreak(),
    ]

    # --- Índice ---
    indice = TableOfContents()
    indice.levelStyles = [e["toc1"], e["toc2"], e["toc3"]]
    indice.dotsMinLevel = 0
    historia += [Paragraph("Índice", e["titulo_toc"]), indice, PageBreak()]

    # --- Documentos ---
    conversor = Conversor(e)
    for idx, (archivo, _) in enumerate(DOCUMENTOS):
        ruta = RAIZ / archivo
        if not ruta.exists():
            sys.exit(f"No se encontró {ruta}")
        lineas = io.open(ruta, encoding="utf-8").read().split("\n")
        historia.extend(conversor.convertir(lineas))
        if idx < len(DOCUMENTOS) - 1:
            historia.append(PageBreak())

    # multiBuild resuelve las páginas del índice en una segunda pasada.
    doc.multiBuild(historia)
    return salida


def main():
    p = argparse.ArgumentParser(description="Genera el PDF de la documentación")
    p.add_argument("-o", "--salida", default=str(RAIZ / "Suite_ARP_IA_Documentacion.pdf"))
    args = p.parse_args()

    destino = construir(Path(args.salida))
    kb = destino.stat().st_size / 1024
    print(f"PDF generado: {destino}  ({kb:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
