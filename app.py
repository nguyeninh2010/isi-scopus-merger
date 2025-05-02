import streamlit as st
import pandas as pd
import bibtexparser
from io import BytesIO

# Chuẩn hóa dữ liệu .bib theo chuẩn cột Scopus
def convert_bibtex_to_scopus_structure(bib_data):
    records = []
    for entry in bib_data.entries:
        pages = entry.get("pages", "").split("-") if "pages" in entry else ["", ""]
        record = {
            "Title": entry.get("title", ""),
            "Authors": entry.get("author", ""),
            "Author full names": entry.get("author", ""),
            "Affiliations": entry.get("affiliations", "") or entry.get("affiliation", ""),
            "Author Keywords": entry.get("keywords", "") or entry.get("keywords-plus", ""),
            "References": entry.get("cited-references", ""),
            "DOI": entry.get("doi", ""),
            "Year": entry.get("year", ""),
            "Source title": entry.get("journal", ""),
            "Volume": entry.get("volume", ""),
            "Issue": entry.get("number", ""),
            "Page start": pages[0].strip(),
            "Page end": pages[1].strip() if len(pages) > 1 else ""
        }
        records.append(record)
    return pd.DataFrame(records)

# Đọc file Excel hoặc CSV
def convert_excel_or_csv(file):
    ext = file.name.split(".")[-1]
    if ext == "xlsx":
        return pd.read_excel(file)
    elif ext == "csv":
        return pd.read_csv(file)
    else:
        return pd.DataFrame()

# Tạo file CSV tải về
def convert_df(df):
    output = BytesIO()
    df.to_csv(output, index=False)
    return output.getvalue()

# Sắp xếp đúng cột theo chuẩn Scopus
scopus_column_order = [
    "Title", "Authors", "Author full names", "Affiliations",
    "Author Keywords", "References", "DOI", "Year", "Source title",
    "Volume", "Issue", "Page start", "Page end"
]

st.set_page_config(layout="wide")
st.title("📘 Kết nối dữ liệu ISI & Scopus theo chuẩn Scopus")

isi_file = st.file_uploader("📤 Chọn file ISI (.bib, .csv, .xlsx)", type=["bib", "csv", "xlsx"])
scopus_file = st.file_uploader("📤 Chọn file Scopus (.csv, .xlsx)", type=["csv", "xlsx"])

df_isi = pd.DataFrame()
df_scopus = pd.DataFrame()

# Xử lý dữ liệu ISI
if isi_file:
    st.subheader("🔎 Dữ liệu từ file ISI")
    try:
        if isi_file.name.endswith(".bib"):
            bib_data = bibtexparser.load(isi_file)
            df_isi = convert_bibtex_to_scopus_structure(bib_data)
        else:
            df_isi = convert_excel_or_csv(isi_file)

        df_isi = df_isi[[col for col in scopus_column_order if col in df_isi.columns]]
        st.dataframe(df_isi.head(20), use_container_width=True)
    except Exception as e:
        st.error(f"Lỗi khi xử lý file ISI: {e}")

# Xử lý dữ liệu Scopus
if scopus_file:
    st.subheader("🔎 Dữ liệu từ file Scopus")
    try:
        df_scopus = convert_excel_or_csv(scopus_file)
        df_scopus = df_scopus[[col for col in scopus_column_order if col in df_scopus.columns]]
        st.dataframe(df_scopus.head(20), use_container_width=True)
    except Exception as e:
        st.error(f"Lỗi khi xử lý file Scopus: {e}")

# Ghép dữ liệu nếu cả hai đã có
if not df_isi.empty and not df_scopus.empty:
    st.subheader("🔗 Ghép dữ liệu theo DOI")
    try:
        df_isi["DOI"] = df_isi["DOI"].str.lower().str.strip()
        df_scopus["DOI"] = df_scopus["DOI"].str.lower().str.strip()

        merged = pd.merge(df_isi, df_scopus, on="DOI", how="outer", suffixes=("_isi", "_scopus"))
        st.success("✅ Ghép dữ liệu hoàn tất!")
        st.dataframe(merged.head(30), use_container_width=True)

        csv = convert_df(merged)
        st.download_button("📥 Tải file kết quả (CSV)", data=csv, file_name="merged_isi_scopus.csv", mime="text/csv")
    except Exception as e:
        st.error(f"Lỗi khi ghép dữ liệu: {e}")
