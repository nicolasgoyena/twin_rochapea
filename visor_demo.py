# -*- coding: utf-8 -*-
"""
Visor Rochapea – Escenarios, Demografía y Catastro
"""

import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import branca.colormap as cm
import numpy as np

# =========================
# CONFIG
# =========================
GPKG_PATH = "parcelas_rochapea_completas.gpkg"
LAYER_NAME = "parcelas_rochapea"

ZONAS_VERDES_PATH = "simulacion_zonas_verdes_rochapea_RECUPERADA.shp"
ARBOLES_PATH = "arboles_propuestos.shp"

MAP_CRS = 4326

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
    if variable == "Índice de Vulnerabilidad":
        estacion = st.sidebar.selectbox(
            "Estación",
            ["Invierno", "Primavera", "Verano", "Otoño"]
        )
    elif variable == "Reducción del índice de Vulnerabilidad":
        estacion = st.sidebar.selectbox(
            "Estación",
            ["Invierno", "Primavera", "Verano", "Otoño"]
        )



    range_mode = st.sidebar.radio("Rango", ["Automático", "Manual"])

    # =========================
    # SELECCIÓN DE COLUMNA
    # =========================
    if escenario == "Actual" and variable == "Índice de Vulnerabilidad":

        col = f"Índice de Vulnerabilidad en {estacion} en el escenario Actual (0-100)"

    elif variable == "Reducción del índice de contaminación (ICC)":
    
        col = (
            "ESCENARIO 1: Porcentaje de reducción del índice de contaminación (ICC) en escenario Ideal (0-100)"
            if escenario == "Ideal"
            else
            "ESCENARIO 2: Porcentaje de reducción del índice de contaminación (ICC) en escenario Prioritario (0-100)"
        )
    
    elif variable == "Reducción del índice de Vulnerabilidad":
    
        if escenario == "Ideal":
            col = f"ESCENARIO 3: Porcentaje de reducción del índice de Vulnerabilidad en {estacion} en el escenario Ideal (0-100)"
            col = col.replace(
                "3",
                {"Invierno": "3", "Primavera": "5", "Verano": "7", "Otoño": "9"}[estacion]
            )
        else:
            col = f"ESCENARIO 4: Porcentaje de reducción del índice de Vulnerabilidad en {estacion} en el escenario Prioritario (0-100)"
            col = col.replace(
                "4",
                {"Invierno": "4", "Primavera": "6", "Verano": "8", "Otoño": "10"}[estacion]
            )
    
    elif variable == "Índice de Vulnerabilidad":
    
        if escenario == "Ideal":
            col = f"Índice de Vulnerabilidad en {estacion} en el escenario Ideal (0-100)"
        else:
            col = f"Índice de Vulnerabilidad en {estacion} en el escenario Prioritario (0-100)"


    values = gdf[col].dropna()

    if range_mode == "Automático":
        vmin, vmax = float(values.min()), float(values.max())
    else:
        st.sidebar.markdown("**Rango manual (0–100)**")
        vmin = st.sidebar.number_input("Valor mínimo", 0.0, 100.0, 0.0, step=1.0)
        vmax = st.sidebar.number_input("Valor máximo", 0.0, 100.0, 100.0, step=1.0)

    if variable == "Índice de Vulnerabilidad":
        colormap = cm.LinearColormap(
            cm.linear.Reds_09.colors,
            vmin=vmin,
            vmax=vmax
        )
    elif variable == "Reducción del índice de Vulnerabilidad":
        colormap = cm.LinearColormap(
            cm.linear.Oranges_09.colors,
            vmin=vmin,
            vmax=vmax
        )
    else:  # Reducción del índice de contaminación (ICC)
        colormap = cm.LinearColormap(
            cm.linear.Greens_09.colors,
            vmin=vmin,
            vmax=vmax
        )
    

    # ===== MAPA =====
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
        overlay=False,
        control=True
    ).add_to(m)




    # Mapas base
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

    # Parcelas
    folium.GeoJson(
        gdf,
        name="Parcelas (escenario)",
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
        zonas_plot, arboles_plot = None, None


    # =========================
    # CAPAS DE VEGETACIÓN (solo si existen)
    # =========================
    
    if zonas_plot is not None and not zonas_plot.empty:
        folium.GeoJson(
            zonas_plot,
            name="Nuevas zonas verdes",
            overlay=True,
            control=True,
            style_function=lambda x: {
                "fill": True,
                "fillColor": "#2ecc71",
                "color": "#1e8449",
                "weight": 1,
                "fillOpacity": 0.5
            }
        ).add_to(m)
    
    if arboles_plot is not None and not arboles_plot.empty:
        arboles_fg = folium.FeatureGroup(
            name="Árboles propuestos",
            overlay=True,
            control=True
        )
    
        for _, r in arboles_plot.iterrows():
            arboles_fg.add_child(
                folium.CircleMarker(
                    location=[r.geometry.y, r.geometry.x],
                    radius=3,
                    color="#145a32",
                    fill=True,
                    fill_color="#27ae60",
                    fill_opacity=0.9
                )
            )
    
        arboles_fg.add_to(m)


    colormap.caption = col
    colormap.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

# ============================================================
# ============ MODO 2: DEMOGRAFÍA Y CATASTRO =================
# ============================================================
else:

    st.sidebar.header("DEMOGRAFÍA Y CATASTRO")

    demog_vars = {
        "Número de viviendas": "NViviendas",
        "Población masculina": "Hombres_es",
        "Población femenina": "Mujeres_es",
        "Hombres de 0 a 17 años": "H_0_17_est",
        "Mujeres de 0 a 17 años": "M_0_17_est",
        "Hombres de 18 a 64 años": "H_18_64_es",
        "Mujeres de 18 a 64 años": "M_18_64_es",
        "Hombres de 65 años o más": "H_65p_esti",
        "Mujeres de 65 años o más": "M_65p_esti",
        "Población total": "Poblacion_",
        "Afluencia estimada de personas": "Afluencia",
        "Tipología del edificio (uso)": "USO"
    }

    demog_vars = {k: v for k, v in demog_vars.items() if v in gdf.columns}

    var_label = st.sidebar.selectbox("Variable demográfica / catastral", list(demog_vars.keys()))
    col = demog_vars[var_label]

    if col == "USO":
        m = gdf.explore(
            column="USO",
            categorical=True,
            cmap="Set3",
            tooltip=["USO"],
            tiles="openstreetmap",
            legend=True
        )
    else:
        values = gdf[col].dropna()
        range_mode = st.sidebar.radio("Rango", ["Automático", "Manual"])

        if range_mode == "Automático":
            vmin, vmax = float(values.min()), float(values.max())
        else:
            vmin = st.sidebar.number_input("Valor mínimo", float(values.min()), float(values.max()), float(values.min()))
            vmax = st.sidebar.number_input("Valor máximo", float(values.min()), float(values.max()), float(values.max()))

        colormap = cm.LinearColormap(cm.linear.Blues_09.colors, vmin=vmin, vmax=vmax)

        center = gdf.geometry.centroid
        m = folium.Map(
            location=[center.y.mean(), center.x.mean()],
            zoom_start=14,
            tiles=None
        )

        folium.TileLayer("openstreetmap", name="OpenStreetMap").add_to(m)
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
            tooltip=folium.GeoJsonTooltip(
                fields=["USO", col],
                aliases=["Tipología del edificio", var_label],
                localize=True
            )
        ).add_to(m)

        colormap.caption = col
        colormap.add_to(m)

        folium.LayerControl(collapsed=False).add_to(m)

# =========================
# MOSTRAR MAPA
# =========================
st_folium(
    m,
    width=1200,
    height=650,
    returned_objects=[]
)

