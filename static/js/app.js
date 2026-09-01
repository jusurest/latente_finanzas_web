/**
 * app.js
 * ------
 * JavaScript básico (sin frameworks) para:
 *  1) Agregar/quitar filas dinámicas en los formularios de costos
 *     (materia prima, mano de obra, costos indirectos, costos operativos).
 *  2) Disparar la impresión / guardado como PDF desde el navegador.
 *
 * Cada bloque repetible se define en el HTML con una plantilla <template>
 * y un contenedor con data-repetible="<nombre>". Este script clona la
 * plantilla y le agrega un botón para quitar la fila.
 */

document.addEventListener("DOMContentLoaded", function () {
  inicializarBloquesRepetibles();
  inicializarBotonesImprimir();
});

function inicializarBloquesRepetibles() {
  document.querySelectorAll("[data-agregar]").forEach(function (boton) {
    var nombre = boton.getAttribute("data-agregar");
    boton.addEventListener("click", function () {
      agregarFila(nombre);
    });
  });

  // Delegación de eventos para los botones "Quitar" (las filas se crean dinámicamente)
  document.addEventListener("click", function (evento) {
    var boton = evento.target.closest(".btn-quitar");
    if (!boton) return;
    var fila = boton.closest(".bloque-repetible");
    var contenedor = fila ? fila.parentElement : null;
    if (fila && contenedor) {
      // Nunca dejar el formulario en cero filas: si es la última, solo se limpia.
      var filas = contenedor.querySelectorAll(".bloque-repetible");
      if (filas.length > 1) {
        fila.remove();
        renumerarFilas(contenedor);
      } else {
        limpiarFila(fila);
      }
    }
  });
}

function agregarFila(nombre) {
  var plantilla = document.querySelector('template[data-plantilla="' + nombre + '"]');
  var contenedor = document.querySelector('[data-repetible="' + nombre + '"]');
  if (!plantilla || !contenedor) return;

  var fragmento = plantilla.content.cloneNode(true);
  contenedor.appendChild(fragmento);
  renumerarFilas(contenedor);
}

function renumerarFilas(contenedor) {
  var filas = contenedor.querySelectorAll(".bloque-repetible");
  filas.forEach(function (fila, indice) {
    var titulo = fila.querySelector(".fila-titulo span");
    if (titulo) {
      titulo.textContent = titulo.textContent.replace(/#\d+/, "#" + (indice + 1));
    }
  });
}

function limpiarFila(fila) {
  fila.querySelectorAll("input").forEach(function (input) {
    input.value = "";
  });
}

function inicializarBotonesImprimir() {
  document.querySelectorAll("[data-imprimir]").forEach(function (boton) {
    boton.addEventListener("click", function () {
      window.print();
    });
  });
}
