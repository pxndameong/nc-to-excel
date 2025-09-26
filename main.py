import streamlit as st
import xarray as xr
import pandas as pd
from io import BytesIO

# ====================================================================
# A. KONFIGURASI DAN FUNGSI CACHING
# ====================================================================

# Set konfigurasi halaman Streamlit
st.set_page_config(
    page_title="NC File Viewer",
    layout="wide" 
)

# Inisialisasi session state
for key, default in [
    ('processed_df', None),
    ('var_metadata', {'var_name': None, 'export_rows': 'All'}),
    ('show_preview_clicked', False),
    ('preview_configs_changed', True)
]:
    if key not in st.session_state:
        st.session_state[key] = default


# 1. Fungsi Caching untuk Dataset (Resource)
@st.cache_resource(show_spinner="Memuat file NetCDF...")
def load_netcdf_file(file_bytes: bytes) -> xr.Dataset:
    """Memuat file NetCDF menggunakan st.cache_resource."""
    with xr.open_dataset(BytesIO(file_bytes)) as ds:
        return ds.load() 

# 2. Fungsi Caching untuk Konversi ke DataFrame (Data)
@st.cache_data(show_spinner="Mempersiapkan data variabel...")
def convert_to_dataframe(var_name: str, _data_array: xr.DataArray) -> pd.DataFrame:
    """Mengubah xarray.DataArray menjadi Pandas DataFrame. 'var_name' sebagai kunci cache."""
    _data_array.load() 
    df = _data_array.to_dataframe().reset_index()
    return df

# 3. Fungsi Download Excel (Helper function untuk dipanggil oleh st.download_button)
def get_excel_download_bytes():
    """Mengambil DataFrame dari state dan memprosesnya menjadi bytes Excel."""
    df = st.session_state['processed_df']
    var_name = st.session_state['var_metadata']['var_name']
    export_option = st.session_state['var_metadata']['export_rows']
    
    # Gunakan fungsi pembuat Excel yang sudah ada
    excel_bytes, filename = convert_to_excel_and_download(df, export_option, var_name)
    
    # st.download_button membutuhkan data (bytes) dan nama file (string)
    # Kita hanya mengembalikan data bytes di sini, karena file_name akan dikembalikan di argumen terpisah
    return excel_bytes 

def convert_to_excel_and_download(df: pd.DataFrame, num_rows: str, var_name: str) -> tuple[bytes, str]:
    """Membuat bytes Excel."""
    
    if num_rows.lower() == 'all':
        df_export = df
        suffix = "ALL"
    else:
        try:
            limit = int(num_rows) 
            df_export = df.head(limit)
            suffix = f"Top{limit}"
        except ValueError:
            df_export = df.head(100)
            suffix = "Top100"

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_export.to_excel(writer, index=False, sheet_name=var_name)
    
    processed_data = output.getvalue()
    return processed_data, f"{var_name}_{suffix}.xlsx"

# ====================================================================
# B. APLIKASI STREAMLIT UTAMA
# ====================================================================

st.title("NC File Viewer 🔎")
st.markdown("Unggah file **NetCDF (.nc)**, konfigurasikan di **Sidebar**, lalu klik **'Tampilkan Pratinjau'** sebelum mengunduh.")

# --- Unggah File ---
uploaded_file = st.file_uploader("Pilih file NetCDF (.nc)", type="nc")

if uploaded_file is not None:
    
    file_bytes = uploaded_file.getvalue()
    
    try:
        ds = load_netcdf_file(file_bytes)
        
        # --- Sidebar Konfigurasi ---
        with st.sidebar:
            st.header("⚙️ Konfigurasi Data")
            
            variables = list(ds.data_vars.keys())
            if not variables:
                st.warning("Dataset tidak memiliki variabel data yang dapat ditampilkan.")
                st.stop()

            selected_var = st.selectbox(
                "Pilih variabel data:", 
                variables,
                key="sidebar_var_select" 
            )

            st.subheader("Pengaturan Tampilan")
            preview_options = ["10", "50", "100", "500", "All"]
            selected_preview = st.selectbox(
                "Jumlah Baris Pratinjau:",
                preview_options,
                index=0, 
                key="sidebar_preview_rows"
            )

            st.subheader("Pengaturan Ekspor Excel")
            export_options = ["All", "1000", "10000", "50000"]
            selected_export = st.selectbox(
                "Jumlah Baris Ekspor:",
                export_options,
                index=0, 
                key="sidebar_export_rows",
                help="Pilih jumlah baris yang akan dimasukkan dalam file Excel yang diunduh."
            )
            
            # Cek jika ada perubahan pada konfigurasi
            current_config = (selected_var, selected_preview, selected_export)
            if 'last_config' not in st.session_state or st.session_state['last_config'] != current_config:
                 st.session_state['preview_configs_changed'] = True
                 st.session_state['last_config'] = current_config
            else:
                 st.session_state['preview_configs_changed'] = False
            
            # Tombol Tampilkan Pratinjau
            if st.button("Tampilkan Pratinjau", type="primary", disabled=st.session_state['show_preview_clicked'] and not st.session_state['preview_configs_changed']):
                st.session_state['var_metadata']['var_name'] = selected_var
                st.session_state['var_metadata']['export_rows'] = selected_export
                st.session_state['show_preview_clicked'] = True
                st.rerun()

        # --- Tampilan Utama Hasil ---
        
        if st.session_state['show_preview_clicked']:
            
            var = st.session_state['var_metadata']['var_name']
            export_option = st.session_state['var_metadata']['export_rows']
            
            st.subheader(f"Hasil Konfigurasi Data: `{var}`")
            
            try:
                # 1. Konversi Data ke DataFrame (sekali berkat caching)
                data_array = ds[var]
                df = convert_to_dataframe(var, data_array) 
                st.session_state['processed_df'] = df # Simpan DataFrame di state
                total_rows = len(df)

                # --- Informasi & Statistik ---
                col_info, col_stat = st.columns([1, 2])
                
                with col_info:
                    st.metric(label="Total Baris Data", value=f"{total_rows:,}")
                
                with col_stat:
                    st.markdown(f"**Statistik Deskriptif ({var}):**")
                    st.dataframe(df[var].describe().to_frame().T, use_container_width=True)

                st.markdown("---")
                
                # --- Tampilkan Tabel Pratinjau ---
                st.subheader("Tabel Pratinjau")
                
                if selected_preview.lower() == 'all':
                    st.info(f"Menampilkan **SEMUA** {total_rows:,} baris data.")
                    st.dataframe(df, use_container_width=True)
                else:
                    limit = int(selected_preview)
                    st.info(f"Menampilkan **{limit:,}** baris teratas dari data.")
                    st.dataframe(df.head(limit), use_container_width=True)

                # --- Tombol Unduh Excel ---
                st.markdown("---")
                st.subheader("Opsi Unduh Excel")
                
                # Mendapatkan nama file yang benar untuk tombol unduh
                _, filename = convert_to_excel_and_download(df, export_option, var)
                
                # PENTING: Menggunakan fungsi pembantu (get_excel_download_bytes) yang sudah disederhanakan
                st.download_button(
                    label=f"⬇️ Unduh Data '{var}' ({export_option} Baris) sebagai XLSX",
                    data=get_excel_download_bytes, # Panggil fungsi tanpa () untuk mendapatkan callable
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_excel_final"
                )

            except Exception as e:
                st.error(f"Terjadi kesalahan saat memproses data variabel '{var}'. Kesalahan: {e}")
                st.session_state['show_preview_clicked'] = False
        
        # --- Informasi Dataset (Selalu Tampil) ---
        st.markdown("---")
        st.subheader("Informasi Dataset (Metadata)")
        st.code(str(ds), language='text') 

    except Exception as e:
        st.error(f"Gagal memuat file NetCDF. Pastikan file berformat .nc yang valid. Kesalahan: {e}")

# Di luar blok if uploaded_file is not None:
else:
    # Reset semua state saat tidak ada file
    st.cache_resource.clear()
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.info("Silakan unggah file NetCDF (.nc) Anda di atas untuk memulai.")