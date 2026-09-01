# -*- coding: utf-8 -*-
"""
app.py
------
LATENTE FINANZAS WEB
Aplicación Flask mobile-first que reemplaza el Excel de finanzas del
Laboratorio de Transformación Digital LATENTE. El emprendedor responde
un formulario guiado y la app calcula automáticamente costos, precio
sugerido, flujo de caja y capacidad de endeudamiento, mostrando un
Dashboard con alertas y recomendaciones.

No requiere login. Los datos se guardan en la sesión del navegador
(cookie firmada de Flask) mientras el usuario navega por la app.
"""

from flask import Flask, render_template, request, redirect, url_for, session

import calculations as calc

app = Flask(__name__)
# Clave de sesión: en un entorno real esto debería venir de una variable
# de entorno. Para el prototipo demostrable basta con un valor fijo.
app.secret_key = "latente-finanzas-clave-demo-2026"


# ---------------------------------------------------------------------------
# FILTROS DE PLANTILLA (para mostrar números legibles en los templates)
# ---------------------------------------------------------------------------
@app.template_filter("moneda")
def filtro_moneda(valor):
    """Muestra un número como dinero, con separador de miles con punto.
    Ejemplo: 1234567.8 -> '1.234.568'
    """
    try:
        return "{:,.0f}".format(float(valor)).replace(",", ".")
    except (ValueError, TypeError):
        return "0"


@app.template_filter("porcentaje")
def filtro_porcentaje(valor):
    """Muestra un número como porcentaje con un decimal. Ejemplo: 30.456 -> '30.5%'"""
    try:
        return "{:.1f}%".format(float(valor))
    except (ValueError, TypeError):
        return "0%"


# ---------------------------------------------------------------------------
# DATOS DE EJEMPLO (producto tipo hamburguesa, igual a la guía del Excel)
# ---------------------------------------------------------------------------
DATOS_EJEMPLO = {
    "negocio": {
        "nombre_negocio": "Mi Negocio Latente",
        "tipo_negocio": "Restaurante",
        "producto": "Hamburguesa clásica",
        "ciudad": "Bello, Antioquia",
        "unidades_mes": "100",
        "precio_actual": "25000",
        "margen_deseado": "30",
    },
    "materia_prima": [
        {"nombre": "Pan", "costo_compra": "12000", "cantidad_compra": "12", "cantidad_usada": "1"},
        {"nombre": "Carne", "costo_compra": "45000", "cantidad_compra": "1000", "cantidad_usada": "150"},
        {"nombre": "Queso", "costo_compra": "18000", "cantidad_compra": "20", "cantidad_usada": "1"},
    ],
    "mano_obra": [
        {"nombre": "Cocinero", "pago_mensual": "1300000", "horas_mes": "160", "minutos_unidad": "6"},
        {"nombre": "Auxiliar", "pago_mensual": "800000", "horas_mes": "120", "minutos_unidad": "3"},
    ],
    "costos_indirectos": [
        {"concepto": "Arriendo", "valor_mensual": "800000", "porcentaje_asignado": "100"},
        {"concepto": "Servicios públicos", "valor_mensual": "250000", "porcentaje_asignado": "100"},
        {"concepto": "Internet", "valor_mensual": "80000", "porcentaje_asignado": "50"},
        {"concepto": "Contabilidad", "valor_mensual": "150000", "porcentaje_asignado": "100"},
    ],
    "costos_operativos": [
        {"concepto": "Empaque", "costo_fijo_unidad": "1200", "porcentaje_venta": "0"},
        {"concepto": "Servilletas", "costo_fijo_unidad": "300", "porcentaje_venta": "0"},
        {"concepto": "Comisión pasarela de pago", "costo_fijo_unidad": "0", "porcentaje_venta": "3"},
    ],
    "flujo_caja": {
        "ingresos_mensuales": "2500000",
        "otros_ingresos": "0",
        "gastos_fijos": "1280000",
        "gastos_variables": "300000",
        "pago_deudas": "0",
        "impuestos": "50000",
        "inversiones": "0",
        "caja_inicial": "1000000",
    },
    "financiamiento": {
        "monto": "5000000",
        "tasa_anual": "25",
        "plazo_meses": "24",
    },
}


# ---------------------------------------------------------------------------
# FUNCIONES AUXILIARES DE SESIÓN
# ---------------------------------------------------------------------------
def get_seccion(nombre, valor_defecto):
    """Obtiene una sección de datos de la sesión, o un valor por defecto."""
    return session.get(nombre, valor_defecto)


def calcular_todo():
    """
    Recalcula todos los indicadores financieros a partir de lo que hay
    guardado en la sesión. Se llama cada vez que el Dashboard o las
    Recomendaciones necesitan números frescos.
    Devuelve None si todavía no hay datos mínimos (negocio) cargados.
    """
    negocio = session.get("negocio")
    if not negocio:
        return None

    materia_prima = session.get("materia_prima", [])
    mano_obra = session.get("mano_obra", [])
    costos_indirectos = session.get("costos_indirectos", [])
    costos_operativos = session.get("costos_operativos", [])
    flujo_caja_datos = session.get("flujo_caja", {})
    financiamiento_datos = session.get("financiamiento", {})

    mp = calc.calcular_materia_prima(materia_prima)
    mo = calc.calcular_mano_obra(mano_obra)
    ci = calc.calcular_costos_indirectos(costos_indirectos, negocio.get("unidades_mes"))
    co = calc.calcular_costos_operativos(costos_operativos, negocio.get("precio_actual"))

    costos_precios = calc.calcular_costos_y_precios(
        negocio, mp["total_unitario"], mo["total_unitario"],
        ci["total_unitario"], co["total_unitario"]
    )

    flujo = calc.calcular_flujo_caja(flujo_caja_datos)
    financiamiento = calc.calcular_financiamiento(
        financiamiento_datos, costos_precios["utilidad_mensual"]
    )
    # El estado de resultados necesita saber cuánto del gasto financiero e
    # impuestos mensuales aplicar; se los pasamos dentro del mismo dict para
    # no tener que cambiar la firma de calcular_financiamiento.
    financiamiento_para_resultados = dict(financiamiento)
    financiamiento_para_resultados["impuestos_mensuales"] = flujo["impuestos"]

    costo_variable_unitario = mp["total_unitario"] + mo["total_unitario"] + co["total_unitario"]

    # Usamos el precio ya convertido a float desde costos_precios, para no
    # volver a parsear el texto del formulario.
    punto_equilibrio = calc.calcular_punto_equilibrio(
        ci["total_asignado_mensual"], costos_precios["precio_actual"], costo_variable_unitario
    )

    estado_resultados = calc.calcular_estado_resultados(
        negocio, costo_variable_unitario, ci["total_asignado_mensual"], financiamiento_para_resultados
    )

    proyeccion = calc.calcular_proyeccion_flujo_caja(flujo, meses=12)

    recomendaciones = calc.generar_recomendaciones(
        costos_precios, flujo, financiamiento,
        punto_equilibrio=punto_equilibrio, proyeccion=proyeccion,
    )

    return {
        "negocio": negocio,
        "materia_prima": mp,
        "mano_obra": mo,
        "costos_indirectos": ci,
        "costos_operativos": co,
        "costos_precios": costos_precios,
        "flujo_caja": flujo,
        "financiamiento": financiamiento,
        "punto_equilibrio": punto_equilibrio,
        "estado_resultados": estado_resultados,
        "proyeccion": proyeccion,
        "recomendaciones": recomendaciones,
    }


def _lista_desde_formulario(prefijo, campos):
    """
    Reconstruye una lista de dicts a partir de campos de formulario tipo
    array: nombre="mp_nombre[]", etc. `campos` es un dict
    {clave_interna: nombre_de_campo_html_sin_corchetes}.
    Se descartan filas totalmente vacías.
    """
    listas = {clave: request.form.getlist(f"{prefijo}_{campo}[]")
              for clave, campo in campos.items()}
    # Todas las listas deben tener la misma longitud (una fila por índice)
    largo = max((len(v) for v in listas.values()), default=0)
    filas = []
    for i in range(largo):
        fila = {}
        vacio = True
        for clave in campos:
            valores = listas[clave]
            valor = valores[i] if i < len(valores) else ""
            fila[clave] = valor
            if valor.strip():
                vacio = False
        if not vacio:
            filas.append(fila)
    return filas


# ---------------------------------------------------------------------------
# RUTAS
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/cargar-ejemplo")
def cargar_ejemplo():
    """Precarga datos de ejemplo (hamburguesa) en la sesión para demostrar la app."""
    for clave, valor in DATOS_EJEMPLO.items():
        session[clave] = valor
    return redirect(url_for("diagnostico"))


@app.route("/reiniciar")
def reiniciar():
    """Borra todos los datos de la sesión y vuelve al inicio."""
    session.clear()
    return redirect(url_for("index"))


@app.route("/diagnostico", methods=["GET", "POST"])
def diagnostico():
    errores = []
    if request.method == "POST":
        nombre_negocio = request.form.get("nombre_negocio", "").strip()
        producto = request.form.get("producto", "").strip()
        unidades_mes = request.form.get("unidades_mes", "")
        precio_actual = request.form.get("precio_actual", "")
        margen_deseado = request.form.get("margen_deseado", "")

        if not nombre_negocio:
            errores.append("Escribe el nombre de tu negocio.")
        if not producto:
            errores.append("Escribe el producto o servicio principal.")
        if calc._to_float(unidades_mes) <= 0:
            errores.append("Las unidades vendidas al mes deben ser mayores a 0.")
        if calc._to_float(precio_actual) <= 0:
            errores.append("El precio actual debe ser mayor a 0.")
        if not (0 <= calc._to_float(margen_deseado) < 100):
            errores.append("El margen deseado debe estar entre 0 y 99%.")

        if not errores:
            session["negocio"] = {
                "nombre_negocio": nombre_negocio,
                "tipo_negocio": request.form.get("tipo_negocio", "").strip(),
                "producto": producto,
                "ciudad": request.form.get("ciudad", "").strip(),
                "unidades_mes": unidades_mes,
                "precio_actual": precio_actual,
                "margen_deseado": margen_deseado,
            }
            return redirect(url_for("costos"))

    negocio = get_seccion("negocio", {})
    return render_template("diagnostico.html", negocio=negocio, errores=errores)


@app.route("/costos", methods=["GET", "POST"])
def costos():
    if not session.get("negocio"):
        return redirect(url_for("diagnostico"))

    errores = []
    if request.method == "POST":
        materia_prima = _lista_desde_formulario("mp", {
            "nombre": "nombre", "costo_compra": "costo_compra",
            "cantidad_compra": "cantidad_compra", "cantidad_usada": "cantidad_usada",
        })
        mano_obra = _lista_desde_formulario("mo", {
            "nombre": "nombre", "pago_mensual": "pago_mensual",
            "horas_mes": "horas_mes", "minutos_unidad": "minutos_unidad",
        })
        costos_indirectos = _lista_desde_formulario("ci", {
            "concepto": "concepto", "valor_mensual": "valor_mensual",
            "porcentaje_asignado": "porcentaje_asignado",
        })
        costos_operativos = _lista_desde_formulario("co", {
            "concepto": "concepto", "costo_fijo_unidad": "costo_fijo_unidad",
            "porcentaje_venta": "porcentaje_venta",
        })

        if not materia_prima and not mano_obra:
            errores.append(
                "Agrega al menos un insumo de materia prima o un rol de mano de obra "
                "para poder calcular el costo del producto."
            )

        if not errores:
            session["materia_prima"] = materia_prima
            session["mano_obra"] = mano_obra
            session["costos_indirectos"] = costos_indirectos
            session["costos_operativos"] = costos_operativos
            return redirect(url_for("flujo_caja"))

    contexto = {
        "negocio": get_seccion("negocio", {}),
        "materia_prima": get_seccion("materia_prima", []),
        "mano_obra": get_seccion("mano_obra", []),
        "costos_indirectos": get_seccion("costos_indirectos", []),
        "costos_operativos": get_seccion("costos_operativos", []),
        "errores": errores,
    }
    return render_template("costos.html", **contexto)


@app.route("/flujo-caja", methods=["GET", "POST"])
def flujo_caja():
    if not session.get("negocio"):
        return redirect(url_for("diagnostico"))

    errores = []
    if request.method == "POST":
        campos = ["ingresos_mensuales", "otros_ingresos", "gastos_fijos",
                   "gastos_variables", "pago_deudas", "impuestos",
                   "inversiones", "caja_inicial"]
        datos = {campo: request.form.get(campo, "0") for campo in campos}

        if calc._to_float(datos["ingresos_mensuales"]) < 0:
            errores.append("Los ingresos mensuales no pueden ser negativos.")

        if not errores:
            session["flujo_caja"] = datos
            return redirect(url_for("financiamiento"))

    contexto = {
        "negocio": get_seccion("negocio", {}),
        "datos": get_seccion("flujo_caja", {}),
        "errores": errores,
    }
    return render_template("flujo_caja.html", **contexto)


@app.route("/financiamiento", methods=["GET", "POST"])
def financiamiento():
    if not session.get("negocio"):
        return redirect(url_for("diagnostico"))

    errores = []
    if request.method == "POST":
        datos = {
            "monto": request.form.get("monto", "0"),
            "tasa_anual": request.form.get("tasa_anual", "0"),
            "plazo_meses": request.form.get("plazo_meses", "0"),
        }
        monto = calc._to_float(datos["monto"])
        plazo = calc._to_float(datos["plazo_meses"])
        if monto > 0 and plazo <= 0:
            errores.append("Si vas a simular un crédito, indica el plazo en meses.")

        if not errores:
            session["financiamiento"] = datos
            return redirect(url_for("dashboard"))

    contexto = {
        "negocio": get_seccion("negocio", {}),
        "datos": get_seccion("financiamiento", {}),
        "errores": errores,
    }
    return render_template("financiamiento.html", **contexto)


@app.route("/dashboard")
def dashboard():
    resultado = calcular_todo()
    if resultado is None:
        return redirect(url_for("diagnostico"))
    return render_template("dashboard.html", **resultado)


@app.route("/recomendaciones")
def recomendaciones():
    resultado = calcular_todo()
    if resultado is None:
        return redirect(url_for("diagnostico"))
    return render_template("recomendaciones.html", **resultado)


if __name__ == "__main__":
    app.run(debug=True)
