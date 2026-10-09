import streamlit as st
import pandas as pd

st.set_page_config(page_title='Escaleras 3.2', page_icon='📈', layout='centered')
st.markdown('''<style>
.block-container{max-width:740px;padding-top:1.3rem;padding-left:1rem;padding-right:1rem}
h1{font-size:1.8rem!important}div[data-testid="stMetric"]{background:#192536;border:1px solid #34475b;padding:12px;border-radius:14px}
.stButton button{border-radius:12px;min-height:44px;width:100%}
@media(max-width:600px){h1{font-size:1.55rem!important}.block-container{padding-left:.8rem;padding-right:.8rem}}
</style>''', unsafe_allow_html=True)
st.title('📈 Escaleras 3.2')
st.caption('Simulador de líneas acumulativas • diseñado para celular')

jugador = st.text_input('⚽ Jugador', 'Gonzalo García')
mercado = st.selectbox('Mercado', ['Tiros', 'Tiros a puerta', 'Faltas', 'Otro'])
presupuesto = st.number_input('💰 Presupuesto ($)', min_value=1.0, value=500.0, step=50.0)
modo = st.selectbox('🎯 Estrategia', ['🟡 Progresiva (B)', '🟢 Conservadora', '🔴 Agresiva', '✍️ Manual'])
st.caption('En las estrategias automáticas se reserva una parte para la primera línea y el resto se distribuye entre líneas superiores.')

if 'niveles' not in st.session_state:
    st.session_state.niveles = [{'linea':3,'cuota':1.56,'pct':70.0}, {'linea':4,'cuota':2.62,'pct':20.0}, {'linea':5,'cuota':4.0,'pct':10.0}]

c1,c2 = st.columns(2)
with c1:
    if st.button('➕ Agregar línea'):
        ultimo=max((x['linea'] for x in st.session_state.niveles), default=2)
        st.session_state.niveles.append({'linea':ultimo+1,'cuota':3.0,'pct':0.0})
        st.rerun()
with c2:
    if st.button('➖ Quitar última') and len(st.session_state.niveles)>2:
        st.session_state.niveles.pop()
        st.rerun()

st.subheader('📊 Líneas y momios')
filas=[]
for i, original in enumerate(st.session_state.niveles):
    with st.container(border=True):
        a,b,c=st.columns([1,1.2,1])
        with a: linea=st.number_input('Línea (+)',min_value=1,step=1,value=int(original['linea']),key=f'linea_{i}')
        with b: cuota=st.number_input('Cuota decimal',min_value=1.01,step=.05,value=float(original['cuota']),format='%.2f',key=f'cuota_{i}')
        with c: pct=st.number_input('% manual',min_value=0.0,max_value=100.0,step=5.0,value=float(original['pct']),key=f'pct_{i}')
        filas.append({'linea':linea,'cuota':cuota,'pct':pct})
st.session_state.niveles=filas
filas=sorted(filas,key=lambda x:x['linea'])

if modo=='🟡 Progresiva (B)':
    meta=st.number_input('Ganancia mínima deseada en primera línea ($)',min_value=0.0,value=25.0,step=5.0)
    sesgo=st.slider('Prioridad de líneas altas',1,5,3,help='Mayor valor = más inversión hacia la última línea.')
elif modo=='🟢 Conservadora':
    meta=0.0
    st.caption('Busca recuperar el presupuesto al alcanzar la primera línea, sin exigir ganancia.')
elif modo=='🔴 Agresiva':
    tolerancia=st.slider('Pérdida máxima aceptada al alcanzar primera línea (%)',0,90,30,5)
    meta=-presupuesto*tolerancia/100
    st.caption('La primera línea puede cerrar con pérdida; se destina más dinero a las superiores.')
else:
    meta=None

try:
    if len(filas)<2 or len(set(x['linea'] for x in filas))!=len(filas):
        raise ValueError('Necesitas al menos dos líneas distintas.')
    if modo=='✍️ Manual':
        total=sum(x['pct'] for x in filas)
        if abs(total-100)>0.001: raise ValueError(f'Los porcentajes manuales deben sumar 100%. Actualmente: {total:g}%.')
        montos=[presupuesto*x['pct']/100 for x in filas]
    else:
        cuota_base=filas[0]['cuota']
        minimo=(presupuesto+meta)/cuota_base
        if minimo>presupuesto+1e-8:
            max_ganancia=presupuesto*(cuota_base-1)
            raise ValueError(f'La meta de ${meta:,.2f} no es posible con cuota {cuota_base:.2f}. Incluso apostando todo a la primera línea, la ganancia máxima sería ${max_ganancia:,.2f}, sin presupuesto para las demás.')
        if minimo<0: minimo=0
        resto=max(0,presupuesto-minimo)
        # Reservar toda la cantidad necesaria para el objetivo base; repartir el resto en líneas superiores.
        # Las ponderaciones controlan el perfil de riesgo; no son optimización de EV.
        superiores=filas[1:]
        if modo=='🟢 Conservadora': pesos=[1/(i+1) for i in range(len(superiores))]
        elif modo=='🔴 Agresiva': pesos=[(i+1)**2 for i in range(len(superiores))]
        else: pesos=[(i+1)**(sesgo-1) for i in range(len(superiores))]
        suma=sum(pesos)
        montos=[minimo]+[resto*w/suma for w in pesos]
        if resto<0.01:
            st.warning('La meta consume casi todo el presupuesto: apenas queda dinero para las líneas altas.')
    st.subheader('💵 Distribución propuesta')
    for f,m in zip(filas,montos):
        with st.container(border=True):
            x,y,z=st.columns(3)
            x.metric('Línea',f"{f['linea']}+")
            y.metric('Apostar',f'${m:,.2f}')
            z.metric('Cobro individual',f'${m*f["cuota"]:,.2f}')
            st.caption(f"Momio {f['cuota']:.2f} · {100*m/presupuesto:.1f}% del presupuesto")
    st.subheader('🏁 Resultados posibles')
    niveles=[x['linea'] for x in filas]
    escenarios=[min(niveles)-1]+list(range(min(niveles), max(niveles)+1))
    resultados=[]
    for n in escenarios:
        cobro=sum(m*f['cuota'] for m,f in zip(montos,filas) if n>=f['linea'])
        neto=cobro-presupuesto
        resultados.append({'Tiros / eventos':f'Menos de {min(niveles)}' if n < min(niveles) else (f'{n}' if n < max(niveles) else f'{n} o más'), 'Cobro ($)':round(cobro,2),'Ganancia neta ($)':round(neto,2),'ROI (%)':round(neto/presupuesto*100,1)})
        with st.container(border=True):
            st.markdown(f"**{'Menos de '+str(min(niveles)) if n < min(niveles) else (str(n) if n < max(niveles) else str(n)+' o más')} {mercado.lower()}**")
            p,q=st.columns(2)
            p.metric('Cobro total',f'${cobro:,.2f}')
            q.metric('Ganancia neta',f'${neto:+,.2f}')
    st.bar_chart(pd.DataFrame(resultados).set_index('Tiros / eventos')['Ganancia neta ($)'])
    st.download_button('⬇️ Descargar simulación CSV',pd.DataFrame(resultados).to_csv(index=False).encode('utf-8-sig'),file_name='escalera_resultados.csv',mime='text/csv',use_container_width=True)
    st.info('Las apuestas del mismo jugador son acumulativas: alcanzar una línea alta también gana las inferiores. Los cobros incluyen la devolución del importe de las selecciones ganadoras.')
    st.caption('La distribución es una regla matemática, no un pronóstico ni una optimización estadística. No considera probabilidades, comisiones ni cambios de cuotas. Comprueba siempre las reglas del mercado.')
except (ValueError,TypeError) as e:
    st.error(str(e))

st.divider()
st.header('🔎 Análisis estadístico y cuotas')
st.caption('Introduce los resultados de partidos anteriores y compara cuotas de distintas casas. No consulta automáticamente StatsHub ni casas de apuestas.')
with st.expander('📋 Introducir historial y analizar', expanded=True):
    historial = st.text_area('Estadísticas por partido (separadas por comas)', value='6, 4, 3, 1, 5, 3, 3, 1, 6, 3', help='Ejemplo: 2, 4, 1, 3. Cada número representa un partido.')
    st.caption('Escribe los tiros de los últimos 10 partidos, separados por comas. El promedio se calcula automáticamente; no necesitas escribirlo.')
    minutos_promedio = st.number_input('⏱️ Minutos promedio por partido (StatsHub)', min_value=0.0, max_value=130.0, value=81.67, step=0.5, help='Introduce 0 si no tienes el dato. Debe corresponder a los mismos partidos del historial para estimar eventos/90.')
    st.caption('No necesitas introducir los minutos de cada partido. Con un único promedio de minutos se calcula una tasa aproximada por 90; no se pueden filtrar partidos por minutos individuales.')
    col_a, col_b = st.columns(2)
    with col_a:
        casa_1 = st.text_input('Casa 1', 'Draftea')
    with col_b:
        casa_2 = st.text_input('Casa 2', 'Novibet')
    st.markdown('**Cuotas para las líneas de la escalera**')
    st.caption('Puedes dejar un momio vacío si la casa no ofrece esa línea.')
    cuotas_casas=[]
    for j, f in enumerate(filas):
        ca, cb, cc = st.columns([1, 1.2, 1.2])
        ca.markdown(f"**{f['linea']}+**")
        q1 = cb.text_input(f'{casa_1} · {f["linea"]}+', value=f'{f["cuota"]:.2f}', key=f'casa1_{j}')
        q2 = cc.text_input(f'{casa_2} · {f["linea"]}+', value='', placeholder='Opcional', key=f'casa2_{j}')
        cuotas_casas.append((f['linea'], q1, q2))
    try:
        valores = [int(s.strip()) for s in historial.replace('\n', ',').replace(';', ',').split(',') if s.strip()]
        if not valores or any(v < 0 for v in valores):
            raise ValueError('Introduce al menos un resultado entero mayor o igual a cero.')
        if len(valores) != 10:
            st.info(f'Has introducido {len(valores)} partidos. Puedes usar esa cantidad, aunque se recomiendan los últimos 10.')
        n = len(valores)
        st.subheader('📈 Resumen del historial')
        m1, m2, m3 = st.columns(3)
        m1.metric('Partidos', n)
        m2.metric('Promedio', f'{sum(valores)/n:.2f}')
        m3.metric('Máximo', max(valores))
        if minutos_promedio > 0:
            a90, b90 = st.columns(2)
            a90.metric('Eventos por 90 min (aprox.)', f'{(sum(valores)/n)*90/minutos_promedio:.2f}')
            b90.metric('Minutos promedio (introducido)', f'{minutos_promedio:.1f}')
            st.caption('Estimación: promedio de eventos × 90 ÷ minutos promedio. Solo es válida como tasa agregada si ambos promedios corresponden a la misma muestra; no equivale a predecir los próximos 90 minutos.')
        st.line_chart(pd.DataFrame({'Partido':list(range(1,n+1)), 'Eventos':valores}).set_index('Partido'))
        datos=[]
        for linea, q1, q2 in cuotas_casas:
            aciertos=sum(v>=linea for v in valores)
            ph=aciertos/n
            # Suavizado Beta(2,2): evita probabilidades extremas en muestras pequeñas.
            p=(aciertos+2)/(n+4)
            for casa, qtxt in ((casa_1,q1),(casa_2,q2)):
                if not qtxt.strip():
                    continue
                cuota=float(qtxt.replace(',','.'))
                if not (1 < cuota < 100000):
                    raise ValueError(f'El momio de {casa} para {linea}+ debe ser mayor que 1.')
                datos.append({'Línea':f'{linea}+', 'Casa':casa, 'Cuota':cuota,
                              'Aciertos':f'{aciertos}/{n}', 'Histórico (%)':round(ph*100,1),
                              'Estimado (%)':round(p*100,1), 'Equilibrio (%)':round(100/cuota,1),
                              'EV (%)':round((p*cuota-1)*100,1)})
        tabla=pd.DataFrame(datos)
        if not tabla.empty:
            st.subheader('🏠 Comparación de casas')
            st.dataframe(tabla, hide_index=True, use_container_width=True)
            st.caption('Prob. estimada = (aciertos + 2) / (partidos + 4), con suavizado Beta(2,2). EV = probabilidad estimada × cuota − 1. El cálculo usa el historial introducido, sin filtrar por minutos. No ajusta por los minutos futuros esperados.')
            for linea in sorted(tabla['Línea'].unique(), key=lambda s:int(s[:-1])):
                subset=tabla[tabla['Línea']==linea]
                mejor=subset.loc[subset['Cuota'].idxmax()]
                st.markdown(f'**{linea}:** mejor cuota introducida: **{mejor["Casa"]} ({mejor["Cuota"]:.2f})** · EV estimado **{mejor["EV (%)"]:+.1f}%**')
            st.download_button('⬇️ Descargar análisis CSV', tabla.to_csv(index=False).encode('utf-8-sig'), file_name='analisis_jugador.csv', mime='text/csv', use_container_width=True)
        st.warning('Los eventos por 90 son una tasa descriptiva: no implican que el jugador mantendrá el mismo ritmo durante 90 minutos. El EV es ilustrativo y depende de una probabilidad incierta. Rival, titularidad y contexto pueden cambiar los resultados. No hay ganancias garantizadas.')
    except (ValueError, OverflowError) as error:
        st.error(f'Revisa los datos: {error}')
