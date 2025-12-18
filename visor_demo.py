# -*- coding: utf-8 -*-
"""
Visor Rochapea – Escenarios, Demografía y Catastro
"""

import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import branca.colormap as cm

# =========================
# CONFIG
# =========================
GPKG_PATH = "parcelas_rochapea_completas.gpkg"
LAYER_NAME = "parcelas_rochapea"

ZONAS_VERDES_PATH = "simulacion_zonas_verdes_rochapea_RECUPERADA.shp"
ARBOLES_PATH = "arboles_propuestos.shp"

MAP_CRS = 4326

# Rangos fijos
RANGO_REDICCION_CONTAMINACION = (0.0, 20.0)
RANGO_REDICCION_VULNERABILIDAD = (0.0, 25.0)
RANGO_INDICE_VULNERABILIDAD = (0.0, 100.0)

# =========================
# TEXTOS EXPLICATIVOS
# =========================

TEXTO_VULNERABILIDAD = """
**Índice de Vulnerabilidad**

El índice mide la vulnerabilidad relativa a nivel de parcela, integrando factores como la contaminación atmosférica
(NO₂, PM₂.₅, PM₁₀), la presencia de vegetación (zonas verdes de gran densidad o parques),
las características demográficas asociadas a cada tipo de edificio y la cantidad de población expuesta.

Las variables se normalizan y transforman para reflejar relaciones no lineales y se combinan de forma ponderada.
El índice se expresa en una escala de 0 a 1 (re-escalada a 0–100 en el visor), donde valores más altos indican
mayor vulnerabilidad.

Este índice sirve para comparar parcelas dentro del barrio de la Rochapea y evaluar el impacto de estrategias
de mitigación, como el aumento de vegetación, en los distintos escenarios (actual, ideal y prioritario)
y a lo largo de las estaciones del año.
"""

TEXTO_ICC = """
**Índice de Contaminación Combinado (ICC)**

Los mapas de contaminación se han generado combinando información procedente de sensores,
modelos CFD y estaciones de calidad del aire.

Se consideran los contaminantes NO₂, PM₂.₅ y PM₁₀, que se integran mediante el
Índice de Contaminación Combinado (ICC), definido como:

ICC(e, v) = 0.5 · PM₂.₅(e, v) + 0.3 · NO₂(e, v) + 0.2 · PM₁₀(e, v)

donde *e* representa la estación del año y *v* la parcela.
Valores más altos indican una mayor carga contaminante.
"""

TEXTO_REDICCION = """
**Reducción del indicador**

Las variables de reducción representan el cambio porcentual respecto al escenario actual,
como consecuencia de la incorporación de nuevas zonas verdes y arbolado.

Valores más altos indican una mayor mejora ambiental asociada a la estrategia de vegetación
implementada en cada escenario.
"""


# =========================
# MAPEO DE COLUMNAS – REDUCCIÓN ÍNDICE DE VULNERABILIDAD
# =========================

REDUCCION_VULNERABILIDAD_COLS = {
    "Ideal": {
        "Invierno": "ESCENARIO 3: Porcentaje de reducción del índice de Vulnerabilidad en Invierno con Vegetación Ideal respecto a la Vegetación Actual",
        "Primavera": "ESCENARIO 5: Porcentaje de reducción del índice de Vulnerabilidad en Primavera con Vegetación Ideal respecto a la Vegetación Actual",
        "Verano": "ESCENARIO 7: Porcentaje de reducción del índice de Vulnerabilidad en Verano con Vegetación Ideal respecto a la Vegetación Actual",
        "Otoño": "ESCENARIO 9: Porcentaje de reducción del índice de Vulnerabilidad en Otoño con Vegetación Ideal respecto a la Vegetación Actual",
    },
    "Prioritario": {
        "Invierno": "ESCENARIO 4: Porcentaje de reducción del índice de Vulnerabilidad en Invierno con Vegetación Prioritaria respecto a la Vegetación Actual",
        "Primavera": "ESCENARIO 6: Porcentaje de reducción del índice de Vulnerabilidad en Primavera con Vegetación Prioritaria respecto a la Vegetación Actual",
        "Verano": "ESCENARIO 8: Porcentaje de reducción del índice de Vulnerabilidad en Verano con Vegetación Prioritaria respecto a la Vegetación Actual",
        "Otoño": "ESCENARIO 10: Porcentaje de reducción del índice de Vulnerabilidad en Otoño con Vegetación Prioritaria respecto a la Vegetación Actual",
    }
}
# =========================
# MAPEO ICC – ESCENARIO ACTUAL
# =========================
ICC_ACTUAL_COLS = {
    "Invierno": "ICC en Invierno (0-100)",
    "Primavera": "ICC en Primavera (0-100)",
    "Verano": "ICC en Verano (0-100)",
    "Otoño": "ICC en Otoño (0-100)",
    "Media anual": "ICC Media Anual (0-100)"
}


st.set_page_config(layout="wide")
st.title("Visor urbano – Rochapea")

# =========================
# CARGA DE DATOS
# =========================
@st.cache_data
def load_data():
    return gpd.read_file(GPKG_PATH, layer=LAYER_NAME).to_crs(epsg=MAP_CRS)

@st.cache_data
def load_vegetation():
    zonas = gpd.read_file(ZONAS_VERDES_PATH).to_crs(epsg=MAP_CRS)
    arboles = gpd.read_file(ARBOLES_PATH).to_crs(epsg=MAP_CRS)
    return zonas, arboles

gdf = load_data()
zonas_verdes, arboles = load_vegetation()

# =========================
# SIDEBAR – MODO PRINCIPAL
# =========================
st.sidebar.header("MODO DEL VISOR")

modo = st.sidebar.radio(
    "Selecciona modo",
    ["Simulación de escenarios", "Demografía y Catastro"]
)

# ============================================================
# =================== MODO 1: ESCENARIOS =====================
# ============================================================
if modo == "Simulación de escenarios":

    st.sidebar.header("SIMULACIÓN DE ESCENARIOS")

    escenario = st.sidebar.selectbox(
        "Escenario",
        ["Actual", "Ideal", "Prioritario"]
    )

    if escenario == "Actual":
        variable = st.sidebar.selectbox(
            "Variable",
            [
                "Índice de Vulnerabilidad",
                "Índice de contaminación (ICC)"
            ]
        )

    else:
        variable = st.sidebar.selectbox(
            "Variable",
            [
                "Reducción del índice de contaminación (ICC)",
                "Reducción del índice de Vulnerabilidad",
                "Índice de Vulnerabilidad"
            ]
        )

    estacion = None
    # =========================
    # SELECTOR DE ESTACIÓN
    # =========================
    if variable in [
        "Índice de Vulnerabilidad",
        "Reducción del índice de Vulnerabilidad"
    ]:
        # Vulnerabilidad → SIN media anual
        estacion = st.sidebar.selectbox(
            "Estación",
            ["Invierno", "Primavera", "Verano", "Otoño"]
        )
    
    elif variable == "Índice de contaminación (ICC)":
        # ICC → CON media anual
        estacion = st.sidebar.selectbox(
            "Estación",
            ["Invierno", "Primavera", "Verano", "Otoño", "Media anual"]
        )



    # 👉 NUEVO: ajuste manual opcional
    ajustar_rango = st.sidebar.checkbox(
        "Ajustar escala manualmente",
        value=False
    )

    # =========================
    # SELECCIÓN DE COLUMNA
    # =========================
    if escenario == "Actual" and variable == "Índice de contaminación (ICC)":
        col = ICC_ACTUAL_COLS[estacion]

    elif escenario == "Actual":
        col = f"Índice de Vulnerabilidad en {estacion} en el escenario Actual (0-100)"

    elif variable == "Reducción del índice de contaminación (ICC)":
        col = (
            "ESCENARIO 1: Porcentaje de reducción del índice de contaminación (ICC) en escenario Ideal (0-100)"
            if escenario == "Ideal"
            else
            "ESCENARIO 2: Porcentaje de reducción del índice de contaminación (ICC) en escenario Prioritario (0-100)"
        )

    elif variable == "Reducción del índice de Vulnerabilidad":
        col = REDUCCION_VULNERABILIDAD_COLS[escenario][estacion]


    else:
        col = f"Índice de Vulnerabilidad en {estacion} en el escenario {escenario} (0-100)"

    # =========================
    # RANGO BASE (FIJO)
    # =========================
    if escenario == "Actual" and variable == "Índice de contaminación (ICC)":
        # ICC actual → escala fija 0–60
        vmin, vmax = 0.0, 50.0
    
    elif variable == "Reducción del índice de contaminación (ICC)":
        vmin, vmax = RANGO_REDICCION_CONTAMINACION
    
    elif variable == "Reducción del índice de Vulnerabilidad":
        vmin, vmax = RANGO_REDICCION_VULNERABILIDAD
    
    else:
        # Índice de Vulnerabilidad (Actual / Ideal / Prioritario)
        vmin, vmax = RANGO_INDICE_VULNERABILIDAD
    

    # =========================
    # AJUSTE MANUAL OPCIONAL
    # =========================
    if ajustar_rango:
        st.sidebar.markdown("**Escala manual**")

        vmin = st.sidebar.number_input(
            "Valor mínimo",
            min_value=0.0,
            max_value=100.0,
            value=vmin,
            step=1.0
        )

        vmax = st.sidebar.number_input(
            "Valor máximo",
            min_value=0.0,
            max_value=100.0,
            value=vmax,
            step=1.0
        )

        if vmin >= vmax:
            st.sidebar.error("El valor mínimo debe ser menor que el máximo")
            st.stop()

    # =========================
    # COLORMAP
    # =========================
    if escenario == "Actual" and variable == "Índice de contaminación (ICC)":
        # ICC actual → contaminación (más = peor)
        colormap = cm.LinearColormap(
            cm.linear.Reds_09.colors,
            vmin=vmin,
            vmax=vmax
        )
    
    elif variable == "Índice de Vulnerabilidad":
        # Vulnerabilidad (más = peor)
        colormap = cm.LinearColormap(
            cm.linear.Reds_09.colors,
            vmin=vmin,
            vmax=vmax
        )
    
    elif variable == "Reducción del índice de Vulnerabilidad":
        # Reducción (más = mejor)
        colormap = cm.LinearColormap(
            cm.linear.Greens_09.colors,
            vmin=vmin,
            vmax=vmax
        )
    
    else:
        # Reducción del ICC (más = mejor)
        colormap = cm.LinearColormap(
            cm.linear.Greens_09.colors,
            vmin=vmin,
            vmax=vmax
        )

    

    # =========================
    # MAPA
    # =========================
    center = gdf.geometry.centroid
    m = folium.Map(
        location=[center.y.mean(), center.x.mean()],
        zoom_start=16,
        tiles=None
    )

    folium.TileLayer(
        tiles="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII=",
        attr=" ",
        name="Sin mapa base",
        overlay=False
    ).add_to(m)

    folium.TileLayer("cartodbpositron", name="CartoDB Positron").add_to(m)

    def style_function(feature):
        val = feature["properties"].get(col)
        if val is None or val < vmin or val > vmax:
            return {"fillOpacity": 0, "weight": 0}
        return {
            "fill": True,
            "fillColor": colormap(val),
            "color": "#333333",
            "weight": 0.3,
            "fillOpacity": 0.8,
        }

    folium.GeoJson(
        gdf,
        name="Parcelas",
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(fields=[col], localize=True)
    ).add_to(m)

    # =========================
    # VEGETACIÓN
    # =========================
    if escenario == "Ideal":
        zonas_plot, arboles_plot = zonas_verdes, arboles
    elif escenario == "Prioritario":
        zonas_plot = zonas_verdes[zonas_verdes["Prioridad"] == "1"]
        arboles_plot = arboles[arboles["Prioridad"] == "1"]
    else:
        zonas_plot = arboles_plot = None

    if zonas_plot is not None and not zonas_plot.empty:
        folium.GeoJson(
            zonas_plot,
            name="Nuevas zonas verdes",
            style_function=lambda x: {
                "fill": True,
                "fillColor": "#2ecc71",
                "color": "#1e8449",
                "weight": 1,
                "fillOpacity": 0.5
            }
        ).add_to(m)

    if arboles_plot is not None and not arboles_plot.empty:
        fg = folium.FeatureGroup(name="Árboles propuestos")
        for _, r in arboles_plot.iterrows():
            fg.add_child(
                folium.CircleMarker(
                    location=[r.geometry.y, r.geometry.x],
                    radius=3,
                    color="#145a32",
                    fill=True,
                    fill_color="#27ae60",
                    fill_opacity=0.9
                )
            )
        fg.add_to(m)
    colormap.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

# =========================
# MOSTRAR TÍTULO + MAPA
# =========================
st.markdown(f"### {col}")

if variable == "Índice de Vulnerabilidad":
    st.info(TEXTO_VULNERABILIDAD)

elif variable == "Índice de contaminación (ICC)":
    st.info(TEXTO_ICC)

elif "Reducción" in variable:
    st.info(TEXTO_REDICCION)

st_folium(
    m,
    width=1200,
    height=650,
    returned_objects=[]
)










