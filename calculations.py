# -*- coding: utf-8 -*-
"""
calculations.py
----------------
Toda la lógica financiera de LATENTE FINANZAS vive aquí, separada de Flask.
Cada función es pura: recibe datos simples (dict/list) y devuelve resultados
simples (dict). Esto facilita probar la lógica y mantenerla igual de
confiable que el Excel original.

Las fórmulas replican exactamente la hoja de cálculo base del proyecto:
- Costo total unitario = MP + MO + costos indirectos + costos operativos
- Precio sugerido = costo total unitario / (1 - margen deseado)
- Margen actual = (precio actual - costo total unitario) / precio actual
- Financiamiento con cuota fija (sistema de amortización francés simplificado)
"""


def _to_float(valor, default=0.0):
    """Convierte texto de formulario a float de forma segura.
    Si el usuario deja vacío o escribe algo inválido, no se rompe la app.
    """
    try:
        if valor is None or valor == "":
            return default
        return float(str(valor).replace(",", "."))
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# 1. MATERIA PRIMA
# ---------------------------------------------------------------------------
def calcular_materia_prima(insumos):
    """
    insumos: lista de dicts con:
        nombre, costo_compra, cantidad_compra, cantidad_usada
    Fórmula (igual que el Excel): costo_unitario = (costo_compra / cantidad_compra) * cantidad_usada
    """
    detalle = []
    total = 0.0
    for item in insumos:
        costo_compra = _to_float(item.get("costo_compra"))
        cantidad_compra = _to_float(item.get("cantidad_compra"))
        cantidad_usada = _to_float(item.get("cantidad_usada"))

        if cantidad_compra > 0:
            costo_unitario = (costo_compra / cantidad_compra) * cantidad_usada
        else:
            costo_unitario = 0.0

        detalle.append({
            "nombre": item.get("nombre", "").strip() or "Insumo",
            "costo_compra": costo_compra,
            "cantidad_compra": cantidad_compra,
            "cantidad_usada": cantidad_usada,
            "costo_unitario": costo_unitario,
        })
        total += costo_unitario

    return {"detalle": detalle, "total_unitario": total}


# ---------------------------------------------------------------------------
# 2. MANO DE OBRA
# ---------------------------------------------------------------------------
def calcular_mano_obra(roles):
    """
    roles: lista de dicts con:
        nombre, pago_mensual, horas_mes, minutos_unidad
    Fórmula: costo_hora = pago_mensual / horas_mes
             costo_unitario = costo_hora * (minutos_unidad / 60)
    """
    detalle = []
    total = 0.0
    for item in roles:
        pago_mensual = _to_float(item.get("pago_mensual"))
        horas_mes = _to_float(item.get("horas_mes"))
        minutos_unidad = _to_float(item.get("minutos_unidad"))

        costo_hora = (pago_mensual / horas_mes) if horas_mes > 0 else 0.0
        costo_unitario = costo_hora * (minutos_unidad / 60.0)

        detalle.append({
            "nombre": item.get("nombre", "").strip() or "Rol",
            "pago_mensual": pago_mensual,
            "horas_mes": horas_mes,
            "minutos_unidad": minutos_unidad,
            "costo_hora": costo_hora,
            "costo_unitario": costo_unitario,
        })
        total += costo_unitario

    return {"detalle": detalle, "total_unitario": total}


# ---------------------------------------------------------------------------
# 3. COSTOS INDIRECTOS (gastos fijos generales)
# ---------------------------------------------------------------------------
def calcular_costos_indirectos(gastos, unidades_mes):
    """
    gastos: lista de dicts con:
        concepto, valor_mensual, porcentaje_asignado (0-100)
    Fórmula: valor_asignado = valor_mensual * (porcentaje_asignado / 100)
             costo_unitario = valor_asignado / unidades_mes
    """
    detalle = []
    total_asignado = 0.0
    unidades_mes = _to_float(unidades_mes)

    for item in gastos:
        valor_mensual = _to_float(item.get("valor_mensual"))
        porcentaje = _to_float(item.get("porcentaje_asignado"))
        valor_asignado = valor_mensual * (porcentaje / 100.0)

        detalle.append({
            "concepto": item.get("concepto", "").strip() or "Gasto",
            "valor_mensual": valor_mensual,
            "porcentaje_asignado": porcentaje,
            "valor_asignado": valor_asignado,
        })
        total_asignado += valor_asignado

    costo_unitario = (total_asignado / unidades_mes) if unidades_mes > 0 else 0.0

    return {
        "detalle": detalle,
        "total_asignado_mensual": total_asignado,
        "total_unitario": costo_unitario,
    }


# ---------------------------------------------------------------------------
# 4. COSTOS OPERATIVOS (por venta / entrega)
# ---------------------------------------------------------------------------
def calcular_costos_operativos(costos, precio_actual):
    """
    costos: lista de dicts con:
        concepto, costo_fijo_unidad, porcentaje_venta (0-100)
    Fórmula: costo_unitario = costo_fijo_unidad + (porcentaje_venta/100 * precio_actual)
    """
    detalle = []
    total = 0.0
    precio_actual = _to_float(precio_actual)

    for item in costos:
        costo_fijo = _to_float(item.get("costo_fijo_unidad"))
        porcentaje = _to_float(item.get("porcentaje_venta"))
        costo_unitario = costo_fijo + (porcentaje / 100.0) * precio_actual

        detalle.append({
            "concepto": item.get("concepto", "").strip() or "Costo operativo",
            "costo_fijo_unidad": costo_fijo,
            "porcentaje_venta": porcentaje,
            "costo_unitario": costo_unitario,
        })
        total += costo_unitario

    return {"detalle": detalle, "total_unitario": total}


# ---------------------------------------------------------------------------
# 5. COSTOS Y PRECIOS (hoja central)
# ---------------------------------------------------------------------------
def calcular_costos_y_precios(negocio, mp_total, mo_total, ci_total, co_total):
    """
    Une las 4 categorías de costo y calcula precio sugerido, margen y utilidad.
    negocio: dict con precio_actual, margen_deseado (0-100), unidades_mes
    """
    precio_actual = _to_float(negocio.get("precio_actual"))
    margen_deseado = _to_float(negocio.get("margen_deseado")) / 100.0
    unidades_mes = _to_float(negocio.get("unidades_mes"))

    costo_total_unitario = mp_total + mo_total + ci_total + co_total

    if margen_deseado < 1:
        precio_sugerido = costo_total_unitario / (1 - margen_deseado)
    else:
        precio_sugerido = 0.0  # margen inválido (100% o más) evita división por cero/negativos

    margen_actual = ((precio_actual - costo_total_unitario) / precio_actual
                      if precio_actual > 0 else 0.0)
    utilidad_unitaria = precio_actual - costo_total_unitario
    utilidad_mensual = utilidad_unitaria * unidades_mes

    # Diagnóstico según las reglas exactas del proyecto
    if precio_actual < costo_total_unitario:
        diagnostico = "Alerta: estás vendiendo por debajo del costo."
        nivel = "alerta"
    elif margen_actual < margen_deseado:
        diagnostico = "Revisión necesaria: tu precio actual no alcanza el margen que deseas."
        nivel = "precaucion"
    else:
        diagnostico = "OK: tu precio cubre el costo y el margen deseado."
        nivel = "ok"

    return {
        "precio_actual": precio_actual,
        "margen_deseado": margen_deseado * 100.0,
        "unidades_mes": unidades_mes,
        "costo_mp_unitario": mp_total,
        "costo_mo_unitario": mo_total,
        "costo_ci_unitario": ci_total,
        "costo_co_unitario": co_total,
        "costo_total_unitario": costo_total_unitario,
        "precio_sugerido": precio_sugerido,
        "margen_actual": margen_actual * 100.0,
        "utilidad_unitaria": utilidad_unitaria,
        "utilidad_mensual": utilidad_mensual,
        "diagnostico": diagnostico,
        "nivel": nivel,
    }


# ---------------------------------------------------------------------------
# 6. FLUJO DE CAJA Y PRESUPUESTO
# ---------------------------------------------------------------------------
def calcular_flujo_caja(datos):
    """
    datos: dict con ingresos_mensuales, otros_ingresos, gastos_fijos,
           gastos_variables, pago_deudas, impuestos, inversiones, caja_inicial
    """
    ingresos_mensuales = _to_float(datos.get("ingresos_mensuales"))
    otros_ingresos = _to_float(datos.get("otros_ingresos"))
    gastos_fijos = _to_float(datos.get("gastos_fijos"))
    gastos_variables = _to_float(datos.get("gastos_variables"))
    pago_deudas = _to_float(datos.get("pago_deudas"))
    impuestos = _to_float(datos.get("impuestos"))
    inversiones = _to_float(datos.get("inversiones"))
    caja_inicial = _to_float(datos.get("caja_inicial"))

    total_ingresos = ingresos_mensuales + otros_ingresos
    total_egresos = gastos_fijos + gastos_variables + pago_deudas + impuestos + inversiones
    flujo_neto = total_ingresos - total_egresos
    saldo_final = caja_inicial + flujo_neto

    if saldo_final < 0:
        alerta = "Alerta: el negocio puede quedarse sin caja."
        nivel = "alerta"
    elif flujo_neto < 0:
        alerta = "Precaución: este mes el negocio está consumiendo caja."
        nivel = "precaucion"
    else:
        alerta = "OK: el flujo de caja proyectado es positivo."
        nivel = "ok"

    return {
        "ingresos_mensuales": ingresos_mensuales,
        "otros_ingresos": otros_ingresos,
        "gastos_fijos": gastos_fijos,
        "gastos_variables": gastos_variables,
        "pago_deudas": pago_deudas,
        "impuestos": impuestos,
        "inversiones": inversiones,
        "caja_inicial": caja_inicial,
        "total_ingresos": total_ingresos,
        "total_egresos": total_egresos,
        "flujo_neto": flujo_neto,
        "saldo_final": saldo_final,
        "alerta": alerta,
        "nivel": nivel,
    }


# ---------------------------------------------------------------------------
# 7. FINANCIAMIENTO
# ---------------------------------------------------------------------------
def calcular_financiamiento(datos, utilidad_mensual):
    """
    datos: dict con monto, tasa_anual (%), plazo_meses
    Cuota fija mensual (amortización francesa simplificada):
        tasa_mensual = tasa_anual / 12 / 100
        cuota = monto * tasa_mensual / (1 - (1 + tasa_mensual) ** -plazo)
    """
    monto = _to_float(datos.get("monto"))
    tasa_anual = _to_float(datos.get("tasa_anual"))
    plazo_meses = _to_float(datos.get("plazo_meses"))

    tasa_mensual = tasa_anual / 12.0 / 100.0

    if monto <= 0 or plazo_meses <= 0:
        cuota_mensual = 0.0
    elif tasa_mensual == 0:
        cuota_mensual = monto / plazo_meses
    else:
        cuota_mensual = monto * tasa_mensual / (1 - (1 + tasa_mensual) ** (-plazo_meses))

    total_pagado = cuota_mensual * plazo_meses
    total_intereses = total_pagado - monto if monto > 0 else 0.0

    if cuota_mensual > 0:
        cobertura = utilidad_mensual / cuota_mensual
    else:
        cobertura = 0.0

    if monto <= 0:
        diagnostico = "Sin crédito simulado todavía."
        nivel = "info"
    elif utilidad_mensual < cuota_mensual:
        diagnostico = "Alerta: la utilidad proyectada no cubre la cuota del crédito."
        nivel = "alerta"
    elif 1 <= cobertura <= 1.5:
        diagnostico = "Precaución: la cuota parece ajustada."
        nivel = "precaucion"
    else:
        diagnostico = "OK: según los datos ingresados, la cuota parece sostenible."
        nivel = "ok"

    return {
        "monto": monto,
        "tasa_anual": tasa_anual,
        "plazo_meses": plazo_meses,
        "cuota_mensual": cuota_mensual,
        "total_pagado": total_pagado,
        "total_intereses": total_intereses,
        "utilidad_mensual": utilidad_mensual,
        "cobertura": cobertura,
        "diagnostico": diagnostico,
        "nivel": nivel,
    }


# ---------------------------------------------------------------------------
# 8. PUNTO DE EQUILIBRIO
# ---------------------------------------------------------------------------
def calcular_punto_equilibrio(costo_fijo_mensual, precio_unitario, costo_variable_unitario):
    """
    Unidades que hay que vender al mes solo para cubrir los costos fijos
    (sin ganar ni perder). Es el dato clásico de "costo-volumen-utilidad"
    que no estaba en el Excel base pero que los emprendedores piden mucho.

    margen de contribución = precio - costo variable unitario
        (lo que deja cada unidad para pagar los costos fijos)
    unidades de equilibrio = costo fijo mensual / margen de contribución
    """
    margen_contribucion = precio_unitario - costo_variable_unitario

    if margen_contribucion <= 0:
        # El precio ni siquiera cubre el costo variable: nunca se llega
        # al punto de equilibrio subiendo unidades, hay que subir precio
        # o bajar costo variable primero.
        return {
            "aplica": False,
            "margen_contribucion": margen_contribucion,
            "unidades": 0.0,
            "valor_ventas": 0.0,
        }

    unidades = costo_fijo_mensual / margen_contribucion
    valor_ventas = unidades * precio_unitario

    return {
        "aplica": True,
        "margen_contribucion": margen_contribucion,
        "unidades": unidades,
        "valor_ventas": valor_ventas,
    }


# ---------------------------------------------------------------------------
# 9. ESTADO DE RESULTADOS SIMPLIFICADO (mensual)
# ---------------------------------------------------------------------------
def calcular_estado_resultados(negocio, costo_variable_unitario, gastos_fijos_mensuales, financiamiento):
    """
    Versión simplificada de un Estado de Resultados (P&G) mensual, calculada
    con los mismos datos que el usuario ya diligenció (no pide nada nuevo):

        Ventas totales            = precio actual x unidades vendidas al mes
      - Costo variable total      = costo variable unitario x unidades
      = Utilidad bruta
      - Gastos fijos              = costos indirectos asignados al mes
      = Utilidad operacional
      - Gasto financiero estimado = intereses del crédito repartidos en el plazo
      - Impuestos aproximados     = el valor que el usuario ingresó en Flujo de caja
      = Utilidad neta estimada

    No reemplaza un estado financiero certificado por un contador; es una
    lectura rápida para tomar decisiones.
    """
    precio_actual = _to_float(negocio.get("precio_actual"))
    unidades_mes = _to_float(negocio.get("unidades_mes"))

    ventas_totales = precio_actual * unidades_mes
    costo_variable_total = costo_variable_unitario * unidades_mes
    utilidad_bruta = ventas_totales - costo_variable_total
    utilidad_operacional = utilidad_bruta - gastos_fijos_mensuales

    plazo = financiamiento.get("plazo_meses", 0.0)
    gasto_financiero = (financiamiento.get("total_intereses", 0.0) / plazo) if plazo > 0 else 0.0
    impuestos = financiamiento.get("impuestos_mensuales", 0.0)

    utilidad_neta = utilidad_operacional - gasto_financiero - impuestos
    margen_bruto = (utilidad_bruta / ventas_totales * 100.0) if ventas_totales > 0 else 0.0
    margen_neto = (utilidad_neta / ventas_totales * 100.0) if ventas_totales > 0 else 0.0

    return {
        "ventas_totales": ventas_totales,
        "costo_variable_total": costo_variable_total,
        "utilidad_bruta": utilidad_bruta,
        "margen_bruto": margen_bruto,
        "gastos_fijos_mensuales": gastos_fijos_mensuales,
        "utilidad_operacional": utilidad_operacional,
        "gasto_financiero": gasto_financiero,
        "impuestos": impuestos,
        "utilidad_neta": utilidad_neta,
        "margen_neto": margen_neto,
    }


# ---------------------------------------------------------------------------
# 10. PROYECCIÓN DE FLUJO DE CAJA A 12 MESES
# ---------------------------------------------------------------------------
def calcular_proyeccion_flujo_caja(flujo, meses=12):
    """
    Repite el flujo neto mensual (igual que hace el Excel base) para ver
    cómo se acumula la caja durante el año. Si el usuario quiere modelar
    crecimiento mes a mes, puede repetir el diagnóstico con datos distintos;
    por ahora esta es una proyección plana, simple de leer en celular.
    """
    filas = []
    saldo = flujo["caja_inicial"]

    for mes in range(1, meses + 1):
        saldo += flujo["flujo_neto"]
        filas.append({
            "mes": mes,
            "flujo_neto": flujo["flujo_neto"],
            "saldo": saldo,
        })

    meses_negativos = sum(1 for fila in filas if fila["saldo"] < 0)

    return {
        "filas": filas,
        "saldo_mes_12": filas[-1]["saldo"],
        "meses_negativos": meses_negativos,
    }


# ---------------------------------------------------------------------------
# 11. RECOMENDACIONES AUTOMÁTICAS
# ---------------------------------------------------------------------------
def generar_recomendaciones(costos_precios, flujo_caja, financiamiento,
                             punto_equilibrio=None, proyeccion=None):
    """Devuelve una lista de recomendaciones de texto según el estado del negocio."""
    recomendaciones = []

    if costos_precios["precio_actual"] < costos_precios["costo_total_unitario"]:
        recomendaciones.append(
            "Sube tu precio o reduce costos: hoy cada venta puede estar dejando pérdida."
        )
    elif costos_precios["margen_actual"] < costos_precios["margen_deseado"]:
        recomendaciones.append(
            "Sube tu precio o reduce costos para alcanzar el margen deseado."
        )
    else:
        recomendaciones.append(
            "El precio actual cubre costos y permite margen, pero debes controlar gastos fijos."
        )

    total_costo = costos_precios["costo_total_unitario"]
    if total_costo > 0 and costos_precios["costo_mp_unitario"] / total_costo > 0.5:
        recomendaciones.append(
            "Revisa tus costos de materia prima, porque representan una parte alta del costo total."
        )

    if flujo_caja["saldo_final"] < 0:
        recomendaciones.append(
            "Tu negocio necesita mejorar caja antes de invertir o de asumir nuevas deudas."
        )

    if financiamiento["monto"] > 0:
        if financiamiento["utilidad_mensual"] < financiamiento["cuota_mensual"]:
            recomendaciones.append(
                "Evita asumir esta financiación: la cuota supera la utilidad mensual estimada."
            )
        elif financiamiento["cobertura"] < 1.5:
            recomendaciones.append(
                "Si tomas el crédito, negocia un plazo o monto que deje más margen de seguridad."
            )

    if punto_equilibrio is not None:
        if not punto_equilibrio["aplica"]:
            recomendaciones.append(
                "Con el precio actual nunca alcanzas el punto de equilibrio: "
                "primero sube el precio o baja el costo variable, y luego revisa cuánto necesitas vender."
            )
        elif costos_precios["unidades_mes"] < punto_equilibrio["unidades"]:
            recomendaciones.append(
                "Estás vendiendo por debajo de tu punto de equilibrio: te faltan unidades "
                "para cubrir los costos fijos del mes."
            )

    if proyeccion is not None and proyeccion["meses_negativos"] > 0:
        recomendaciones.append(
            "Tu proyección a 12 meses muestra caja negativa en algunos meses si nada cambia: "
            "planea cobros más rápidos o reduce gastos antes de que eso pase."
        )

    if not recomendaciones:
        recomendaciones.append("Tu negocio muestra indicadores saludables. Sigue revisando el Dashboard cada mes.")

    return recomendaciones
