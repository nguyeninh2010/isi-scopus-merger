import streamlit as st
import pandas as pd
import difflib
from io import BytesIO

def clean_title(title):
    if pd.isnull(title):
        return ""
    return ''.join(e for e in title.lower().strip() if e.isalnum() or e.isspace())

def map_columns(df, source):
    mapping_isi = {'TI': 'title', 'DI': 'doi', 'AU': 'authors', 'SO': 'journal', 'PY': 'year'}
    mapping_scopus = {'Title': 'title', 'DOI': 'doi', 'Authors': 'authors', 'Source title': 'journal', 'Year': 'year'}
    mapping = mapping_isi if source == 'isi' else mapping_scopus
    return df.rename(columns={k: v for k, v in mapping.items() if k in df.columns})

def merge_datasets(df1, df2):
    df1['title_clean'] = df1['title'].apply(clean_title)
    df2['title_clean'] = df2['title'].apply(clean_title)

    merged = pd.merge(df1, df2, on='doi', how='outer', suffixes=('_isi', '_scopus'))

    no_doi_isi = df1[df1['doi'].isnull()]
    no_doi_scopus = df2[df2['doi'].isnull()]
    for idx, row in no_doi_isi.iterrows():
        matches = difflib.get_close_matches(row['title_clean'], no_doi_scopus['title_clean'], n=1, cutoff=0.95)
        if matches:
            match_row = no_doi_scopus[no_doi_scopus['title_clean'] == matches[0]]
            if not match_row.empty:
                merged = pd.concat([merged, pd.merge(row.to_frame().T, match_row, on='title_clean', how='inner', suffixes=('_isi', '_scopus'))])

    merged.drop(columns=['title_clean'], inplace=True, errors='ignore')
    return merged

def convert_df(df):
    output = BytesIO()
    df.to_csv(output, index=False)
    return output.getvalue()

# Streamlit UI
st.title("🔗 Kết nối dữ liệu ISI & Scopus")

file1 = st.file_uploader("Chọn file ISI (.csv, .xlsx)", type=['csv', 'xlsx'])
file2 = st.file_uploader("Chọn file Scopus (.csv, .xlsx)", type=['csv', 'xlsx'])

if file1 and file2:
    ext1 = file1.name.split('.')[-1]
    ext2 = file2.name.split('.')[-1]
    df1 = pd.read_csv(file1) if ext1 == 'csv' else pd.read_excel(file1)
    df2 = pd.read_csv(file2) if ext2 == 'csv' else pd.read_excel(file2)

    df1 = map_columns(df1, source='isi')
    df2 = map_columns(df2, source='scopus')

    with st.spinner("Đang xử lý và ghép dữ liệu..."):
        merged_df = merge_datasets(df1, df2)

    st.success("✅ Ghép dữ liệu hoàn tất!")
    st.write(merged_df.head(50))

    csv = convert_df(merged_df)
    st.download_button(
        label="📥 Tải file kết quả CSV",
        data=csv,
        file_name='merged_isi_scopus.csv',
        mime='text/csv',
    )
