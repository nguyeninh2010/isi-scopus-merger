import streamlit as st
import pandas as pd
import difflib
from io import BytesIO
import bibtexparser

def clean_title(title):
    if pd.isnull(title):
        return ""
    return ''.join(e for e in title.lower().strip() if e.isalnum() or e.isspace())

def read_isi_bib_file(file):
    bib_database = bibtexparser.load(file)
    rows = []
    for entry in bib_database.entries:
        rows.append({
            'Title': entry.get('title', ''),
            'Authors': entry.get('author', ''),
            'Source title': entry.get('journal', ''),
            'Year': entry.get('year', ''),
            'DOI': entry.get('doi', ''),
            'Author Keywords': entry.get('keywords', ''),
            'Affiliations': entry.get('affiliations') or entry.get('affiliation', ''),
            'References': entry.get('cited-references') or entry.get('cited_references') or entry.get('citedreferences', ''),
        })
    return pd.DataFrame(rows)

def map_columns(df, source):
    if source == 'isi':
        return df.rename(columns={
            'Title': 'title', 'Authors': 'authors', 'Source title': 'journal',
            'Year': 'year', 'DOI': 'doi', 'Author Keywords': 'keywords',
            'Affiliations': 'affiliations', 'References': 'references'
        })
    elif source == 'scopus':
        return df.rename(columns={
            'Title': 'title', 'Authors': 'authors', 'Source title': 'journal',
            'Year': 'year', 'DOI': 'doi', 'Author Keywords': 'keywords',
            'Affiliations': 'affiliations', 'References': 'references'
        })
    return df

def merge_datasets(df1, df2):
    df1['title_clean'] = df1['title'].apply(clean_title)
    df2['title_clean'] = df2['title'].apply(clean_title)
    merged = pd.merge(df1, df2, on='doi', how='outer', suffixes=('_isi', '_scopus'))
    no_doi_isi = df1[df1['doi'].isnull()]
    no_doi_scopus = df2[df2['doi'].isnull()]
    for _, row in no_doi_isi.iterrows():
        matches = difflib.get_close_matches(row['title_clean'], no_doi_scopus['title_clean'], n=1, cutoff=0.95)
        if matches:
            matched_row = no_doi_scopus[no_doi_scopus['title_clean'] == matches[0]]
            if not matched_row.empty:
                merged = pd.concat([merged, pd.merge(row.to_frame().T, matched_row, on='title_clean', how='inner', suffixes=('_isi', '_scopus'))])
    return merged.drop(columns='title_clean', errors='ignore')

def convert_df(df):
    buffer = BytesIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue()

# Streamlit UI
st.title("🔗 Kết nối dữ liệu ISI & Scopus")

file1 = st.file_uploader("📄 Chọn file ISI (.bib, .csv, .xlsx)", type=["bib", "csv", "xlsx"])
file2 = st.file_uploader("📄 Chọn file Scopus (.csv, .xlsx)", type=["csv", "xlsx"])

df1, df2 = None, None

if file1:
    try:
        ext = file1.name.split('.')[-1].lower()
        if ext == 'csv':
            df1 = pd.read_csv(file1)
        elif ext == 'xlsx':
            df1 = pd.read_excel(file1)
        elif ext == 'bib':
            df1 = read_isi_bib_file(file1)
        df1 = map_columns(df1, 'isi')
        st.subheader("📘 Dữ liệu từ file ISI")
        st.dataframe(df1.head(10))
    except Exception as e:
        st.error(f"❌ Lỗi xử lý file ISI: {e}")

if file2:
    try:
        ext = file2.name.split('.')[-1].lower()
        if ext == 'csv':
            df2 = pd.read_csv(file2)
        elif ext == 'xlsx':
            df2 = pd.read_excel(file2)
        df2 = map_columns(df2, 'scopus')
        st.subheader("📙 Dữ liệu từ file Scopus")
        st.dataframe(df2.head(10))
    except Exception as e:
        st.error(f"❌ Lỗi xử lý file Scopus: {e}")

if df1 is not None and df2 is not None:
    with st.spinner("🛠️ Đang ghép dữ liệu..."):
        merged = merge_datasets(df1, df2)
    st.success("✅ Ghép dữ liệu hoàn tất!")
    st.dataframe(merged.head(10))
    st.download_button("📥 Tải file kết quả CSV", convert_df(merged), "merged_isi_scopus.csv", "text/csv")
