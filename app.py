import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import pydeck as pdk
import gdown

st.set_page_config(page_title="Monitor de Calidad del Aire", layout="wide")
st.title("🌎 Monitor de Calidad del Aire")

# Descargar archivo desde Google Drive
file_id = "1e8q6VZvEvu9VGymnNwFVO7rsP-miTAXu"
url = f"https://drive.google.com/uc?id={file_id}"
archivo = "datos.xlsx"

try:
    gdown.download(url, archivo, quiet=False)
    df = pd.read_excel(archivo)
    st.success("✅ Informacion cargada automáticamente")
except Exception as e:
    st.error("❌ No se pudo cargar el archivo automáticamente.")
    st.exception(e)
    st.stop()

# Convertir fechas
df['local_time'] = pd.to_datetime(df['local_time'])
df['fecha'] = df['local_time'].dt.date

# Detectar columnas de lat/lon
lat_col = None
lon_col = None
for col in df.columns:
    if col.lower() in ['latitude', 'lat']:
        lat_col = col
    if col.lower() in ['longitude', 'lon', 'long']:
        lon_col = col

# Crear columna 'Mapa' con link Markdown si hay lat/lon
if lat_col and lon_col:
    df['Mapa'] = df.apply(
        lambda row: f"[Ver mapa](https://www.google.com/maps?q={row[lat_col]},{row[lon_col]})"
        if pd.notnull(row[lat_col]) and pd.notnull(row[lon_col]) else "",
        axis=1
    )

# Clasificación de calidad del aire por PM2.5
def clasificar_pm25(valor):
    if pd.isna(valor): return "Sin dato"
    if valor <= 12.0: return "Buena"
    elif valor <= 35.4: return "Moderada"
    elif valor <= 55.4: return "Dañina a sensibles"
    elif valor <= 150.4: return "Dañina"
    elif valor <= 250.4: return "Muy dañina"
    else: return "Peligrosa"

if 'PM 2.5' in df.columns:
    df['Calidad del Aire'] = df['PM 2.5'].apply(clasificar_pm25)
else:
    df['Calidad del Aire'] = "Sin dato"

# Mapeo de colores
color_map = {
    "Buena": [0, 128, 0],
    "Moderada": [255, 255, 0],
    "Dañina a sensibles": [255, 165, 0],
    "Dañina": [255, 0, 0],
    "Muy dañina": [153, 0, 76],
    "Peligrosa": [128, 0, 0],
    "Sin dato": [128, 128, 128]
}
df['color'] = df['Calidad del Aire'].map(color_map)
df['color'] = df['color'].apply(lambda x: list(x) if isinstance(x, (list, tuple)) else [128, 128, 128])

st.sidebar.header("Filtros diarios")

if 'sensor_id' in df.columns:
    sensores_disponibles = sorted(df['sensor_id'].unique())
    sensor_seleccionado = st.sidebar.selectbox("🔎 Selecciona sensor", sensores_disponibles)
    df_filtrado = df[df['sensor_id'] == sensor_seleccionado]
else:
    df_filtrado = df.copy()

fechas_disponibles = sorted(df_filtrado['fecha'].unique())
fecha_seleccionada = st.sidebar.selectbox("📅 Selecciona una fecha", fechas_disponibles)
df_fecha = df_filtrado[df_filtrado['fecha'] == fecha_seleccionada]

st.markdown("## 📅 Resumen Diario")

num_registros = len(df_fecha)
st.write(f"- Sensor seleccionado: **{sensor_seleccionado if 'sensor_seleccionado' in locals() else 'N/A'}**")
st.write(f"- Fecha seleccionada: **{fecha_seleccionada}**")
st.write(f"- Número de registros para este filtro: **{num_registros}**")

if num_registros > 0:
    promedios = {}
    for col in ['PM 2.5', 'PM 10', 'CO', 'O3', 'NO2']:
        if col in df_fecha.columns:
            promedios[col] = df_fecha[col].mean()

    if promedios:
        # Panel visual
        indice = promedios.get('PM 2.5', 0)
        if indice <= 12: valor_indice = 25
        elif indice <= 35.4: valor_indice = 63
        elif indice <= 55.4: valor_indice = 100
        elif indice <= 150.4: valor_indice = 150
        else: valor_indice = 200

        nivel_calidad = clasificar_pm25(indice)
        icono = {
            "Buena": "🟢", "Moderada": "🟡", "Dañina a sensibles": "🟠",
            "Dañina": "🔴", "Muy dañina": "🟣", "Peligrosa": "⚫", "Sin dato": "⚪"
        }.get(nivel_calidad, "⚪")

        st.markdown("## 🧭 Panel de Calidad del Aire")
        col1, col2 = st.columns([1, 2])

        with col1:
            st.markdown(f"""
            <div style='background-color:#0d3b66; color:white; padding: 20px; border-radius: 10px; text-align: center;'>
                <h2 style='font-size: 48px; margin: 0;'>{valor_indice}</h2>
                <p style='font-size: 18px; margin: 5px 0;'>Índice CITEAIR</p>
                <p style='font-size: 20px; font-weight: bold;'>{icono} {nivel_calidad}</p>
                <small>Contaminante principal: PM 2.5</small>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown("### 🔬 Promedios de Contaminantes")
            cols = st.columns(5)
            unidades = {
                'PM 2.5': 'μg/m³', 'PM 10': 'μg/m³', 'CO': 'ppb', 'O3': 'ppb', 'NO2': 'ppb'
            }
            for i, (cont, unidad) in enumerate(unidades.items()):
                if cont in promedios:
                    with cols[i]:
                        st.markdown(f"""
                        <div style='background:#f4f4f4; padding:10px; border-radius:10px; text-align:center'>
                            <h4 style='margin:0'>{cont}</h4>
                            <p style='font-size:20px; margin:0'><strong>{promedios[cont]:.2f}</strong> <sub>{unidad}</sub></p>
                        </div>
                        """, unsafe_allow_html=True)

    # Tabla con links
    st.write(f"### 📊 Datos del sensor {sensor_seleccionado} para el día {fecha_seleccionada}")
    cols_tabla = ['sensor_id', 'local_time', 'PM 2.5', 'PM 10', 'CO', 'O3', 'NO2', 'Calidad del Aire', 'Mapa']
    cols_tabla = [col for col in cols_tabla if col in df_fecha.columns]

    def tabla_con_links(df, columnas):
        tabla_md = "| " + " | ".join(columnas) + " |\n"
        tabla_md += "| " + " | ".join(["---"] * len(columnas)) + " |\n"
        for _, fila in df[columnas].iterrows():
            fila_str = []
            for col in columnas:
                val = fila[col]
                if col == "Mapa" and val != "":
                    fila_str.append(val)
                else:
                    fila_str.append(str(val))
            tabla_md += "| " + " | ".join(fila_str) + " |\n"
        return tabla_md

    st.markdown(tabla_con_links(df_fecha, cols_tabla), unsafe_allow_html=True)

    # Gráfica de contaminantes
    contaminantes = [c for c in ['PM 2.5', 'PM 10', 'CO', 'O3', 'NO2'] if c in df_fecha.columns]
    if contaminantes:
        contaminante_sel = st.selectbox("📈 Selecciona contaminante para graficar", contaminantes)
        df_fecha['hora'] = df_fecha['local_time'].dt.hour

        fig, ax = plt.subplots()
        for calidad in df_fecha['Calidad del Aire'].unique():
            subset = df_fecha[df_fecha['Calidad del Aire'] == calidad]
            color = [c / 255 for c in color_map.get(calidad, [128, 128, 128])]
            ax.scatter(subset['hora'], subset[contaminante_sel], label=calidad, color=color)

        ax.set_xlabel("Hora del día")
        ax.set_ylabel(contaminante_sel)
        ax.set_title(f"{contaminante_sel} a lo largo del día")
        ax.legend(title="Calidad del Aire")
        st.pyplot(fig)

# 🗺️ Mapa del trayecto diario con puntos de medición codificados por calidad del aire
if lat_col and lon_col and not df_fecha.empty:
    st.markdown("### 🗺️ Trayecto del Sensor Durante el Día")

    import numpy as np

    # 🔧 Preparar DataFrame para el mapa
    df_mapa = df_fecha[[lat_col, lon_col, 'color']].copy()
    df_mapa = df_mapa.dropna(subset=[lat_col, lon_col, 'color'])
    df_mapa[lat_col] = df_mapa[lat_col].astype(float)
    df_mapa[lon_col] = df_mapa[lon_col].astype(float)

    # Asegurar que color esté en formato correcto
    df_mapa['color'] = df_mapa['color'].apply(
        lambda x: [int(i) for i in x] if isinstance(x, (list, tuple, np.ndarray)) and not pd.isnull(x).any() else [128, 128, 128]
    )

    # Crear la capa de puntos
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df_mapa,
        get_position=f"[{lon_col}, {lat_col}]",
        get_color="color",
        get_radius=50,
        pickable=True
    )

    # Vista centrada en el promedio del trayecto
    view_state = pdk.ViewState(
        latitude=df_mapa[lat_col].mean(),
        longitude=df_mapa[lon_col].mean(),
        zoom=12,
        pitch=0
    )

    # Mostrar mapa
    st.pydeck_chart(pdk.Deck(
        map_style="mapbox://styles/mapbox/light-v9",
        initial_view_state=view_state,
        layers=[layer]
    ))
