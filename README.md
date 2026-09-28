# LATENTE Finanzas Web

MVP de una aplicación web (Python + Flask) que reemplaza el Excel de finanzas
del Laboratorio de Transformación Digital LATENTE. Está pensada para que un
emprendedor la use **desde el celular**, respondiendo un formulario guiado en
lenguaje simple, sin necesidad de manejar Excel ni contratar un consultor.

Al final, el emprendedor recibe un **Dashboard** con costos, precio sugerido,
flujo de caja, capacidad de endeudamiento y **recomendaciones automáticas**.

---

## 1. Requisitos

- Python 3.9 o superior instalado.
- No necesita internet para funcionar (corre 100% local).

## 2. Instalación y ejecución

Desde la carpeta `latente_finanzas_web/`, en Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

En macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Luego abre en el navegador (o en el celular conectado a la misma red, ver punto 6):

```
http://127.0.0.1:5000
```

Para detener el servidor, presiona `Ctrl + C` en la terminal.

## 3. Cómo funciona (explicación breve)

La app tiene 5 pasos guiados, más el Dashboard y las Recomendaciones:

1. **Diagnóstico financiero** — datos generales del negocio: nombre, producto,
   unidades vendidas al mes, precio actual y margen de utilidad deseado.
2. **Costos y precios** — el usuario agrega, con botones "+ Agregar",
   cuantas filas necesite de:
   - Materia prima (insumos)
   - Mano de obra (roles o personas)
   - Costos indirectos (gastos generales)
   - Costos operativos (costos por venta o entrega)
3. **Flujo de caja y presupuesto** — ingresos y egresos mensuales, caja inicial.
4. **Financiamiento** — simulación de un crédito (monto, tasa anual, plazo).
5. **Dashboard** — muestra todos los indicadores calculados automáticamente,
   con alertas de color (rojo = alerta, amarillo = precaución, verde = OK),
   además de:
   - **Punto de equilibrio**: unidades y ventas necesarias para no perder ni ganar.
   - **Estado de resultados simplificado (mensual)**: ventas, costo variable,
     utilidad bruta, gastos fijos, utilidad operacional, gasto financiero,
     impuestos y utilidad neta estimada.
   - **Proyección de caja a 12 meses**: repite el flujo neto mensual actual
     para ver cómo se acumula (o se agota) la caja durante el año.

   Todo esto se calcula con los mismos datos del formulario guiado; no se
   le pide nada nuevo al usuario. Al final hay un botón para **imprimir o
   guardar como PDF** desde el navegador (usa la función nativa de
   impresión de Chrome/Safari/Edge).
6. **Recomendaciones** — lista de acciones sugeridas según los resultados,
   más un checklist final.

Los datos se guardan en la **sesión del navegador** (cookie firmada de Flask)
mientras el usuario navega. No se usa base de datos ni login: al cerrar la
sesión o hacer clic en "Borrar todo y reiniciar", los datos desaparecen.
Esto es intencional para un MVP demostrable; si más adelante se necesita
persistencia entre visitas, se puede agregar SQLite sin cambiar la lógica
de `calculations.py`.

### Fórmulas replicadas del Excel base

| Cálculo | Fórmula |
|---|---|
| Costo de un insumo | `(costo de compra / cantidad que trae la compra) * cantidad usada por unidad` |
| Costo de mano de obra | `(pago mensual / horas disponibles al mes) * (minutos por unidad / 60)` |
| Costo indirecto unitario | `(valor mensual * % asignado) / unidades vendidas al mes` |
| Costo operativo unitario | `costo fijo por unidad + (% sobre venta * precio actual)` |
| Costo total unitario | `MP + MO + costos indirectos + costos operativos` |
| Precio sugerido | `costo total unitario / (1 - margen deseado)` |
| Margen actual | `(precio actual - costo total unitario) / precio actual` |
| Utilidad mensual | `(precio actual - costo total unitario) * unidades vendidas al mes` |
| Flujo neto | `total ingresos - total egresos` |
| Saldo final | `caja inicial + flujo neto` |
| Cuota del crédito | `monto * tasa mensual / (1 - (1 + tasa mensual) ^ -plazo)` |
| Cobertura de la cuota | `utilidad mensual / cuota mensual` |
| Margen de contribución | `precio actual - costo variable unitario (MP + MO + operativos)` |
| Punto de equilibrio (unidades) | `costos indirectos asignados al mes / margen de contribución` |
| Utilidad bruta (estado de resultados) | `ventas totales - costo variable total` |
| Utilidad operacional | `utilidad bruta - gastos fijos del mes` |
| Utilidad neta estimada | `utilidad operacional - gasto financiero estimado - impuestos` |
| Proyección de caja (mes N) | `saldo del mes N-1 + flujo neto mensual` (flujo neto constante, igual que el Excel base) |

> Nota: el simulador de financiamiento usa una cuota fija mensual (amortización
> simplificada con tasa nominal anual / 12). Es suficiente para un diagnóstico
> rápido; para negociar un crédito real, el emprendedor debe validar la cuota
> exacta con la entidad financiera.

### Reglas de alerta (iguales a las del Excel)

- Precio actual < costo total unitario → **Alerta: vendiendo por debajo del costo.**
- Margen actual < margen deseado → **Revisión necesaria.**
- Saldo de caja final < 0 → **Alerta: puede quedarse sin caja.**
- Utilidad mensual < cuota del crédito → **Alerta: la utilidad no cubre la cuota.**
- Cobertura de la cuota entre 1 y 1.5 → **Precaución: cuota ajustada.**
- Cobertura de la cuota > 1.5 → **OK: cuota sostenible.**

## 4. Datos de ejemplo para probar

En la pantalla de Inicio hay un botón **"Ver un ejemplo cargado"** que llena
automáticamente la app con el caso de una hamburguesería (el mismo ejemplo de
la guía en Excel), para que puedas navegar el Dashboard sin escribir nada:

- Negocio: Mi Negocio Latente — Hamburguesa clásica, 100 unidades/mes a $25.000,
  margen deseado 30%.
- Materia prima: pan, carne, queso.
- Mano de obra: cocinero y auxiliar.
- Costos indirectos: arriendo, servicios, internet, contabilidad.
- Costos operativos: empaque, servilletas, comisión de pasarela de pago (3%).
- Flujo de caja e ingresos/egresos mensuales de ejemplo.
- Crédito simulado de $5.000.000 al 25% anual a 24 meses.

También puedes usar el botón **"Borrar todo y reiniciar"** (en Inicio o en el
Dashboard) para limpiar la sesión y empezar con datos reales de tu propio
negocio.

## 5. Validaciones incluidas

- El Diagnóstico exige nombre del negocio, producto, unidades > 0, precio > 0
  y margen deseado entre 0% y 99%.
- Costos y precios exige al menos una fila de materia prima o de mano de obra
  para poder calcular un costo.
- Las filas vacías (sin ningún campo diligenciado) se descartan automáticamente
  al guardar, así el usuario no tiene que borrarlas a mano.
- Todos los campos numéricos se leen de forma segura: si el usuario deja algo
  vacío o escribe texto inválido, la app usa 0 en vez de romperse.
- Las divisiones por cero (por ejemplo, cantidad de compra en 0, horas al mes
  en 0, unidades vendidas en 0) siempre devuelven 0 en vez de un error.

## 6. Usarla desde el celular en la misma red Wi-Fi

Por defecto Flask solo escucha en el propio computador (`127.0.0.1`). Para
probarla desde un celular conectado a la misma red Wi-Fi:

1. Abre `app.py` y cambia la última línea por:
   ```python
   app.run(debug=True, host="0.0.0.0")
   ```
2. Busca la IP local de tu computador (en Windows: `ipconfig`, en macOS/Linux:
   `ifconfig` o `ip addr`), por ejemplo `192.168.1.15`.
3. Desde el celular, entra a `http://192.168.1.15:5000`.

## 7. Estructura del proyecto

```
latente_finanzas_web/
│
├── app.py                  # Rutas Flask, sesión y validaciones
├── calculations.py          # Toda la lógica financiera (funciones puras)
├── requirements.txt
├── README.md
│
├── static/
│   ├── css/styles.css       # Sistema de diseño (mobile-first)
│   └── js/app.js            # Filas dinámicas + botón imprimir
│
└── templates/
    ├── base.html             # Barra superior + navegación inferior móvil
    ├── index.html            # Inicio
    ├── diagnostico.html       # Paso 1: datos del negocio
    ├── costos.html            # Paso 2: materia prima, MO, indirectos, operativos
    ├── flujo_caja.html        # Paso 3: ingresos y egresos
    ├── financiamiento.html    # Paso 4: simulador de crédito
    ├── dashboard.html         # Resultado final con alertas
    └── recomendaciones.html   # Acciones sugeridas + checklist
```

## 8. Próximos pasos sugeridos (fuera del alcance de este MVP)

- **Balance general** (activos, pasivos, patrimonio): a propósito no se incluyó
  en esta versión, porque pediría datos que el emprendedor típicamente no
  tiene a la mano (inventario valorizado, deudas totales, activos fijos) y
  el objetivo del MVP es que nadie necesite un consultor para diligenciarlo.
  Si el laboratorio decide que sí se necesita, se puede agregar como una
  pantalla adicional sin tocar la lógica actual.
- Guardar historial mensual en SQLite para comparar mes a mes (como la hoja
  "Presupuesto" del Excel original) y poder ver la proyección de 12 meses
  con datos reales en vez de repetir el mismo mes.
- Permitir varios productos/servicios por negocio (el Excel base sí lo soporta;
  este MVP se enfoca en un producto principal para simplificar el celular).
- Exportar el Dashboard como PDF generado en el servidor (hoy se usa la
  impresión nativa del navegador, que ya permite "Guardar como PDF").


## Indicadores SENA / Fondo Emprender

La app incluye una sección `/indicadores-sena` para organizar indicadores financieros orientativos útiles para la preparación de planes de negocio:

- Ventas mensuales proyectadas.
- Costos y gastos.
- Utilidad mensual estimada.
- Margen actual.
- Flujo de caja.
- Saldo final de caja.
- Punto de equilibrio.
- Inversión o crédito solicitado.
- Cobertura de cuota.
- Roles o empleos directos registrados.

Esta sección no reemplaza los formatos oficiales del SENA, pero ayuda al emprendedor a preparar información financiera clave.
