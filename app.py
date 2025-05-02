import streamlit as st
import pandas as pd
import bibtexparser
from io import BytesIO

# Cấu trúc chuẩn
STANDARD_COLUMNS = [
    "TITLE", "AUTHORS", "AUTHOR FULL NAMES", "AFFILIATIONS",
    "AUTHOR KEYWORDS", "REFERENCES", "DOI", "YEAR", "SOURCE TITLE",
    "VOLUME", "ISSUE", "PAGE START", "PAGE END"
]

# Chuyển BibTeX sang cấu trúc Scopus chuẩn
def convert_bibtex_to_standard(bib_data):
    records = []
    for entry in bib_data.entries:
        pages = entry.get("pages", "")
        page_start = pages.split("-")[0] if "-" in pages else ""
        page_end = pages.split("-")[1] if "-" in pages else ""

        record = {
            "TITLE": entry.get("title", ""),
            "AUTHORS": entry.get("author", ""),
            "AUTHOR FULL NAMES": entry.get("author", ""),
            "AFFILIATIONS": entry.get("affiliations", "") or entry.get("affiliation", ""),
            "AUTHOR KEYWORDS": entry.get("keywords", "") or entry.get("keywords-plus", ""),
            "REFERENCES": entry.get("cited-references", ""),
            "DOI": entry.get("doi", ""),
            "YEAR": entry.get("year", ""),
            "SOURCE TITLE": entry.get("journal", ""),
            "VOLUME": entry.get("volume", ""),
            "ISSUE": entry.get("number", ""),
            "PAGE START": page_start,
            "PAGE END": page_end
        }
        records.append(record)
    return pd.DataFrame(records)

# Xử lý Excel/CSV
def read_csv_or_excel(file):
    ext = file.name.split(".")[-1].lower()
    if ext == "csv":
        return pd.read_csv(file)
    elif ext == "xlsx":
        return pd.read_excel(file)
    else:
        return pd.DataFrame()

# Chuẩn hóa tên cột
def normalize_columns(df):
    df.columns = [col.strip().upper() for col in df.columns]
    return df

# Xuất CSV
def convert_df(df):
    buffer = BytesIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue()

# Giao diện
st.title("🔗 Kết nối dữ liệu ISI & Scopus theo chuẩn Scopus/VOSviewer")

isi_file = st.file_uploader("📥 Chọn file ISI (.bib, .csv, .xlsx)", type=["bib", "csv", "xlsx"])
scopus_file = st.file_uploader("📥 Chọn file Scopus (.csv, .xlsx)", type=["csv", "xlsx"])

df_isi, df_scopus = pd.DataFrame(), pd.DataFrame()

# Xử lý ISI
if isi_file:
    try:
        st.subheader("📘 Dữ liệu từ ISI")
        if isi_file.name.endswith(".bib"):
            bib_data = bibtexparser.load(isi_file)
            df_isi = convert_bibtex_to_standard(bib_data)
        else:
            df_isi = read_csv_or_excel(isi_file)
            df_isi = normalize_columns(df_isi)
            df_isi = df_isi.rename(columns={col: col.upper() for col in df_isi.columns})
        st.dataframe(df_isi.head(10))
    except Exception as e:
        st.error(f"Lỗi xử lý ISI: {e}")

# Xử lý Scopus
if scopus_file:
    try:
        st.subheader("📗 Dữ liệu từ Scopus")
        df_scopus = read_csv_or_excel(scopus_file)
        df_scopus = normalize_columns(df_scopus)
        st.dataframe(df_scopus.head(10))
    except Exception as e:
        st.error(f"Lỗi xử lý Scopus: {e}")

# Ghép và chuẩn hóa
if not df_isi.empty and not df_scopus.empty:
    try:
        st.subheader("🔄 Ghép dữ liệu theo DOI (ưu tiên dữ liệu Scopus)")
        df_isi["DOI"] = df_isi["DOI"].str.strip().str.lower()
        df_scopus["DOI"] = df_scopus["DOI"].str.strip().str.lower()

        merged = pd.merge(df_isi, df_scopus, on="DOI", how="outer", suffixes=("_ISI", "_SCOPUS"))

        final_df = pd.DataFrame()
        for col in STANDARD_COLUMNS:
            col_isi = col + "_ISI"
            col_scopus = col + "_SCOPUS"
            if col_scopus in merged.columns or col_isi in merged.columns:
                final_df[col] = merged.get(col_scopus, "").combine_first(merged.get(col_isi, ""))

        st.success("✅ Ghép dữ liệu hoàn tất!")
        st.dataframe(final_df.head(30))

        csv = convert_df(final_df)
        st.download_button("📥 Tải kết quả CSV", csv, file_name="merged_for_vosviewer.csv", mime="text/csv")

    except Exception as e:
        st.error(f"Lỗi ghép dữ liệu: {e}")
