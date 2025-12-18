# -*- coding: utf-8 -*-
"""
Visor Rochapea – Escenarios, Demografía y Catastro
"""

import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import branca.colormap as cm
import rasterio
from rasterio.plot import reshape_as_image
import matplotlib.pyplot as plt
import io
import base64
from pyproj import Transformer


# =========================
# CONFIG
# =========================
GPKG_PATH = "parcelas_rochapea_completas.gpkg"
LAYER_NAME = "parcelas_rochapea"

ZONAS_VERDES_PATH = "simulacion_zonas_verdes_rochapea_RECUPERADA.shp"
ARBOLES_PATH = "arboles_propuestos.shp"
ICC_RASTERS = {
    "Invierno": "ICC_invierno.tif",
    "Primavera": "ICC_primavera.tif",
    "Verano": "ICC_verano.tif",
    "Otoño": "ICC_otono.tif",
    "Media anual": "ICC_anual.tif"
}


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

Este índice permite comparar parcelas dentro del barrio de la Rochapea y evaluar el impacto de estrategias
de mitigación en los distintos escenarios (actual, ideal y prioritario) y estaciones del año.
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

TEXTO_REDUCCION_VULNERABILIDAD = """
**Reducción del Índice de Vulnerabilidad**

Esta variable representa la reducción porcentual del índice de vulnerabilidad
respecto al escenario actual, como consecuencia de la incorporación de nuevas zonas verdes
y arbolado en los escenarios ideal y prioritario.

Valores más altos indican una mayor disminución de la vulnerabilidad, asociada a una mejora
en las condiciones ambientales y sociales de la parcela, en función de la estación del año.
"""

TEXTO_REDUCCION_ICC = """
**Reducción del Índice de Contaminación (ICC)**

Esta variable representa la reducción porcentual del Índice de Contaminación Combinado (ICC)
respecto al escenario actual, derivada de la implementación de nuevas zonas verdes
y arbolado en los escenarios ideal y prioritario.

Valores más altos indican una mayor reducción de la carga contaminante atmosférica
(NO₂, PM₂.₅ y PM₁₀) asociada a la estrategia de vegetación considerada.
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
    
@st.cache_data
def load_icc_raster(raster_path):
    import rasterio
    with rasterio.open(raster_path) as src:
        data = src.read(1)
        transform = src.transform
        crs = src.crs
        height = src.height
        width = src.width
    return data, transform, crs, height, width

gdf = load_data()
zonas_verdes, arboles = load_vegetation()

import rasterio
import numpy as np
from rasterio.warp import calculate_default_transform, reproject, Resampling
import folium


def add_icc_raster_to_map(
    m,
    raster_path,
    layer_name="ICC (nivel de calle)",
    colormap="reds"
):
    import rasterio
    import numpy as np
    from rasterio.warp import calculate_default_transform, reproject, Resampling
    import folium
    import streamlit as st

    with rasterio.open(raster_path) as src:

        dst_crs = "EPSG:4326"

        transform, width, height = calculate_default_transform(
            src.crs,
            dst_crs,
            src.width,
            src.height,
            *src.bounds
        )

        data = np.empty((height, width), dtype=np.float32)

        reproject(
            source=rasterio.band(src, 1),
            destination=data,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=transform,
            dst_crs=dst_crs,
            resampling=Resampling.bilinear
        )

        # =========================
        # MÁSCARA CORRECTA
        # =========================
        data = np.array(data)

        # Definir rango válido real
        valid_mask = (data > 0) & np.isfinite(data)

        if not valid_mask.any():
            st.warning("Raster sin valores válidos")
            return

        vmin = data[valid_mask].min()
        vmax = data[valid_mask].max()

        norm = np.zeros_like(data, dtype=np.float32)
        norm[valid_mask] = (data[valid_mask] - vmin) / (vmax - vmin)

        # =========================
        # RGBA
        # =========================
        rgba = np.zeros((data.shape[0], data.shape[1], 4), dtype=np.float32)

        if colormap == "reds":
            rgba[..., 0] = norm
        elif colormap == "greens":
            rgba[..., 1] = norm
        elif colormap == "blues":
            rgba[..., 2] = norm

        # ALPHA SOLO DONDE HAY DATOS
        rgba[..., 3] = np.where(valid_mask, norm * 0.9, 0.0)

        # =========================
        # Bounds
        # =========================
        bounds = rasterio.transform.array_bounds(
            height, width, transform
        )

        folium_bounds = [
            [bounds[1], bounds[0]],  # south, west
            [bounds[3], bounds[2]]   # north, east
        ]

        fg = folium.FeatureGroup(
            name=layer_name,
            overlay=True,
            control=True,
            show=True
        )

        folium.raster_layers.ImageOverlay(
            image=rgba,
            bounds=folium_bounds,
            opacity=1.0,
            interactive=True
        ).add_to(fg)

        fg.add_to(m)

        m.fit_bounds(folium_bounds)
        st.write("Raster CRS:", raster_crs)
        st.write("Raster transform:", raster_transform)
        st.write("Lat/Lon clic:", lat, lon)
        st.write("Pixel row/col:", row, col)




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
                "Índice de contaminación (ICC)",
                "ICC a nivel de calle"
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
    
    elif variable in ["Índice de contaminación (ICC)", "ICC a nivel de calle"]:
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
    colormap = None
    
    if variable != "ICC a nivel de calle":
    
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
    # =========================
    # CAPA RASTER ICC (solo escenario actual)
    # =========================
    # =========================
    # CAPA RASTER ICC A NIVEL DE CALLE
    # =========================
    if escenario == "Actual" and variable == "ICC a nivel de calle":
    
        raster_path = ICC_RASTERS.get(estacion)
    
        if raster_path is None:
            st.warning("No hay raster ICC para esta estación.")
        else:
            add_icc_raster_to_map(
                m,
                raster_path,
                layer_name=f"ICC {estacion} (nivel de calle)",
                colormap="reds"
            )
        icc_min = 0
        icc_max = 60   # o el rango que hayas decidido
    
        icc_colormap = cm.LinearColormap(
            colors=cm.linear.Reds_09.colors,
            vmin=icc_min,
            vmax=icc_max,
            caption="ICC a nivel de calle (0–60)"
        )
    
        icc_colormap.add_to(m)




    folium.TileLayer(
            tiles="about:blank",
            attr=" ",
            name="Sin mapa base",
            overlay=False,
            control=True,
            show=True
        ).add_to(m)
        
    m.get_root().html.add_child(
            folium.Element(
                """
                <style>
                .leaflet-container {
                    background: #f5f5f5;
                }
                </style>
                """
            )
    )

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

    # =========================
    # CAPA DE PARCELAS (solo si NO es ICC raster)
    # =========================
    if not (escenario == "Actual" and variable == "ICC a nivel de calle"):
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
    # Añadir colormap SOLO si existe (parcelas)
    if colormap is not None:
        colormap.add_to(m)
    
    folium.LayerControl(collapsed=False).add_to(m)

    # =========================
    # TÍTULO Y TEXTO EXPLICATIVO
    # =========================
    if escenario == "Actual" and variable == "ICC a nivel de calle":
        st.markdown(
            "## ICC a nivel de calle – "
            f"{estacion} (escenario Actual)"
        )
    elif variable == "Índice de Vulnerabilidad":
        st.markdown(
            f"## Índice de Vulnerabilidad en {estacion} "
            f"en el escenario {escenario} (0–100)"
        )
    else:
        st.markdown(f"## {col}")


    if variable == "Índice de Vulnerabilidad":
        st.info(TEXTO_VULNERABILIDAD)

    elif variable == "Índice de contaminación (ICC)":
        st.info(TEXTO_ICC)

    elif variable == "Reducción del índice de Vulnerabilidad":
        st.info(TEXTO_REDUCCION_VULNERABILIDAD)

    elif variable == "Reducción del índice de contaminación (ICC)":
        st.info(TEXTO_REDUCCION_ICC)

    # =========================
    # LAYOUT: MAPA + INFO
    # =========================
    col_map, col_info = st.columns([3, 1])  # 75% mapa, 25% info
    
    with col_map:
        map_data = st_folium(
            m,
            width=900,
            height=650,
            returned_objects=["last_clicked"]
        )
    
    with col_info:
        st.markdown("### Información del punto")

    # =========================
    # LECTURA DEL VALOR ICC AL HACER CLICK
    # =========================
    if (
        escenario == "Actual"
        and variable == "ICC a nivel de calle"
        and map_data
        and map_data.get("last_clicked") is not None
    ):
        lat = map_data["last_clicked"]["lat"]
        lon = map_data["last_clicked"]["lng"]
    
        import rasterio
        from rasterio.warp import transform
    
        raster_path = ICC_RASTERS.get(estacion)
    
        if raster_path is not None:
            data, raster_transform, raster_crs, height, width = load_icc_raster(raster_path)
            xs, ys = transform(
                "EPSG:4326",
                raster_crs,
                [lon],
                [lat]
            )
            
            row, col = rasterio.transform.rowcol(
                raster_transform,
                xs[0],
                ys[0]
            )
            
            if 0 <= row < height and 0 <= col < width:
                value = data[row, col]
            
                if np.isfinite(value):
                    with col_info:
                        st.success(
                            f"📍 **ICC a nivel de calle**\n\n"
                            f"**Estación:** {estacion}\n\n"
                            f"**Valor ICC:** {value:.2f}"
                        )
                else:
                    with col_info:
                        st.warning("No hay valor ICC en este punto.")

    


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

    var_label = st.sidebar.selectbox(
        "Variable demográfica / catastral",
        list(demog_vars.keys())
    )

    col = demog_vars[var_label]

    # =========================
    # MAPA DEMOGRAFÍA
    # =========================
    if col == "USO":
        # Categórico
        m = gdf.explore(
            column="USO",
            categorical=True,
            cmap="Set3",
            tooltip=["USO"],
            tiles="cartodbpositron",
            legend=True
        )


    else:
        # Numérico
        values = gdf[col].dropna()

        vmin = float(values.min())
        vmax = float(values.max())

        colormap = cm.LinearColormap(
            cm.linear.Blues_09.colors,
            vmin=vmin,
            vmax=vmax
        )

        center = gdf.geometry.centroid
        m = folium.Map(
            location=[center.y.mean(), center.x.mean()],
            zoom_start=16,
            tiles=None
        )

        folium.TileLayer(
            tiles="about:blank",
            attr=" ",
            name="Sin mapa base",
            overlay=False,
            control=True,
            show=True
        ).add_to(m)
        
        m.get_root().html.add_child(
            folium.Element(
                """
                <style>
                .leaflet-container {
                    background: #f5f5f5;
                }
                </style>
                """
            )
        )
        
                

    
        folium.TileLayer(
            "cartodbpositron",
            name="CartoDB Positron",
            overlay=False
        ).add_to(m)

    



        def style_function(feature):
            val = feature["properties"].get(col)
            if val is None:
                return {"fillOpacity": 0, "weight": 0}
            return {
                "fill": True,
                "fillColor": colormap(val),
                "color": "#333333",
                "weight": 0.3,
                "fillOpacity": 0.8,
            }

        if not (escenario == "Actual" and variable == "ICC a nivel de calle"):
            folium.GeoJson(
                gdf,
                name="Parcelas",
                style_function=style_function,
                tooltip=folium.GeoJsonTooltip(fields=[col], localize=True)
            ).add_to(m)


        colormap.add_to(m)
        folium.LayerControl(collapsed=False).add_to(m)

    # =========================
    # MOSTRAR MAPA DEMOGRAFÍA
    # =========================
    st_folium(
        m,
        width=1200,
        height=650,
        returned_objects=[]
    )













































