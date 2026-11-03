import re
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Borsa Takip", layout="wide")
st.title("📈 Borsa Takip")

YEDEK = [
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


@st.cache_data(ttl=86400)
def hisse_listesi():
    try:
        import borsapy as bp
        df = bp.companies()
        kaynak = next(
            (df[c] for c in df.columns
             if str(c).lower() in ("ticker", "symbol", "code", "kod", "sembol")),
            None,
        )
        if kaynak is None:
            if isinstance(df.index, pd.RangeIndex):
                kaynak = df.iloc[:, 0]
            else:
                kaynak = df.index.to_series()
        kodlar = sorted({
            str(x).strip().upper() for x in kaynak
            if re.fullmatch(r"[A-Z0-9]{3,6}", str(x).strip().upper())
        })
        if len(kodlar) > 100:
            return kodlar, "tüm BIST"
    except Exception:
        pass
    return sorted(YEDEK), "yedek liste"


@st.cache_data(ttl=900)
def veri_al(kod):
    return yf.Ticker(kod + ".IS").history(period="max", auto_adjust=False)


def rsi_hesapla(kapanis, periyot=14):
    fark = kapanis.diff()
    kazanc = fark.clip(lower=0).ewm(alpha=1 / periyot, adjust=False).mean()
    kayip = (-fark.clip(upper=0)).ewm(alpha=1 / periyot, adjust=False).mean()
    return 100 - 100 / (1 + kazanc / kayip)


def yorum_uret(df):
    kap = df["Close"].dropna()
    if len(kap) < 60:
        return None, ["Yorum için yeterli geçmiş veri yok."]
    puan = 0
    notlar = []
    fiyat = kap.iloc[-1]

    sma20 = kap.rolling(20).mean().iloc[-1]
    sma50 = kap.rolling(50).mean().iloc[-1]

    if fiyat > sma50:
        puan += 1
        notlar.append(f"Fiyat 50 günlük ortalamanın ({sma50:.2f}) üstünde → olumlu")
    else:
        puan -= 1
        notlar.append(f"Fiyat 50 günlük ortalamanın ({sma50:.2f}) altında → olumsuz")

    if sma20 > sma50:
        puan += 1
        notlar.append("20 günlük ortalama 50 günlüğün üstünde → olumlu")
    else:
        puan -= 1
        notlar.append("20 günlük ortalama 50 günlüğün altında → olumsuz")

    if len(kap) >= 200:
        sma200 = kap.rolling(200).mean().iloc[-1]
        if fiyat > sma200:
            puan += 1
            notlar.append(f"Fiyat 200 günlük ortalamanın ({sma200:.2f}) üstünde → olumlu")
        else:
            puan -= 1
            notlar.append(f"Fiyat 200 günlük ortalamanın ({sma200:.2f}) altında → olumsuz")

    rsi = rsi_hesapla(kap).iloc[-1]
    if pd.notna(rsi):
        if rsi >= 70:
            puan -= 1
            notlar.append(f"RSI {rsi:.0f}: aşırı alım bölgesi, geri çekilme riski → olumsuz")
        elif rsi <= 30:
            puan += 1
            notlar.append(f"RSI {rsi:.0f}: aşırı satım bölgesi, tepki gelebilir → olumlu")
        else:
            notlar.append(f"RSI {rsi:.0f}: nötr bölge")

    ay = (fiyat / kap.iloc[-22] - 1) * 100
    if ay > 5:
        puan += 1
        notlar.append(f"Son 1 ayda %{ay:+.1f} → olumlu")
    elif ay < -5:
        puan -= 1
        notlar.append(f"Son 1 ayda %{ay:+.1f} → olumsuz")
    else:
        notlar.append(f"Son 1 ayda %{ay:+.1f}: yatay")

    hac = df["Volume"]
    h5 = hac.tail(5).mean()
    h20 = hac.tail(20).mean()
    if h20 > 0 and h5 > 1.5 * h20:
        notlar.append("Son 5 günde hacim 20 günlük ortalamanın %50'den fazla üstünde → hareket güçlü")

    return puan, notlar


HISSELER, KAYNAK = hisse_listesi()
st.caption(f"{len(HISSELER)} hisse yüklendi ({KAYNAK})")

varsayilan = HISSELER.index("THYAO") if "THYAO" in HISSELER else 0
secim = st.selectbox("Hisse (yazarak arayabilirsin)", HISSELER, index=varsayilan)
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

st.subheader("Teknik yorum")
puan, notlar = yorum_uret(tum)
if puan is None:
    st.info(notlar[0])
else:
    if puan >= 2:
        st.success(f"📈 Yükseliş eğilimi (puan {puan:+d})")
    elif puan <= -2:
        st.error(f"📉 Düşüş eğilimi (puan {puan:+d})")
    else:
        st.warning(f"➖ Belirsiz / yatay (puan {puan:+d})")
    for n in notlar:
        st.write("• " + n)
st.caption(
    "Otomatik teknik analizdir, yatırım tavsiyesi değildir. "
    "Geçmiş verilere dayanır, geleceği garanti etmez."
)

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
