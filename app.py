import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import pydeck as pdk

st.title("🌎 Monitor de Calidad del Aire")

# Cargar archivo Excel
archivo = st.file_uploader("📁 Cargar archivo Excel con datos", type=["xlsx"])

if archivo:
    df = pd.read_excel(archivo)

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

    # Selector de sensor
    if 'sensor_id' in df.columns:
        sensores_disponibles = sorted(df['sensor_id'].unique())
        sensor_seleccionado = st.selectbox("🔎 Selecciona sensor", sensores_disponibles)
        df = df[df['sensor_id'] == sensor_seleccionado]

    # Selector de fecha
    fechas_disponibles = sorted(df['fecha'].unique())
    fecha_seleccionada = st.selectbox("📅 Selecciona una fecha", fechas_disponibles)
    df_fecha = df[df['fecha'] == fecha_seleccionada]

    st.write(f"## 📊 Datos del sensor {sensor_seleccionado} para el día {fecha_seleccionada}")

    # Tabla con links
    cols_tabla = ['local_time', 'PM 2.5', 'PM 10', 'CO', 'O3', 'NO2', 'Calidad del Aire', 'Mapa']
    cols_tabla = [col for col in cols_tabla if col in df_fecha.columns]

    def tabla_con_links(df, columnas):
        tabla_md = "| " + " | ".join(columnas) + " |\n"
        tabla_md += "| " + " | ".join(["---"] * len(columnas)) + " |\n"
        for _, fila in df[columnas].iterrows():
            fila_str = []
            for col in columnas:
                val = fila[col]
                if col == "Mapa" and val != "":
                    fila_str.append(val)  # val ya es link Markdown
                else:
                    fila_str.append(str(val))
            tabla_md += "| " + " | ".join(fila_str) + " |\n"
        return tabla_md

    st.markdown(tabla_con_links(df_fecha, cols_tabla), unsafe_allow_html=True)

    # Gráfico de contaminante
    contaminantes = [c for c in ['PM 2.5', 'PM 10', 'CO', 'O3', 'NO2'] if c in df_fecha.columns]
    contaminante_sel = st.selectbox("📈 Selecciona contaminante para graficar", contaminantes)
    df_fecha['hora'] = df_fecha['local_time'].dt.hour

    fig, ax = plt.subplots()
    for calidad in df_fecha['Calidad del Aire'].unique():
        subset = df_fecha[df_fecha['Calidad del Aire'] == calidad]
        color = [c/255 for c in color_map.get(calidad, [128, 128, 128])]
        ax.scatter(subset['hora'], subset[contaminante_sel], label=calidad, color=color)

    ax.set_xlabel("Hora del día")
    ax.set_ylabel(contaminante_sel)
    ax.set_title(f"{contaminante_sel} a lo largo del día")
    ax.legend(title="Calidad del Aire")
    st.pyplot(fig)

    # Mapa interactivo con Pydeck
    if lat_col and lon_col and not df_fecha.empty:
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=df_fecha.to_dict(orient="records"),
            get_position=[lon_col, lat_col],
            get_fill_color=lambda d: d['color'],
            get_radius=100,
            pickable=True,
        )
        view_state = pdk.ViewState(
            latitude=df_fecha[lat_col].mean(),
            longitude=df_fecha[lon_col].mean(),
            zoom=11,
            pitch=30,
        )
        r = pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            map_style="mapbox://styles/mapbox/light-v9"
        )
    
