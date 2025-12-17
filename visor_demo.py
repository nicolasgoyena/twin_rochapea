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
RANGO_INDICE_VULNERABILIDAD = (0.0, 100.0)
RANGO_REDICCION_VULNERABILIDAD = (0.0, 60.0)

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
            ["Índice de Vulnerabilidad"]
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
    if variable in ["Índice de Vulnerabilidad", "Reducción del índice de Vulnerabilidad"]:
        estacion = st.sidebar.selectbox(
            "Estación",
            ["Invierno", "Primavera", "Verano", "Otoño"]
        )

    st.sidebar.caption("Escala fija común para todas las estaciones y escenarios")

    # =========================
    # SELECCIÓN DE COLUMNA
    # =========================
    if escenario == "Actual":
        col = f"Índice de Vulnerabilidad en {estacion} en el escenario Actual (0-100)"

    elif variable == "Reducción del índice de contaminación (ICC)":
        col = (
            "ESCENARIO 1: Porcentaje de reducción del índice de contaminación (ICC) en escenario Ideal (0-100)"
            if escenario == "Ideal"
            else
            "ESCENARIO 2: Porcentaje de reducción del índice de contaminación (ICC) en escenario Prioritario (0-100)"
        )

    elif variable == "Reducción del índice de Vulnerabilidad":
        mapa = {
            "Invierno": ("3", "4"),
            "Primavera": ("5", "6"),
            "Verano": ("7", "8"),
            "Otoño": ("9", "10")
        }
        num = mapa[estacion][0] if escenario == "Ideal" else mapa[estacion][1]
        col = f"ESCENARIO {num}: Porcentaje de reducción del índice de Vulnerabilidad en {estacion} en el escenario {escenario} (0-100)"

    else:  # Índice de Vulnerabilidad Ideal / Prioritario
        col = f"Índice de Vulnerabilidad en {estacion} en el escenario {escenario} (0-100)"

    # =========================
    # RANGO FIJO
    # =========================
    if variable == "Reducción del índice de contaminación (ICC)":
        vmin, vmax = RANGO_REDICCION_CONTAMINACION
    elif variable == "Reducción del índice de Vulnerabilidad":
        vmin, vmax = RANGO_REDICCION_VULNERABILIDAD
    else:
        vmin, vmax = RANGO_INDICE_VULNERABILIDAD


    # =========================
    # COLORMAP
    # =========================
    if variable == "Índice de Vulnerabilidad":
        colormap = cm.LinearColormap(cm.linear.Reds_09.colors, vmin=vmin, vmax=vmax)
    elif variable == "Reducción del índice de Vulnerabilidad":
        colormap = cm.LinearColormap(cm.linear.Oranges_09.colors, vmin=vmin, vmax=vmax)
    else:
        colormap = cm.LinearColormap(cm.linear.Greens_09.colors, vmin=vmin, vmax=vmax)

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

    # Vegetación
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

    colormap.caption = col
    colormap.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

# =========================
# MOSTRAR MAPA
# =========================
st_folium(m, width=1200, height=650, returned_objects=[])

