import pandas as pd
import streamlit as st

OLUMLU = ["yatırım", "ihale", "sözleşme", "sipariş", "anlaşma", "temettü",
          "geri alım", "bedelsiz", "ihracat", "kapasite", "yeni tesis"]
OLUMSUZ = ["zarar", "dava", "ceza", "iptal", "temerrüt", "soruşturma",
           "sermaye azaltım"]


def kucult(s):
    return s.replace("İ", "i").replace("I", "ı").lower()


def sutun_bul(df, isimler):
    for c in df.columns:
        if any(i in str(c).lower() for i in isimler):
            return c
    return None


@st.cache_data(ttl=1800)
def haberleri_al(kod):
    import borsapy as bp
    return bp.Ticker(kod).news


def haber_goster(kod):
    st.subheader("📰 Şirket haberleri (KAP)")
    try:
        df = haberleri_al(kod)
        if df is not None and not isinstance(df, pd.DataFrame):
            df = pd.DataFrame(df)
    except Exception as e:
        st.info(f"Haber alınamadı: {e}")
        return
    if df is None or len(df) == 0:
        st.info("Bu hisse için haber bulunamadı.")
        return

    baslik = sutun_bul(df, ["title", "baslik", "başlık", "subject",
                            "konu", "headline", "summary", "özet"])
    if baslik is None:
        metin = [c for c in df.columns if df[c].dtype == object]
        if metin:
            baslik = max(metin, key=lambda c: df[c].astype(str).str.len().mean())
        else:
            baslik = df.columns[0]
    tarih = sutun_bul(df, ["date", "tarih", "time", "zaman"])
    link = sutun_bul(df, ["url", "link"])

    olumlu = olumsuz = adet = 0
    for _, satir in df.head(15).iterrows():
        adet += 1
        yazi = str(satir[baslik])
        k = kucult(yazi)
        ikon = "⚪"
        if any(a in k for a in OLUMSUZ):
            ikon = "🔴"
            olumsuz += 1
        elif any(a in k for a in OLUMLU):
            ikon = "🟢"
            olumlu += 1
        onek = f"{satir[tarih]} — " if tarih is not None else ""
        if link is not None and str(satir[link]).startswith("http"):
            st.markdown(f"{ikon} {onek}[{yazi}]({satir[link]})")
        else:
            st.markdown(f"{ikon} {onek}{yazi}")

    st.caption(
        f"Son {adet} bildirimde olumlu kelimeli: {olumlu}, olumsuz kelimeli: {olumsuz}. "
        "Bu basit bir kelime taramasıdır, haberi mutlaka kendin oku."
    )
