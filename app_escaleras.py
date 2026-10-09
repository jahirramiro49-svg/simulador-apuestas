import streamlit as st
import pandas as pd

st.set_page_config(page_title='Escalera de Props', page_icon='📈', layout='centered')
st.title('📈 Simulador de apuestas escalonadas')
st.caption('Tiros, tiros a puerta, faltas y otras estadísticas. Los cálculos son simulaciones, no pronósticos.')

jugador = st.text_input('Jugador', 'Gonzalo García')
mercado = st.selectbox('Mercado', ['Tiros', 'Tiros a puerta', 'Faltas', 'Otro'])
presupuesto = st.number_input('Presupuesto total ($)', min_value=1.0, value=500.0, step=50.0)
modo = st.radio('Distribución', ['Porcentajes manuales', 'Montos manuales', 'Igualar cobro al alcanzar cada línea'], help='La opción de igualar cobros distribuye el presupuesto inversamente a las cuotas; no garantiza ganancia.')

if 'lineas' not in st.session_state:
    st.session_state.lineas = pd.DataFrame({'Línea (mínimo)': [3, 4, 5], 'Cuota decimal': [1.56, 2.62, 4.0], 'Porcentaje': [50.0, 35.0, 15.0], 'Monto ($)': [250.0, 175.0, 75.0]})
st.subheader('Configura las líneas')
df = st.data_editor(st.session_state.lineas, num_rows='dynamic', hide_index=True, use_container_width=True,
    column_config={'Línea (mínimo)': st.column_config.NumberColumn(min_value=1, step=1),
                   'Cuota decimal': st.column_config.NumberColumn(min_value=1.01, step=0.05, format='%.2f'),
                   'Porcentaje': st.column_config.NumberColumn(min_value=0.0, step=5.0, format='%.2f'),
                   'Monto ($)': st.column_config.NumberColumn(min_value=0.0, step=10.0, format='%.2f')}, key='editor')

try:
    if df.empty or df.isna().any().any():
        raise ValueError('Completa todas las celdas y agrega al menos una línea.')
    niveles = df['Línea (mínimo)'].astype(float).tolist()
    cuotas = df['Cuota decimal'].astype(float).tolist()
    if any(x < 1 or not x.is_integer() for x in niveles) or len(set(niveles)) != len(niveles):
        raise ValueError('Las líneas deben ser enteros positivos y no repetirse.')
    if any(x <= 1 for x in cuotas):
        raise ValueError('Las cuotas decimales deben ser mayores que 1.')
    if modo == 'Porcentajes manuales':
        porcentajes = df['Porcentaje'].astype(float).tolist()
        if any(x < 0 for x in porcentajes) or abs(sum(porcentajes) - 100) > 0.01:
            raise ValueError(f'Los porcentajes deben ser no negativos y sumar 100%. Suman {sum(porcentajes):.2f}%.')
        montos = [presupuesto * p / 100 for p in porcentajes]
    elif modo == 'Montos manuales':
        montos = df['Monto ($)'].astype(float).tolist()
        if any(x < 0 for x in montos) or abs(sum(montos) - presupuesto) > 0.01:
            raise ValueError(f'Los montos deben ser no negativos y sumar ${presupuesto:,.2f}. Suman ${sum(montos):,.2f}.')
    else:
        pesos = [1 / cuota for cuota in cuotas]
        montos = [presupuesto * peso / sum(pesos) for peso in pesos]

    st.subheader('Distribución calculada')
    apuestas = pd.DataFrame({'Línea': [f'{int(n)}+' for n in niveles], 'Cuota': cuotas, 'Apuesta ($)': montos,
                             'Cobro individual ($)': [m*c for m,c in zip(montos,cuotas)]})
    st.dataframe(apuestas.style.format({'Cuota':'{:.2f}', 'Apuesta ($)':'${:,.2f}', 'Cobro individual ($)':'${:,.2f}'}), hide_index=True, use_container_width=True)

    st.subheader('Resultados según la estadística final')
    resultados=[]
    for n in range(0, int(max(niveles))+1):
        cobro=sum(m*c for linea,m,c in zip(niveles,montos,cuotas) if n >= linea)
        neto=cobro-presupuesto
        resultados.append({'Resultado': str(n) if n < max(niveles) else f'{n} o más', 'Cobro ($)': cobro,
                           'Ganancia neta ($)': neto, 'ROI (%)': neto/presupuesto*100})
    tabla=pd.DataFrame(resultados)
    st.dataframe(tabla.style.format({'Cobro ($)':'${:,.2f}', 'Ganancia neta ($)':'${:+,.2f}', 'ROI (%)':'{:+.1f}%'}).map(lambda v: 'color: #16a34a' if v>=0 else 'color: #ef4444', subset=['Ganancia neta ($)']), hide_index=True, use_container_width=True)
    st.bar_chart(tabla.set_index('Resultado')['Ganancia neta ($)'])
    st.info('Las líneas del mismo jugador son acumulativas: si consigue 5 tiros, también ganan 3+ y 4+. El cobro incluye lo apostado en las selecciones ganadoras.')
    csv=tabla.to_csv(index=False).encode('utf-8-sig')
    st.download_button('Descargar resultados CSV', csv, file_name='simulacion_escalera.csv', mime='text/csv')
except (ValueError, TypeError) as e:
    st.error(str(e))
