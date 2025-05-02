import streamlit as st
import pandas as pd
import bibtexparser
from io import BytesIO

# Định nghĩa cột chuẩn theo Scopus
SCOPUS_COLUMNS = [
    "Title", "Authors", "Author full names", "Affiliations", "Author Keywords",
    "References", "DOI", "Year", "Source title", "Volume", "Issue", "Page start", "Page end"
]

def convert_bibtex_to_scopus_structure(bib_data):
    records = []
    for entry in bib_data.entries:
        pages = entry.get("pages", "")
        page_start, page_end = "", ""
        if "-" in pages:
            parts = pages.split("-")
            page_start = parts[0].strip()
            page_end = parts[-1].strip()
        record = {
            "Title": entry.get("title", ""),
            "Authors": entry.get("author", ""),
            "Author full names": entry.get("author", ""),
            "Affiliations": entry.get("affiliations", ""),
            "Author Keywords": entry.get("keywords", "") or entry.get("keywords-plus", ""),
            "References": entry.get("cited-references", ""),
            "DOI": entry.get("doi", ""),
            "Year": entry.get("year", ""),
            "Source title": entry.get("journal", ""),
            "Volume": entry.get("volume", ""),
            "Issue": entry.get("number", ""),
            "Page start": page_start,
            "Page end": page_end
        }
        records.append(record)
    return pd.DataFrame(records)

def convert_excel_or_csv(file):
    ext = file.name.split(".")[-1].lower()
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

st.set_page_config(page_title="Kết nối dữ liệu ISI & Scopus", layout="wide")
st.title("📘 Kết nối dữ liệu ISI & Scopus theo chuẩn Scopus")

isi_file = st.file_uploader("📤 Chọn file ISI (.bib, .csv, .xlsx)", type=["bib", "csv", "xlsx"])
scopus_file = st.file_uploader("📤 Chọn file Scopus (.csv, .xlsx)", type=["csv", "xlsx"])

df_isi = pd.DataFrame()
df_scopus = pd.DataFrame()

if isi_file:
    st.subheader("🔎 Dữ liệu từ file ISI")
    try:
        if isi_file.name.endswith(".bib"):
            bib_data = bibtexparser.load(isi_file)
            df_isi = convert_bibtex_to_scopus_structure(bib_data)
        else:
            df_isi = convert_excel_or_csv(isi_file)
        st.dataframe(df_isi.head(5))
    except Exception as e:
        st.error(f"Lỗi khi xử lý file ISI: {e}")

if scopus_file:
    st.subheader("🔎 Dữ liệu từ file Scopus")
    try:
        df_scopus = convert_excel_or_csv(scopus_file)
        st.dataframe(df_scopus.head(5))
    except Exception as e:
        st.error(f"Lỗi khi xử lý file Scopus: {e}")

if not df_isi.empty and not df_scopus.empty:
    st.subheader("🔗 Ghép dữ liệu theo DOI")
    try:
        df_isi["DOI"] = df_isi["DOI"].str.lower().str.strip()
        df_scopus["DOI"] = df_scopus["DOI"].str.lower().str.strip()

        merged = pd.merge(df_isi, df_scopus, on="DOI", how="outer", suffixes=('_isi', '_scopus'))

        # Ưu tiên giữ các cột từ Scopus (nếu có), hoặc từ ISI nếu không có
        for col in SCOPUS_COLUMNS:
            col_scopus = col + "_scopus"
            col_isi = col + "_isi"
            if col in merged.columns:
                continue
            elif col_scopus in merged.columns and col_isi in merged.columns:
                merged[col] = merged[col_scopus].combine_first(merged[col_isi])
                merged.drop([col_scopus, col_isi], axis=1, inplace=True)
            elif col_scopus in merged.columns:
                merged.rename(columns={col_scopus: col}, inplace=True)
            elif col_isi in merged.columns:
                merged.rename(columns={col_isi: col}, inplace=True)

        # Loại bỏ các cột phụ còn sót lại
        merged = merged[[col for col in SCOPUS_COLUMNS if col in merged.columns]]

        st.success("✅ Ghép dữ liệu hoàn tất!")
        st.dataframe(merged.head(30))

        csv = convert_df(merged)
        st.download_button("📥 Tải file kết quả (CSV)", data=csv, file_name="merged_isi_scopus.csv", mime="text/csv")
    except Exception as e:
        st.error(f"Lỗi khi ghép dữ liệu: {e}")
