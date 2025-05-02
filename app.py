import streamlit as st
import pandas as pd
import bibtexparser
from io import BytesIO

# ======= CHUẨN HÓA CỘT THEO SCOPUS =======
SCOPUS_COLUMNS = [
    "Title", "Authors", "Author full names", "Affiliations", "Author Keywords",
    "References", "DOI", "Year", "Source title", "Volume", "Issue", "Page start", "Page end"
]

def convert_bibtex_to_scopus_structure(bib_data):
    records = []
    for entry in bib_data.entries:
        pages = entry.get("pages", "")
        page_start = page_end = ""
        if "-" in pages:
            page_start, page_end = pages.split("-", 1)
        elif pages:
            page_start = page_end = pages

        record = {
            "Title": entry.get("title", ""),
            "Authors": entry.get("author", ""),
            "Author full names": entry.get("author", ""),
            "Affiliations": entry.get("affiliations", "") or entry.get("affiliation", ""),
            "Author Keywords": entry.get("keywords", "") or entry.get("keywords-plus", ""),
            "References": entry.get("cited-references", "") or entry.get("references", ""),
            "DOI": entry.get("doi", ""),
            "Year": entry.get("year", ""),
            "Source title": entry.get("journal", ""),
            "Volume": entry.get("volume", ""),
            "Issue": entry.get("number", ""),
            "Page start": page_start.strip(),
            "Page end": page_end.strip()
        }
        records.append(record)
    df = pd.DataFrame(records)
    return df[SCOPUS_COLUMNS]

def convert_excel_or_csv(file):
    ext = file.name.split(".")[-1]
    if ext == "xlsx":
        return pd.read_excel(file)
    elif ext == "csv":
        return pd.read_csv(file)
    else:
        return pd.DataFrame()

def convert_df(df):
    output = BytesIO()
    df.to_csv(output, index=False)
    return output.getvalue()

# ======= GIAO DIỆN STREAMLIT =======
st.set_page_config(page_title="Kết nối dữ liệu ISI & Scopus", layout="wide")
st.title("📘 Kết nối dữ liệu ISI & Scopus (chuẩn Scopus - dùng cho VOSviewer)")

isi_file = st.file_uploader("📤 Chọn file ISI (.bib, .csv, .xlsx)", type=["bib", "csv", "xlsx"])
scopus_file = st.file_uploader("📤 Chọn file Scopus (.csv, .xlsx)", type=["csv", "xlsx"])

df_isi = pd.DataFrame()
df_scopus = pd.DataFrame()

if isi_file:
    st.subheader("📄 Dữ liệu từ file ISI")
    try:
        if isi_file.name.endswith(".bib"):
            bib_data = bibtexparser.load(isi_file)
            df_isi = convert_bibtex_to_scopus_structure(bib_data)
        else:
            df_isi = convert_excel_or_csv(isi_file)
        st.dataframe(df_isi.head(5), use_container_width=True)
    except Exception as e:
        st.error(f"❌ Lỗi khi xử lý file ISI: {e}")

if scopus_file:
    st.subheader("📄 Dữ liệu từ file Scopus")
    try:
        df_scopus = convert_excel_or_csv(scopus_file)
        st.dataframe(df_scopus.head(5), use_container_width=True)
    except Exception as e:
        st.error(f"❌ Lỗi khi xử lý file Scopus: {e}")

if not df_isi.empty and not df_scopus.empty:
    st.subheader("🔗 Ghép dữ liệu theo DOI")
    try:
        df_isi["DOI"] = df_isi["DOI"].str.lower().str.strip()
        df_scopus["DOI"] = df_scopus["DOI"].astype(str).str.lower().str.strip()

        merged = pd.merge(df_isi, df_scopus, on="DOI", how="outer")

        # Loại bỏ các cột trùng hoặc _dup
        merged = merged.loc[:, ~merged.columns.duplicated()]
        merged = merged[SCOPUS_COLUMNS] if all(col in merged.columns for col in SCOPUS_COLUMNS) else merged

        st.success("✅ Ghép dữ liệu hoàn tất!")
        st.dataframe(merged.head(20), use_container_width=True)

        csv = convert_df(merged)
        st.download_button(
            "📥 Tải file kết quả (CSV chuẩn Scopus)",
            data=csv,
            file_name="merged_isi_scopus.csv",
            mime="text/csv"
        )
    except Exception as e:
        st.error(f"❌ Lỗi khi ghép dữ liệu: {e}")
