import streamlit as st
import pandas as pd

st.set_page_config(page_title='Escaleras 2.0', page_icon='📈', layout='centered')
st.markdown('''<style>
.block-container{max-width:740px;padding-top:1.3rem;padding-left:1rem;padding-right:1rem}
h1{font-size:1.8rem!important}div[data-testid="stMetric"]{background:#192536;border:1px solid #34475b;padding:12px;border-radius:14px}
.stButton button{border-radius:12px;min-height:44px;width:100%}
@media(max-width:600px){h1{font-size:1.55rem!important}.block-container{padding-left:.8rem;padding-right:.8rem}}
</style>''', unsafe_allow_html=True)
st.title('📈 Escaleras 2.0')
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
    escenarios=sorted(set([0]+niveles))
    resultados=[]
    for n in escenarios:
        cobro=sum(m*f['cuota'] for m,f in zip(montos,filas) if n>=f['linea'])
        neto=cobro-presupuesto
        resultados.append({'Tiros / eventos':f'Menos de {niveles[0]}' if n==0 else f'{n}+', 'Cobro ($)':round(cobro,2),'Ganancia neta ($)':round(neto,2),'ROI (%)':round(neto/presupuesto*100,1)})
        with st.container(border=True):
            st.markdown(f"**{'Menos de '+str(niveles[0]) if n==0 else str(n)+' o más'} {mercado.lower()}**")
            p,q=st.columns(2)
            p.metric('Cobro total',f'${cobro:,.2f}')
            q.metric('Ganancia neta',f'${neto:+,.2f}')
    st.bar_chart(pd.DataFrame(resultados).set_index('Tiros / eventos')['Ganancia neta ($)'])
    st.download_button('⬇️ Descargar simulación CSV',pd.DataFrame(resultados).to_csv(index=False).encode('utf-8-sig'),file_name='escalera_resultados.csv',mime='text/csv',use_container_width=True)
    st.info('Las apuestas del mismo jugador son acumulativas: alcanzar una línea alta también gana las inferiores. Los cobros incluyen la devolución del importe de las selecciones ganadoras.')
    st.caption('La distribución es una regla matemática, no un pronóstico ni una optimización estadística. No considera probabilidades, comisiones ni cambios de cuotas. Comprueba siempre las reglas del mercado.')
except (ValueError,TypeError) as e:
    st.error(str(e))
