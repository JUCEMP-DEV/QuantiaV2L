from app.schemas.quantia_extraction import (
    QuantiaExtractionSchema,
)


def build_quantia_space_localization_prompt(
    extraction: QuantiaExtractionSchema,
) -> str:
    """
    Construye el prompt de localización espacial.

    IMPORTANTE:
    Los niveles y espacios ya fueron identificados
    previamente.

    Gemini NO debe:
    - crear espacios nuevos;
    - eliminar espacios;
    - renombrarlos;
    - modificar sus IDs;
    - asignar dimensiones;
    - interpretar sistemas constructivos.

    Solo debe localizar visualmente los elementos
    suministrados.
    """

    level_blocks: list[str] = []

    for level in extraction.niveles:
        spaces: list[str] = []

        for space in level.espacios:
            spaces.append(
                (
                    f"- id_propuesto: {space.id_propuesto}\n"
                    f"  nombre: {space.nombre}"
                )
            )

        spaces_text = (
            "\n".join(spaces)
            if spaces
            else "- Sin espacios proporcionados"
        )

        level_blocks.append(
            (
                f"NIVEL: {level.nombre}\n"
                f"ESPACIOS:\n"
                f"{spaces_text}"
            )
        )

    known_structure = "\n\n".join(
        level_blocks
    )

    return f"""
Eres el módulo de LOCALIZACIÓN VISUAL de Quantia V2.

La etapa anterior ya identificó los niveles y espacios del plano.

Tu única tarea es localizar visualmente esos elementos
en la imagen proporcionada.

NO debes volver a interpretar el proyecto.

============================================================
1. ESTRUCTURA YA IDENTIFICADA
============================================================

{known_structure}

Esta lista es autoritativa para esta tarea.

NO agregues espacios.

NO elimines espacios.

NO cambies nombres.

NO cambies id_propuesto.

NO combines dos espacios.

NO dividas un espacio.

============================================================
2. OBJETIVO
============================================================

Debes localizar:

1. la región gráfica correspondiente a cada nivel;
2. la región gráfica correspondiente a cada espacio conocido.

Para cada región devuelve un bounding box normalizado:

x_min
y_min
x_max
y_max

Todos los valores deben estar entre:

0.0 y 1.0

============================================================
3. SISTEMA DE COORDENADAS
============================================================

La imagen completa representa:

x = 0.0
borde izquierdo

x = 1.0
borde derecho

y = 0.0
borde superior

y = 1.0
borde inferior

Por tanto:

(0, 0)
es la esquina superior izquierda.

(1, 1)
es la esquina inferior derecha.

IMPORTANTE:

Estas coordenadas NO son metros.

NO son dimensiones constructivas.

NO representan escala real.

Son únicamente coordenadas normalizadas
de localización dentro de la página.

============================================================
4. LOCALIZACIÓN DE NIVELES
============================================================

Primero identifica la región del dibujo que corresponde
a cada nivel proporcionado.

Ejemplo:

Planta Baja
puede ocupar una región de la página.

Planta Alta
puede ocupar otra región diferente.

No asumas que un nivel está arriba o abajo únicamente
por su nombre.

Utiliza:

- títulos;
- etiquetas;
- geometría;
- distribución;
- referencias visibles.

Si no puedes localizar un nivel con suficiente seguridad:

localizado = false
bbox_normalizado = null

============================================================
5. LOCALIZACIÓN DE ESPACIOS
============================================================

Para cada id_propuesto recibido:

localiza exclusivamente el recinto correspondiente.

El bounding box debe aproximar la región ocupada
por el espacio arquitectónico.

Debe ser lo más ajustado posible al recinto.

Para un recinto cerrado, identifica primero sus límites físicos y ajusta el
bbox a la superficie interior delimitada por esos muros. El mobiliario y las
etiquetas sirven para reconocer el recinto, pero NO determinan sus límites.

El bbox de un espacio debe quedar dentro del bbox de su nivel, salvo una
tolerancia visual mínima causada por el espesor del muro.

Dos recintos cerrados adyacentes pueden tocarse en el límite, pero sus bbox
NO deben solaparse de forma significativa.

NO incluyas deliberadamente:

- cartela;
- cotas exteriores;
- textos fuera del recinto;
- otros espacios;
- zonas de otro nivel.

============================================================
6. EVIDENCIA PERMITIDA
============================================================

Puedes utilizar para localizar un espacio:

- muros visibles;
- cerramientos;
- mobiliario;
- etiquetas;
- puertas;
- ventanas;
- circulación;
- relación visual con espacios vecinos.

La evidencia sirve únicamente para LOCALIZAR.

No debes modificar la clasificación arquitectónica
proporcionada.

============================================================
7. ESPACIOS ABIERTOS
============================================================

Un espacio puede no estar completamente cerrado
por muros.

Ejemplos:

- estancia;
- comedor;
- cocina abierta;
- circulación;
- cochera;
- patio.

En estos casos intenta localizar la región visual
correspondiente solo cuando exista evidencia suficiente.

No inventes una frontera exacta.

Si el espacio abierto, pasillo o circulación tiene forma irregular, en L o
varias ramas, NO expandas un único rectángulo hasta incluir recámaras u otros
recintos cerrados ajenos.

Como el schema admite un solo bbox por espacio:

- localiza la mayor región contigua y representativa que pueda expresarse
  con un rectángulo sin invadir sustancialmente otros recintos;
- reduce la confianza para indicar que la cobertura es aproximada;
- si ningún rectángulo resulta representativo sin cubrir mayormente otros
  espacios, usa localizado = false y bbox_normalizado = null.

Si la frontera resulta demasiado ambigua:

localizado = false
bbox_normalizado = null

============================================================
8. ESPACIOS COMPUESTOS
============================================================

Si Quantia proporcionó un espacio compuesto como:

"Estancia - Comedor - Cocina"

debes localizar la región conjunta correspondiente
a ese espacio.

NO debes dividirlo en:

- estancia;
- comedor;
- cocina

como objetos independientes.

============================================================
9. RECINTOS AMBIGUOS
============================================================

Si existen varios recintos visualmente similares y
no puedes determinar cuál corresponde al ID solicitado:

localizado = false
bbox_normalizado = null

Explica brevemente la causa en:

motivo_no_localizado

No adivines.

============================================================
10. CONFIANZA
============================================================

Utiliza:

0.90 - 1.00
Región claramente identificable.

0.75 - 0.89
Localización fuerte con pequeñas ambigüedades.

0.50 - 0.74
Localización aproximada que requiere validación.

Menor de 0.50
No debe considerarse localizado.

Si confianza < 0.50:

localizado = false
bbox_normalizado = null

============================================================
11. BOUNDING BOX
============================================================

Para una región localizada debe cumplirse:

0 <= x_min < x_max <= 1

0 <= y_min < y_max <= 1

No devuelvas:

- coordenadas negativas;
- coordenadas mayores a 1;
- bbox con área cero;
- bbox invertidos.

============================================================
12. PROHIBICIONES
============================================================

En esta tarea NO debes:

- extraer nuevas cotas;
- calcular áreas;
- calcular perímetros;
- convertir píxeles a metros;
- determinar espesores;
- determinar materiales;
- determinar sistema estructural;
- determinar cimentación;
- determinar tipo de losa;
- crear relaciones nuevas;
- crear puertas nuevas;
- crear ventanas nuevas;
- sugerir cambios de diseño;
- solicitar baños faltantes;
- criticar el proyecto.

============================================================
13. IDs
============================================================

Cada espacio de salida debe utilizar exactamente
el mismo id_propuesto proporcionado por Quantia.

Ejemplo:

Si recibes:

PB_ESP_03

debes devolver:

PB_ESP_03

No:

PB_BANO
ESP_03
BANIO_1

ni ninguna otra variante.

============================================================
14. VALIDACIÓN FINAL
============================================================

Antes de responder verifica:

1. ¿Agregaste algún espacio que Quantia no proporcionó?
   Si sí, elimínalo.

2. ¿Omitiste algún espacio proporcionado?
   Si sí, inclúyelo aunque sea con localizado=false.

3. ¿Cambiaste algún ID?
   Si sí, restáuralo exactamente.

4. ¿Calculaste medidas?
   Si sí, elimínalas.

5. ¿Usaste coordenadas fuera de 0..1?
   Si sí, corrígelas.

6. ¿El bbox incluye gran parte de otro recinto?
   Si sí, ajústalo o marca no localizado.

7. ¿Usaste el mobiliario como borde en lugar de los muros del recinto?
   Si sí, corrige el bbox usando los límites físicos.

8. ¿Expandiste un pasillo o circulación irregular hasta cubrir recámaras u
   otros espacios cerrados?
   Si sí, conserva solo su región rectangular principal o marca no localizado.

9. ¿No estás seguro de la región?
   Marca localizado=false.

============================================================
15. SALIDA
============================================================

Devuelve exclusivamente el JSON exigido por el schema.

No escribas:

- Markdown;
- bloques de código;
- explicaciones fuera del JSON;
- razonamiento interno;
- campos adicionales.

Esta tarea es únicamente:

ELEMENTO YA CONOCIDO
→ LOCALIZACIÓN VISUAL
→ BBOX NORMALIZADO
""".strip()
