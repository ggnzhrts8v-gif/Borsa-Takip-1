import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Borsa Takip", layout="wide")
st.title("📈 Borsa Takip")

HISSELER = [
    "THYAO", "ASELS", "GARAN", "AKBNK", "YKBNK", "ISCTR", "EREGL", "KCHOL",
    "SAHOL", "BIMAS", "TUPRS", "SISE", "FROTO", "TOASO", "PGSUS", "TCELL",
    "ARCLK", "PETKM", "KOZAL", "HEKTS", "SASA", "EKGYO", "ENKAI", "TAVHL",
    "VESTL", "MGROS", "ULKER", "DOHOL", "TTKOM", "KRDMD", "ALARK", "ASTOR",
    "BRSAN", "CCOLA", "CIMSA", "DOAS", "EGEEN", "GUBRF", "ISMEN", "KONTR",
    "MAVI", "OTKAR", "OYAKC", "SOKM", "TKFEN", "TSKB", "TURSG", "VAKBN",
    "HALKB", "AEFES", "AKSEN", "ALFAS", "ODAS", "ENJSA", "EUPWR", "SMRTG",
]

GUN = {
    "1 ay": 30, "3 ay": 90, "6 ay": 180, "1 yıl": 365,
    "2 yıl": 730, "3 yıl": 1095, "4 yıl": 1460, "5 yıl": 1825,
}


@st.cache_data(ttl=900)
def veri_al(kod):
    return yf.Ticker(kod + ".IS").history(period="max", auto_adjust=False)


secim = st.selectbox("Hisse", HISSELER)
elle = st.text_input("Listede yoksa kodunu yaz (ör: THYAO)")
kod = elle.strip().upper() or secim

sure = st.selectbox("Süre", list(GUN.keys()), index=3)
mum = st.radio("Mum aralığı", ["Günlük", "Haftalık", "Aylık"], horizontal=True)

tum = veri_al(kod)
if tum.empty:
    st.error("Veri bulunamadı. Hisse kodunu kontrol et.")
    st.stop()

son = tum.iloc[-1]
onceki = tum.iloc[-2] if len(tum) > 1 else son
degisim = (son["Close"] / onceki["Close"] - 1) * 100

c1, c2, c3 = st.columns(3)
c1.metric("Son fiyat", f"{son['Close']:.2f} TL", f"{degisim:+.2f}%")
c2.metric("Hacim", f"{int(son['Volume']):,}")
c3.metric("1 yıl en yüksek", f"{tum['High'].tail(252).max():.2f} TL")

d = tum[tum.index >= tum.index.max() - pd.Timedelta(days=GUN[sure])]
if mum != "Günlük":
    kural = "W" if mum == "Haftalık" else "MS"
    d = d.resample(kural).agg(
        {"Open": "first", "High": "max", "Low": "min",
         "Close": "last", "Volume": "sum"}
    ).dropna()

fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                    row_heights=[0.75, 0.25], vertical_spacing=0.03)
fig.add_trace(go.Candlestick(
    x=d.index, open=d["Open"], high=d["High"],
    low=d["Low"], close=d["Close"], name="Fiyat"), row=1, col=1)
fig.add_trace(go.Bar(x=d.index, y=d["Volume"], name="Hacim"), row=2, col=1)
fig.update_layout(height=550, xaxis_rangeslider_visible=False,
                  showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
st.plotly_chart(fig)

st.subheader("Yıllara göre karşılaştırma")
yillik = tum.groupby(tum.index.year).agg(
    {"Open": "first", "High": "max", "Low": "min",
     "Close": "last", "Volume": "sum"})
yillik.columns = ["Açılış", "En yüksek", "En düşük", "Kapanış", "Hacim"]
yillik["Değişim %"] = (yillik["Kapanış"] / yillik["Açılış"] - 1) * 100
yillik.index.name = "Yıl"
st.dataframe(yillik.round(2))
st.bar_chart(yillik["Değişim %"])
