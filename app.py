import streamlit as st
import pandas as pd
import difflib
from io import BytesIO
import bibtexparser

# ---------------------- Xử lý dữ liệu đầu vào ------------------------

def clean_title(title):
    if pd.isnull(title):
        return ""
    return ''.join(e for e in title.lower().strip() if e.isalnum() or e.isspace())

def convert_isi_bibtex_to_scopus(df):
    converted = pd.DataFrame()
    converted["Title"] = df.get("title", "")
    converted["Authors"] = df.get("author", "")
    converted["Source title"] = df.get("journal", "")
    converted["Year"] = df.get("year", "")
    converted["DOI"] = df.get("doi", "")
    converted["Author Keywords"] = df.get("keywords", "")
    converted["Affiliations"] = df.get("institution", df.get("note", ""))
    converted["References"] = ""
    return converted

def merge_datasets(df1, df2):
    df1["title_clean"] = df1["Title"].apply(clean_title)
    df2["title_clean"] = df2["Title"].apply(clean_title)

    merged = pd.merge(df1, df2, on="DOI", how="outer", suffixes=('_isi', '_scopus'))

    no_doi_isi = df1[df1["DOI"].isnull()]
    no_doi_scopus = df2[df2["DOI"].isnull()]
    for _, row in no_doi_isi.iterrows():
        matches = difflib.get_close_matches(row["title_clean"], no_doi_scopus["title_clean"], n=1, cutoff=0.95)
        if matches:
            match_row = no_doi_scopus[no_doi_scopus["title_clean"] == matches[0]]
            if not match_row.empty:
                merged_row = pd.merge(row.to_frame().T, match_row, on="title_clean", how="inner")
                merged = pd.concat([merged, merged_row])

    merged.drop(columns=["title_clean"], inplace=True, errors="ignore")
    return merged

def convert_df_for_export(df):
    # Ưu tiên Scopus, thay thế nếu thiếu bằng ISI
    df["Title"] = df.get("Title_scopus", "").fillna(df.get("Title_isi", ""))
    df["Authors"] = df.get("Authors_scopus", "").fillna(df.get("Authors_isi", ""))
    df["Source title"] = df.get("Source title_scopus", "").fillna(df.get("Source title_isi", ""))
    df["Year"] = df.get("Year_scopus", "").fillna(df.get("Year_isi", ""))
    df["DOI"] = df.get("DOI", "")
    df["Author Keywords"] = df.get("Author Keywords_scopus", "").fillna(df.get("Author Keywords_isi", ""))
    df["Index Keywords"] = df.get("Index Keywords_scopus", "")
    df["Affiliations"] = df.get("Affiliations_scopus", "").fillna(df.get("Affiliations_isi", ""))
    df["References"] = df.get("References_scopus", "").fillna(df.get("References_isi", ""))

    export_df = df[[
        "Title", "Authors", "Source title", "Year", "DOI",
        "Author Keywords", "Index Keywords", "Affiliations", "References"
    ]]

    # ✅ Đảm bảo tên cột chuẩn Scopus, tránh lỗi VOSviewer
    export_df.columns = [
        "Title", "Authors", "Source title", "Year", "DOI",
        "Author Keywords", "Index Keywords", "Affiliations", "References"
    ]

    buffer = BytesIO()
    export_df.to_csv(buffer, index=False)
    return buffer.getvalue()

# ---------------------- Giao diện người dùng ------------------------

st.set_page_config(page_title="Ghép dữ liệu ISI và Scopus", layout="wide")
st.title("🔗 Ứng dụng Ghép Dữ liệu ISI & Scopus (chuẩn Scopus cho VOSviewer)")

file1 = st.file_uploader("📄 Chọn file ISI (.bib, .csv, .xlsx)", type=["bib", "csv", "xlsx"])
file2 = st.file_uploader("📄 Chọn file Scopus (.csv, .xlsx)", type=["csv", "xlsx"])

if file1 and file2:
    try:
        # Xử lý ISI
        ext1 = file1.name.split(".")[-1].lower()
        if ext1 == "bib":
            bib_data = bibtexparser.load(file1)
            isi_raw_df = pd.DataFrame(bib_data.entries)
            isi_df = convert_isi_bibtex_to_scopus(isi_raw_df)
        elif ext1 == "csv":
            isi_raw_df = pd.read_csv(file1)
            isi_df = convert_isi_bibtex_to_scopus(isi_raw_df)
        elif ext1 == "xlsx":
            isi_raw_df = pd.read_excel(file1)
            isi_df = convert_isi_bibtex_to_scopus(isi_raw_df)
        else:
            st.error("❌ Định dạng file ISI không hợp lệ.")
            st.stop()

        # Xử lý Scopus
        ext2 = file2.name.split(".")[-1].lower()
        if ext2 == "csv":
            scopus_df = pd.read_csv(file2)
        elif ext2 == "xlsx":
            scopus_df = pd.read_excel(file2)
        else:
            st.error("❌ Định dạng file Scopus không hợp lệ.")
            st.stop()

        scopus_df.columns = scopus_df.columns.str.strip()

        # Cảnh báo thiếu cột
        required = ["Title", "Authors", "DOI"]
        warnings = []
        for col in required:
            if col not in isi_df.columns or isi_df[col].isnull().all():
                warnings.append(f"📁 ISI thiếu hoặc trống: `{col}`")
            if col not in scopus_df.columns or scopus_df[col].isnull().all():
                warnings.append(f"📁 Scopus thiếu hoặc trống: `{col}`")

        if warnings:
            st.warning("⚠️ Một số trường dữ liệu bị thiếu:")
            for w in warnings:
                st.markdown(f"- {w}")

        with st.spinner("🔄 Đang xử lý và ghép dữ liệu..."):
            merged_df = merge_datasets(isi_df, scopus_df)

        st.success("✅ Ghép dữ liệu hoàn tất!")
        st.dataframe(merged_df.head(50), use_container_width=True)

        # Kiểm tra số lượng tác giả
        all_authors = merged_df.get("Authors_scopus", "").fillna(merged_df.get("Authors_isi", "")).dropna()
        if all_authors.nunique() < 3:
            st.error("❌ Dữ liệu cần ít nhất 3 tác giả khác nhau để dùng với VOSviewer.")
        else:
            csv = convert_df_for_export(merged_df)
            st.download_button("📥 Tải xuống CSV chuẩn Scopus", data=csv, file_name="merged_scopus.csv", mime="text/csv")

    except Exception as e:
        st.error(f"❌ Đã xảy ra lỗi: {e}")
