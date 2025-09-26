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

# Inisialisasi session state untuk menyimpan DataFrame agar bisa diakses
if 'processed_df' not in st.session_state:
    st.session_state['processed_df'] = None
if 'var_metadata' not in st.session_state: # Untuk menyimpan nama variabel & ekspor
    st.session_state['var_metadata'] = {'var_name': None, 'export_rows': 'All'}
if 'show_preview_clicked' not in st.session_state:
    st.session_state['show_preview_clicked'] = False
if 'preview_configs_changed' not in st.session_state:
    st.session_state['preview_configs_changed'] = True # Set True agar tombol tampil

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

# 3. Fungsi Download Excel (Dipanggil langsung oleh st.download_button)
def convert_to_excel_and_download(df: pd.DataFrame, num_rows: str, var_name: str) -> tuple[bytes, str]:
    """Membuat bytes Excel (dijalankan saat tombol download ditekan)."""
    
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

            # 1. Pemilihan Variabel
            selected_var = st.selectbox(
                "Pilih variabel data:", 
                variables,
                key="sidebar_var_select" 
            )

            # 2. Pengaturan Pratinjau
            st.subheader("Pengaturan Tampilan")
            preview_options = ["10", "50", "100", "500", "All"]
            selected_preview = st.selectbox(
                "Jumlah Baris Pratinjau:",
                preview_options,
                index=0, 
                key="sidebar_preview_rows"
            )

            # 3. Pengaturan Ekspor (Hanya untuk disimpan di state)
            st.subheader("Pengaturan Ekspor Excel")
            export_options = ["All", "1000", "10000", "50000"]
            selected_export = st.selectbox(
                "Jumlah Baris Ekspor:",
                export_options,
                index=0, 
                key="sidebar_export_rows",
                help="Pilih jumlah baris yang akan dimasukkan dalam file Excel yang diunduh."
            )
            
            # Cek jika ada perubahan pada konfigurasi pratinjau
            # Jika variabel atau baris berubah, pratinjau harus di-refresh
            current_config = (selected_var, selected_preview)
            if 'last_preview_config' not in st.session_state or st.session_state['last_preview_config'] != current_config:
                 st.session_state['preview_configs_changed'] = True
                 st.session_state['last_preview_config'] = current_config
            else:
                 st.session_state['preview_configs_changed'] = False
            
            # Logika untuk tombol "Tampilkan Pratinjau"
            if st.button("Tampilkan Pratinjau", type="primary", disabled=st.session_state['show_preview_clicked'] and not st.session_state['preview_configs_changed']):
                st.session_state['var_metadata']['var_name'] = selected_var
                st.session_state['var_metadata']['export_rows'] = selected_export
                st.session_state['show_preview_clicked'] = True
                st.rerun()

        # --- Tampilan Utama Hasil ---
        
        if st.session_state['show_preview_clicked']:
            
            var = st.session_state['var_metadata']['var_name']
            
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
                
                # Gunakan nilai yang terakhir dipilih (saat tombol Pratinjau ditekan)
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
                
                export_option = st.session_state['var_metadata']['export_rows']
                df_to_download = st.session_state['processed_df']
                
                # Tombol unduh diproses sebagai aksi terpisah
                st.download_button(
                    label=f"⬇️ Klik untuk Unduh Data ({export_option} Baris) sebagai XLSX",
                    # Gunakan lambda function untuk menjalankan fungsi pemrosesan saat tombol DITEKAN
                    data=lambda: convert_to_excel_and_download(df_to_download, export_option, var)[0],
                    file_name=lambda: convert_to_excel_and_download(df_to_download, export_option, var)[1],
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
    st.cache_resource.clear()
    # Reset semua state
    st.session_state['processed_df'] = None
    st.session_state['var_metadata'] = {'var_name': None, 'export_rows': 'All'}
    st.session_state['show_preview_clicked'] = False
    st.info("Silakan unggah file NetCDF (.nc) Anda di atas untuk memulai.")