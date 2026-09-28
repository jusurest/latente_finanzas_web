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


# ==========================
# Indicadores SENA / Fondo Emprender
# ==========================

def _latente_sena_float(value, default=0.0):
    try:
        if value is None:
            return default
        if isinstance(value, str):
            value = value.strip().replace("$", "").replace("%", "")
            value = value.replace(".", "").replace(",", ".") if "," in value else value
            if value == "":
                return default
        return float(value)
    except Exception:
        return default


def _latente_sena_money(value):
    try:
        n = float(value or 0)
    except Exception:
        n = 0
    return ("$" + f"{n:,.0f}").replace(",", ".")


def _latente_sena_percent(value):
    try:
        n = float(value or 0)
    except Exception:
        n = 0
    return f"{n * 100:.1f}%".replace(".", ",")


def _latente_sena_number(value, decimals=2):
    try:
        n = float(value or 0)
    except Exception:
        n = 0
    return f"{n:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _latente_sena_get(obj, *keys, default=0):
    for key in keys:
        try:
            if isinstance(obj, dict) and key in obj:
                return obj.get(key, default)
            if hasattr(obj, key):
                return getattr(obj, key)
            if hasattr(obj, "__getitem__"):
                return obj[key]
        except Exception:
            pass
    return default


def _latente_sena_calc():
    try:
        if "calculate_all" in globals():
            return calculate_all()
    except Exception:
        pass
    try:
        from calculations import calculate_all as _calc
        try:
            return _calc()
        except TypeError:
            try:
                return _calc(session)
            except Exception:
                return {}
    except Exception:
        return {}


def _latente_sena_session_value(*keys, default=0):
    try:
        for source_key in ["business", "datos_negocio", "diagnostico", "cash_flow", "financing"]:
            source = session.get(source_key, {})
            if isinstance(source, dict):
                for key in keys:
                    if key in source:
                        return source.get(key, default)
    except Exception:
        pass
    return default


def _latente_sena_build_indicators():
    calc = _latente_sena_calc()

    units = _latente_sena_float(_latente_sena_get(calc, "units_per_month", default=_latente_sena_session_value("units_per_month", "unidades_mes")))
    price = _latente_sena_float(_latente_sena_get(calc, "current_price", default=_latente_sena_session_value("current_price", "precio_actual")))
    sales = _latente_sena_float(_latente_sena_get(calc, "total_income", default=units * price))
    expenses = _latente_sena_float(_latente_sena_get(calc, "total_expenses", default=0))
    utility = _latente_sena_float(_latente_sena_get(calc, "monthly_profit", default=sales - expenses))
    margin = _latente_sena_float(_latente_sena_get(calc, "current_margin", default=(utility / sales if sales else 0)))
    net_cash = _latente_sena_float(_latente_sena_get(calc, "net_cash_flow", default=utility))
    ending_cash = _latente_sena_float(_latente_sena_get(calc, "ending_cash", default=net_cash))
    payment = _latente_sena_float(_latente_sena_get(calc, "monthly_payment", default=_latente_sena_session_value("monthly_payment", "cuota_mensual")))
    coverage = _latente_sena_float(_latente_sena_get(calc, "payment_coverage", default=(utility / payment if payment else 0)))
    loan = _latente_sena_float(_latente_sena_get(calc, "loan_amount", default=_latente_sena_session_value("loan_amount", "monto_credito")))
    variable_unit = (
        _latente_sena_float(_latente_sena_get(calc, "mp_unit_total", default=0))
        + _latente_sena_float(_latente_sena_get(calc, "labor_unit_total", default=0))
        + _latente_sena_float(_latente_sena_get(calc, "operational_unit_total", default=0))
    )
    fixed_monthly = _latente_sena_float(_latente_sena_get(calc, "indirect_monthly", default=0))
    contribution = price - variable_unit
    breakeven = fixed_monthly / contribution if contribution > 0 else 0

    labor_details = _latente_sena_get(calc, "labor_details", default=[])
    try:
        jobs = len([x for x in labor_details if x])
    except Exception:
        try:
            jobs = len(session.get("labor", []))
        except Exception:
            jobs = 0

    def status_money_positive(value):
        if value > 0:
            return ("good", "Positivo")
        if value == 0:
            return ("warn", "En cero")
        return ("bad", "Negativo")

    margin_status = ("good", "Rentable") if margin >= 0.25 else ("warn", "Por mejorar") if margin > 0 else ("bad", "Crítico")
    coverage_status = ("info", "Sin crédito") if payment <= 0 else ("good", "Sostenible") if coverage >= 1.5 else ("warn", "Ajustado") if coverage >= 1 else ("bad", "No cubre")
    cash_status = status_money_positive(net_cash)
    utility_status = status_money_positive(utility)

    indicators = [
        {"name": "Ventas mensuales proyectadas", "value": _latente_sena_money(sales), "status": "info" if sales > 0 else "warn", "reading": "Reportado" if sales > 0 else "Falta dato", "relevance": "Ayuda a sustentar la proyección de ventas del plan de negocio."},
        {"name": "Costos y gastos mensuales", "value": _latente_sena_money(expenses), "status": "info" if expenses > 0 else "warn", "reading": "Reportado" if expenses > 0 else "Falta dato", "relevance": "Permite explicar la estructura de costos y gastos de la iniciativa."},
        {"name": "Utilidad mensual estimada", "value": _latente_sena_money(utility), "status": utility_status[0], "reading": utility_status[1], "relevance": "Aporta a la lectura de viabilidad económica y financiera."},
        {"name": "Margen actual", "value": _latente_sena_percent(margin), "status": margin_status[0], "reading": margin_status[1], "relevance": "Muestra si el precio permite cubrir costos y generar excedente."},
        {"name": "Flujo de caja neto", "value": _latente_sena_money(net_cash), "status": cash_status[0], "reading": cash_status[1], "relevance": "Sirve para revisar sostenibilidad operativa y capacidad de pago."},
        {"name": "Saldo final de caja", "value": _latente_sena_money(ending_cash), "status": "good" if ending_cash > 0 else "warn" if ending_cash == 0 else "bad", "reading": "Con caja" if ending_cash > 0 else "Sin margen" if ending_cash == 0 else "Caja negativa", "relevance": "Ayuda a anticipar si el negocio tendrá liquidez después de operar."},
        {"name": "Punto de equilibrio estimado", "value": (_latente_sena_number(breakeven, 0) + " unidades") if breakeven > 0 else "No calculable", "status": "info" if breakeven > 0 else "warn", "reading": "Calculado" if breakeven > 0 else "Faltan datos", "relevance": "Indica cuántas unidades debería vender para cubrir costos."},
        {"name": "Inversión o crédito solicitado", "value": _latente_sena_money(loan), "status": "info" if loan > 0 else "warn", "reading": "Reportado" if loan > 0 else "No indicado", "relevance": "Se relaciona con el valor del proyecto y posibles necesidades de financiación."},
        {"name": "Cobertura de cuota", "value": "Sin crédito" if payment <= 0 else (_latente_sena_number(coverage, 2) + " veces"), "status": coverage_status[0], "reading": coverage_status[1], "relevance": "Permite revisar si la utilidad estimada alcanza para cubrir una deuda."},
        {"name": "Roles / empleos directos registrados", "value": str(jobs), "status": "info" if jobs > 0 else "warn", "reading": "Reportado" if jobs > 0 else "No indicado", "relevance": "Fondo Emprender revisa generación de autoempleos, puestos de trabajo o empleos directos."},
    ]

    max_bar = max(abs(sales), abs(expenses), abs(net_cash), abs(utility), 1)
    bars = [
        {"label": "Ventas proyectadas", "value": _latente_sena_money(sales), "width": min(abs(sales) / max_bar * 100, 100), "kind": ""},
        {"label": "Costos y gastos", "value": _latente_sena_money(expenses), "width": min(abs(expenses) / max_bar * 100, 100), "kind": "cost"},
        {"label": "Utilidad estimada", "value": _latente_sena_money(utility), "width": min(abs(utility) / max_bar * 100, 100), "kind": "cash"},
        {"label": "Flujo de caja neto", "value": _latente_sena_money(net_cash), "width": min(abs(net_cash) / max_bar * 100, 100), "kind": "cash"},
    ]

    summary = {
        "utility": _latente_sena_money(utility),
        "utility_class": utility_status[0],
        "cash_flow": _latente_sena_money(net_cash),
        "cash_class": cash_status[0],
        "margin": _latente_sena_percent(margin),
        "margin_class": margin_status[0],
        "coverage": "Sin crédito" if payment <= 0 else (_latente_sena_number(coverage, 2) + "x"),
        "coverage_class": coverage_status[0],
    }

    return indicators, bars, summary


@app.route("/indicadores-sena")
def indicadores_sena():
    indicators, bars, summary = _latente_sena_build_indicators()
    return render_template("indicadores_sena.html", indicators=indicators, bars=bars, summary=summary)


@app.route("/datos-ejemplo-sena")
def datos_ejemplo_sena():
    # Carga un ejemplo financiero y abre directamente los indicadores SENA.
    session["business"] = {
        "business_name": "Hamburguesas Latente",
        "business_type": "Comidas rápidas",
        "product_name": "Hamburguesa clásica",
        "city": "Envigado",
        "units_per_month": 180,
        "current_price": 18000,
        "desired_margin": 0.30,
    }
    session["mp"] = [
        {"name": "Pan", "purchase_cost": 18000, "purchase_qty": 24, "used_qty": 1, "notes": ""},
        {"name": "Carne", "purchase_cost": 50000, "purchase_qty": 1000, "used_qty": 150, "notes": ""},
        {"name": "Queso", "purchase_cost": 22000, "purchase_qty": 20, "used_qty": 1, "notes": ""},
        {"name": "Vegetales y salsas", "purchase_cost": 30000, "purchase_qty": 30, "used_qty": 1, "notes": ""},
    ]
    session["labor"] = [
        {"role": "Cocinero", "monthly_pay": 1300000, "monthly_hours": 160, "minutes_per_unit": 8, "notes": ""},
        {"role": "Auxiliar", "monthly_pay": 800000, "monthly_hours": 120, "minutes_per_unit": 4, "notes": ""},
    ]
    session["indirect"] = [
        {"concept": "Arriendo", "monthly_value": 900000, "assigned_pct": 1, "notes": ""},
        {"concept": "Servicios públicos", "monthly_value": 300000, "assigned_pct": 1, "notes": ""},
        {"concept": "Internet y software", "monthly_value": 120000, "assigned_pct": 0.5, "notes": ""},
    ]
    session["operational"] = [
        {"concept": "Empaque", "fixed_unit_cost": 1200, "sale_pct": 0, "notes": ""},
        {"concept": "Servilletas", "fixed_unit_cost": 300, "sale_pct": 0, "notes": ""},
        {"concept": "Comisión pasarela", "fixed_unit_cost": 0, "sale_pct": 0.03, "notes": ""},
    ]
    session["cash_flow"] = {
        "initial_cash": 1500000,
        "sales_income": 3240000,
        "other_income": 0,
        "raw_material_purchase": 1737000,
        "payroll": 980000,
        "fixed_expenses": 1260000,
        "operative_expenses": 367200,
        "debt_payments": 0,
        "taxes": 150000,
        "investments": 100000,
    }
    session["financing"] = {"loan_amount": 4000000, "annual_rate": 0.25, "term_months": 24}
    session.modified = True
    return redirect("/indicadores-sena")


if __name__ == "__main__":
    app.run(debug=True)
