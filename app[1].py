
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Smart Energy Optimization", page_icon="⚡", layout="wide")

FACTORIES = {
    "Food Processing": {
        "peak":75, "production":100,
        "machines":[
            ("Industrial Chiller",30,"Critical",15,24),
            ("Air Compressor",18,"High",65,7),
            ("Packaging Machine",14,"Critical",20,11),
            ("Conveyor System",8,"Medium",55,3),
            ("HVAC System",12,"Low",85,3),
            ("Water Pump",7,"Medium",70,2)]
    },
    "Textile Manufacturing": {
        "peak":90, "production":80,
        "machines":[
            ("Spinning Machine",32,"Critical",15,27),
            ("Air Compressor",20,"High",70,7),
            ("Weaving Machine",24,"Critical",20,19),
            ("HVAC",16,"Low",85,4),
            ("Water Pump",9,"Medium",70,3)]
    },
    "Automotive Component": {
        "peak":85, "production":35,
        "machines":[
            ("CNC Machine",28,"Critical",15,23),
            ("Welding Machine",22,"Critical",20,18),
            ("Air Compressor",18,"High",70,6),
            ("Conveyor",10,"Medium",55,4),
            ("HVAC",14,"Low",85,3)]
    }
}

def make_base(factory):
    return pd.DataFrame([
        {"Machine":n,"Rated kW":float(r),"Priority":p,"Flexibility %":float(f),
         "Minimum kW":float(m),"Power kW":float(r),"Status":"Running"}
        for n,r,p,f,m in FACTORIES[factory]["machines"]
    ])

def set_factory(factory):
    st.session_state.factory=factory
    st.session_state.df=make_base(factory)
    st.session_state.peak=False
    st.session_state.actions=[]
    st.session_state.last_action="System ready. Factory is operating at normal baseline."

if "factory" not in st.session_state:
    set_factory("Food Processing")

factory=st.sidebar.selectbox("🏭 Factory",list(FACTORIES),index=list(FACTORIES).index(st.session_state.factory))
if factory != st.session_state.factory:
    set_factory(factory)
df=st.session_state.df.copy()
cfg=FACTORIES[factory]

st.sidebar.title("⚡ Smart Energy Optimization")
st.sidebar.caption("Industrial energy decision & optimization app")

peak=st.sidebar.toggle("⚠️ Simulate Peak Event",value=st.session_state.peak)
if peak != st.session_state.peak:
    st.session_state.peak=peak
    st.session_state.actions=[]
    if peak:
        d=make_base(factory)
        d["Power kW"]=d["Rated kW"]*1.15
        st.session_state.df=d
        st.session_state.last_action="Peak event simulated. Demand increased for stress testing."
    else:
        st.session_state.df=make_base(factory)
        st.session_state.last_action="Peak event OFF. All machine values restored to exact normal baseline."
    st.rerun()

if st.sidebar.button("🔄 Reset Factory",use_container_width=True):
    set_factory(factory)
    st.rerun()

tariff=st.sidebar.number_input("Energy tariff (₹/kWh)",0.0,100.0,8.5,0.5)
emission=st.sidebar.number_input("CO₂ factor (kg/kWh)",0.0,5.0,0.70,0.05)
auto=st.sidebar.toggle("🔁 Auto Re-Optimization",value=False)

df=st.session_state.df.copy()
demand=float(df["Power kW"].sum())
forecast=float(demand*(1.04 if st.session_state.peak else 1.02))
critical=float(df.loc[df.Priority=="Critical","Power kW"].sum())
flex=float(((df["Power kW"]-df["Minimum kW"]).clip(lower=0)*df["Flexibility %"]/100).sum())
risk="HIGH" if forecast>cfg["peak"] else ("MEDIUM" if forecast>0.95*cfg["peak"] else "LOW")
cost=demand*tariff
co2=demand*emission
abnormal=df[df["Power kW"]>df["Rated kW"]*1.10]
required=max(0,forecast-cfg["peak"])

alerts=[]
if forecast>cfg["peak"]:
    alerts.append(f"Peak risk: forecast {forecast:.1f} kW exceeds {cfg['peak']} kW limit.")
for _,r in abnormal.iterrows():
    alerts.append(f"Abnormal consumption: {r.Machine} is above normal baseline.")
for _,r in df[df.Status=="Offline"].iterrows():
    alerts.append(f"Machine offline: {r.Machine}.")

st.title("⚡ Smart Energy Optimization")
st.caption(f"{factory} • Production target: {cfg['production']} units/hr • Virtual factory prototype")

k=st.columns(7)
k[0].metric("Live Demand",f"{demand:.1f} kW")
k[1].metric("Forecast Peak",f"{forecast:.1f} kW")
k[2].metric("Peak Risk",risk)
k[3].metric("Flexible Capacity",f"{flex:.1f} kW")
k[4].metric("Critical Load",f"{critical:.1f} kW")
k[5].metric("Cost / Hour",f"₹{cost:,.0f}")
k[6].metric("CO₂ / Hour",f"{co2:.1f} kg")

tabs=st.tabs(["📊 Dashboard","🎛️ Machine Control","🔮 Forecast","🧠 Optimization","🧪 What-If","🚨 Alerts","📋 Reports"])

with tabs[0]:
    left,right=st.columns(2)
    with left:
        fig=px.bar(df,x="Machine",y="Power kW",title="Current Machine Demand")
        st.plotly_chart(fig,use_container_width=True)
    with right:
        x=np.arange(12)
        y=np.linspace(demand*0.98,forecast,12)
        f=pd.DataFrame({"Step":x,"Demand kW":y})
        fig=px.line(f,x="Step",y="Demand kW",markers=True,title="Forecast Trend")
        fig.add_hline(y=cfg["peak"],line_dash="dash",annotation_text="Peak Limit")
        st.plotly_chart(fig,use_container_width=True)
    st.info("💡 "+st.session_state.last_action)
    st.subheader("Factory Status")
    status=pd.DataFrame({
        "Parameter":["Peak Limit","Production Target","Peak Event","Abnormal Machines","Optimization Actions"],
        "Value":[f"{cfg['peak']} kW",f"{cfg['production']} units/hr","ON" if st.session_state.peak else "OFF",
                 len(abnormal),len(st.session_state.actions)]
    })
    st.dataframe(status,use_container_width=True,hide_index=True)

with tabs[1]:
    st.subheader("🎛️ Machine Control Mode")
    st.write("Simulation mode: adjust flexible machine power or mark a machine offline. Critical machines cannot go below their minimum operating power.")
    control=st.data_editor(
        df[["Machine","Rated kW","Priority","Flexibility %","Minimum kW","Power kW","Status"]],
        use_container_width=True,hide_index=True,
        column_config={
            "Power kW":st.column_config.NumberColumn("Power kW",min_value=0),
            "Status":st.column_config.SelectboxColumn("Status",options=["Running","Offline"])
        },
        disabled=["Machine","Rated kW","Priority","Flexibility %","Minimum kW"]
    )
    if st.button("✅ Apply Machine Changes"):
        new=control.copy()
        for i,r in new.iterrows():
            if r.Status=="Offline":
                new.at[i,"Power kW"]=0.0
            else:
                new.at[i,"Power kW"]=max(float(r["Minimum kW"]),min(float(r["Power kW"]),float(r["Rated kW"])*1.15))
        st.session_state.df=new
        st.session_state.last_action="Manual machine control changes applied and total demand recalculated."
        st.rerun()

with tabs[2]:
    st.subheader("🔮 Demand Forecast")
    horizon=st.slider("Forecast horizon (minutes)",15,120,60,15)
    fp=demand*(1+0.01+horizon/5000)
    c1,c2,c3=st.columns(3)
    c1.metric("Predicted Peak",f"{fp:.1f} kW")
    c2.metric("Peak Limit",f"{cfg['peak']} kW")
    c3.metric("Margin",f"{cfg['peak']-fp:.1f} kW")
    if fp>cfg["peak"]: st.error("⚠️ Forecast crosses the peak limit.")
    else: st.success("✅ Forecast remains within the peak limit.")
    st.caption("Prototype forecast uses simulated operating data. A real deployment can use historical meter data and a trained forecasting model.")

with tabs[3]:
    st.subheader("🧠 Dynamic Production-Safe Optimization")
    st.write("The system selects flexible, lower-priority loads first and protects critical loads.")
    st.metric("Required Reduction",f"{required:.1f} kW")
    cand=df[(df.Priority!="Critical")&(df.Status=="Running")].copy()
    cand["Available Reduction"]=((cand["Power kW"]-cand["Minimum kW"]).clip(lower=0)*cand["Flexibility %"]/100)
    priority_order={"Low":0,"Medium":1,"High":2,"Critical":3}
    cand["Priority Rank"]=cand.Priority.map(priority_order)
    cand=cand.sort_values(["Flexibility %","Priority Rank"],ascending=[False,True])
    st.dataframe(cand[["Machine","Priority","Flexibility %","Available Reduction"]],use_container_width=True,hide_index=True)
    if st.button("🔁 Apply Dynamic Optimization"):
        new=df.copy(); need=required; acts=[]
        for i,r in cand.iterrows():
            if need<=0: break
            reduction=min(need,float(r["Available Reduction"]))
            if reduction>0:
                new.at[i,"Power kW"]=float(r["Power kW"])-reduction
                need-=reduction
                acts.append(f"{r.Machine}: reduced {reduction:.1f} kW")
        saved=demand-float(new["Power kW"].sum())
        st.session_state.df=new
        action="; ".join(acts) if acts else "No safe flexible-load reduction was required."
        st.session_state.last_action="Optimization result: "+action
        st.session_state.actions.append({"Time":datetime.now().strftime("%H:%M:%S"),"Action":action,"Saved kW":max(0,saved)})
        st.success(f"Optimization applied. Demand reduction: {max(0,saved):.1f} kW")
        st.rerun()
    st.subheader("Decision logic")
    st.write("1) Check forecast vs peak limit → 2) find flexible loads → 3) protect critical loads → 4) stay above minimum power → 5) apply the smallest safe adjustment needed.")

with tabs[4]:
    st.subheader("🧪 What-If Simulator")
    m=st.selectbox("Machine",df.Machine)
    r=df[df.Machine==m].iloc[0]
    reduction=st.slider("Reduce selected machine (%)",0,100,20,5)
    simulated=max(float(r["Minimum kW"]),float(r["Power kW"])*(1-reduction/100))
    if r.Status=="Offline": simulated=0
    newtotal=demand-float(r["Power kW"])+simulated
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Current",f"{demand:.1f} kW")
    c2.metric("What-If",f"{newtotal:.1f} kW")
    c3.metric("Cost / Hour",f"₹{newtotal*tariff:,.0f}")
    c4.metric("CO₂ / Hour",f"{newtotal*emission:.1f} kg")
    st.write(f"**{m}:** {r['Power kW']:.1f} kW → {simulated:.1f} kW. Minimum operating limit is protected.")

with tabs[5]:
    st.subheader("🚨 Smart Alerts")
    if alerts:
        for a in alerts: st.warning(a)
    else:
        st.success("No active alerts.")
    st.subheader("🧠 Explainable Optimization")
    if st.session_state.actions:
        st.write(st.session_state.actions[-1]["Action"])
    else:
        st.write("When optimization is applied, the selected load and reduction reason will be shown here.")
    st.info("Selection is based mainly on flexibility and priority. Critical loads are protected.")

with tabs[6]:
    st.subheader("📋 Energy & Optimization Reports")
    saved=sum(float(a["Saved kW"]) for a in st.session_state.actions)
    c1,c2,c3=st.columns(3)
    c1.metric("Recorded Reduction",f"{saved:.1f} kW")
    c2.metric("Estimated Cost Saving / h",f"₹{saved*tariff:,.0f}")
    c3.metric("Estimated CO₂ Avoided / h",f"{saved*emission:.1f} kg")
    st.write("### Machine Report")
    st.dataframe(df,use_container_width=True,hide_index=True)
    if st.session_state.actions:
        h=pd.DataFrame(st.session_state.actions)
        st.write("### Optimization History")
        st.dataframe(h,use_container_width=True,hide_index=True)
        st.download_button("📥 Download CSV",h.to_csv(index=False),"optimization_report.csv","text/csv")
    if st.button("💾 Record Current Reading"):
        st.session_state.actions.append({"Time":datetime.now().strftime("%H:%M:%S"),"Action":"Recorded current factory reading","Saved kW":0.0})
        st.success("Reading recorded.")

st.sidebar.divider()
st.sidebar.caption("Prototype only: values are simulated. Real deployment needs certified meters, PLC/VFD interfaces and safety interlocks.")
