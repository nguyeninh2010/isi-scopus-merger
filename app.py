import streamlit as st
import pandas as pd
import bibtexparser
from io import BytesIO

st.set_page_config(layout="wide")

# ========== Utility functions ==========

def safe_get_series(df, col):
    return df[col] if col in df.columns else pd.Series([None] * len(df))

def convert_isi_bibtex_to_scopus(df):
    converted = pd.DataFrame()
    converted["Title"] = safe_get_series(df, "Title").fillna("")
    converted["Authors"] = safe_get_series(df, "Author").fillna("")
    converted["Source title"] = safe_get_series(df, "Journal").fillna("")
    converted["Year"] = safe_get_series(df, "Year").fillna("")
    converted["DOI"] = safe_get_series(df, "DOI").fillna("")
    converted["Author Keywords"] = (
        safe_get_series(df, "Keywords")
        .combine_first(safe_get_series(df, "Author Keywords"))
        .fillna("")
    )
    converted["Affiliations"] = (
        safe_get_series(df, "Affiliations")
        .combine_first(safe_get_series(df, "Affiliation"))
        .combine_first(safe_get_series(df, "Affiliation Address"))
        .combine_first(safe_get_series(df, "Address"))
        .fillna("")
    )
    converted["References"] = (
        safe_get_series(df, "Cited-References")
        .combine_first(safe_get_series(df, "references"))
        .combine_first(safe_get_series(df, "annote"))
        .combine_first(safe_get_series(df, "note"))
        .combine_first(safe_get_series(df, "review"))
        .combine_first(safe_get_series(df, "misc"))
        .fillna("")
    )
    return converted

def read_uploaded_file(file):
    ext = file.name.split('.')[-1].lower()
    if ext == 'csv':
        return pd.read_csv(file)
    elif ext in ['xlsx', 'xls']:
        return pd.read_excel(file)
    elif ext == 'bib':
        try:
            bib_database = bibtexparser.load(file)
            return pd.DataFrame(bib_database.entries)
        except Exception as e:
            st.error(f"❌ Không thể đọc file .bib: {e}")
            return pd.DataFrame()
    else:
        st.error("❌ Định dạng file không hợp lệ.")
        return pd.DataFrame()

# ========== Main App ==========

st.title("📚 Công cụ kết hợp dữ liệu ISI và Scopus cho VOSviewer")

isi_file = st.file_uploader("📄 Chọn file ISI (.bib, .csv, .xlsx)", type=['bib', 'csv', 'xlsx'])
scopus_file = st.file_uploader("📄 Chọn file Scopus (.csv, .xlsx)", type=['csv', 'xlsx'])

df_isi = pd.DataFrame()
df_scopus = pd.DataFrame()

if isi_file:
    df_isi_raw = read_uploaded_file(isi_file)
    if not df_isi_raw.empty:
        df_isi = convert_isi_bibtex_to_scopus(df_isi_raw)
        st.subheader("📑 Dữ liệu từ file ISI")
        st.dataframe(df_isi)

if scopus_file:
    df_scopus = read_uploaded_file(scopus_file)
    if not df_scopus.empty:
        st.subheader("📑 Dữ liệu từ file Scopus")
        st.dataframe(df_scopus)

# Merge
if not df_isi.empty and not df_scopus.empty:
    merged = pd.concat([df_isi, df_scopus], ignore_index=True)
    st.success("✅ Ghép dữ liệu hoàn tất!")
    st.dataframe(merged)

    # Download
    buffer = BytesIO()
    merged.to_csv(buffer, index=False)
    st.download_button(
        label="📥 Tải xuống kết quả",
        data=buffer.getvalue(),
        file_name="merged_for_vosviewer.csv",
        mime="text/csv"
    )
