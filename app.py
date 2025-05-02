import streamlit as st
import pandas as pd
import difflib
from io import BytesIO
import bibtexparser

def clean_title(title):
    if pd.isnull(title):
        return ""
    return ''.join(e for e in title.lower().strip() if e.isalnum() or e.isspace())

def map_columns(df, source):
    mapping_isi = {
        'TI': 'title', 'DI': 'doi', 'AU': 'authors', 'SO': 'journal', 'PY': 'year',
        'DE': 'author_keywords', 'ID': 'index_keywords', 'C1': 'affiliations', 'CR': 'references'
    }
    mapping_scopus = {
        'Title': 'title', 'DOI': 'doi', 'Authors': 'authors', 'Source title': 'journal', 'Year': 'year',
        'Author Keywords': 'author_keywords', 'Index Keywords': 'index_keywords',
        'Affiliations': 'affiliations', 'References': 'references'
    }
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
                merged_row = pd.merge(
                    row.to_frame().T,
                    match_row,
                    on='title_clean',
                    how='inner',
                    suffixes=('_isi', '_scopus')
                )
                merged = pd.concat([merged, merged_row])

    merged.drop(columns=['title_clean'], inplace=True, errors='ignore')
    return merged

def convert_df(df, output_format='scopus'):
    if output_format == 'scopus':
        columns_to_keep = [
            'title_scopus', 'authors_scopus', 'journal_scopus', 'year_scopus', 'doi',
            'author_keywords_scopus', 'index_keywords_scopus', 'affiliations_scopus', 'references_scopus'
        ]
        rename_map = {
            'title_scopus': 'Title',
            'authors_scopus': 'Authors',
            'journal_scopus': 'Source title',
            'year_scopus': 'Year',
            'doi': 'DOI',
            'author_keywords_scopus': 'Author Keywords',
            'index_keywords_scopus': 'Index Keywords',
            'affiliations_scopus': 'Affiliations',
            'references_scopus': 'References'
        }
    else:
        columns_to_keep = [
            'title_isi', 'authors_isi', 'journal_isi', 'year_isi', 'doi',
            'author_keywords_isi', 'index_keywords_isi', 'affiliations_isi', 'references_isi'
        ]
        rename_map = {
            'title_isi': 'TI',
            'authors_isi': 'AU',
            'journal_isi': 'SO',
            'year_isi': 'PY',
            'doi': 'DI',
            'author_keywords_isi': 'DE',
            'index_keywords_isi': 'ID',
            'affiliations_isi': 'C1',
            'references_isi': 'CR'
        }

    # Bổ sung các cột trống nếu thiếu
    for col in columns_to_keep:
        if col not in df.columns:
            df[col] = ""

    export_df = df[columns_to_keep].rename(columns=rename_map)
    output = BytesIO()
    export_df.to_csv(output, index=False)
    return output.getvalue()

# ---------------- Streamlit UI ----------------

st.set_page_config(page_title="Ghép dữ liệu ISI & Scopus", layout="wide")
st.title("🔗 Kết nối dữ liệu ISI & Scopus")

file1 = st.file_uploader("📄 Chọn file ISI (.csv, .xlsx, .bib)", type=['csv', 'xlsx', 'bib'])
file2 = st.file_uploader("📄 Chọn file Scopus (.csv, .xlsx)", type=['csv', 'xlsx'])

if file1 and file2:
    ext1 = file1.name.split('.')[-1].lower()
    ext2 = file2.name.split('.')[-1].lower()

    try:
        if ext1 == 'csv':
            df1 = pd.read_csv(file1)
        elif ext1 == 'xlsx':
            df1 = pd.read_excel(file1)
        elif ext1 == 'bib':
            bib_data = bibtexparser.load(file1)
            records = bib_data.entries
            df1 = pd.DataFrame(records)
        else:
            st.error("❌ Định dạng file ISI không hợp lệ.")
            st.stop()

        if ext2 == 'csv':
            df2 = pd.read_csv(file2)
        elif ext2 == 'xlsx':
            df2 = pd.read_excel(file2)
        else:
            st.error("❌ Định dạng file Scopus không hợp lệ.")
            st.stop()

        df1.columns = df1.columns.str.strip()
        df2.columns = df2.columns.str.strip()

        df1 = map_columns(df1, source='isi')
        df2 = map_columns(df2, source='scopus')

        with st.spinner("⏳ Đang xử lý và ghép dữ liệu..."):
            merged_df = merge_datasets(df1, df2)

        st.success("✅ Ghép dữ liệu hoàn tất!")
        st.dataframe(merged_df.head(50), use_container_width=True)

        output_format = st.radio(
            "📤 Chọn cấu trúc dữ liệu đầu ra phù hợp với VOSviewer:",
            ('scopus', 'isi'),
            format_func=lambda x: "Chuẩn Scopus" if x == 'scopus' else "Chuẩn ISI"
        )

        csv = convert_df(merged_df, output_format=output_format)
        st.download_button(
            label="📥 Tải file kết quả CSV",
            data=csv,
            file_name=f'merged_{output_format}.csv',
            mime='text/csv',
        )
    except Exception as e:
        st.error(f"❌ Đã xảy ra lỗi khi xử lý: {str(e)}")
