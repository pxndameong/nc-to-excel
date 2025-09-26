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

# Inisialisasi session state untuk menyimpan DataFrame agar bisa diakses oleh tombol Download
if 'processed_df' not in st.session_state:
    st.session_state['processed_df'] = None
if 'selected_var' not in st.session_state:
    st.session_state['selected_var'] = None
if 'selected_export' not in st.session_state:
    st.session_state['selected_export'] = 'All'


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

# 3. Fungsi Download Excel
# Fungsi ini tidak perlu dicache karena hanya menghasilkan output bytes
def convert_to_excel_and_download(df: pd.DataFrame, num_rows: str, var_name: str) -> tuple[bytes, str]:
    """Mengubah DataFrame menjadi file Excel (.xlsx) dengan batasan baris tertentu."""
    
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
st.markdown("Unggah file **NetCDF (.nc)** Anda, lalu gunakan **Sidebar** untuk mengonfigurasi data dan klik **'Tampilkan Pratinjau'**.")

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

            # 3. Pengaturan Ekspor
            st.subheader("Pengaturan Ekspor Excel")
            export_options = ["All", "1000", "10000", "50000"]
            selected_export = st.selectbox(
                "Jumlah Baris Ekspor:",
                export_options,
                index=0, 
                key="sidebar_export_rows",
                help="Pilih jumlah baris yang akan dimasukkan dalam file Excel yang diunduh."
            )
            
            # Tombol "Tampilkan Pratinjau" berada di luar sidebar agar lebih terlihat
            # (Namun, untuk konsistensi, kita tempatkan logika tombolnya di luar block with st.sidebar)


        # --- Tampilan Utama: Tombol Aksi ---
        col_btn_preview, col_btn_download = st.columns([1, 1])

        with col_btn_preview:
            # Tombol untuk memicu pemrosesan data dan menampilkan hasil
            if st.button("Tampilkan Pratinjau", type="primary"):
                # Simpan konfigurasi ke session state saat tombol ditekan
                st.session_state['selected_var'] = selected_var
                st.session_state['selected_export'] = selected_export
                st.session_state['show_preview_clicked'] = True
                # Rerun script untuk menampilkan data
                st.rerun()

        # --- Logika Pemrosesan dan Tampilan Data ---

        # Tampilkan hasil hanya jika tombol 'Tampilkan Pratinjau' sudah ditekan
        if st.session_state.get('show_preview_clicked'):
            
            # Ambil konfigurasi dari session state
            var = st.session_state['selected_var']
            
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
                
                # --- Tampilkan Pratinjau Data ---
                st.subheader("Tabel Pratinjau")
                
                # Tentukan batas pratinjau berdasarkan nilai dari sidebar saat ini
                if selected_preview.lower() == 'all':
                    st.info(f"Menampilkan **SEMUA** {total_rows:,} baris data.")
                    st.dataframe(df, use_container_width=True)
                else:
                    limit = int(selected_preview)
                    st.info(f"Menampilkan **{limit:,}** baris teratas dari data.")
                    st.dataframe(df.head(limit), use_container_width=True)

                # --- Tombol Unduh Excel ---
                st.markdown("---")
                st.subheader("Opsi Unduh")

                # Tombol unduh dipisahkan, hanya muncul setelah pratinjau
                df_to_download = st.session_state['processed_df']
                export_option = st.session_state['selected_export']
                
                excel_data, filename = convert_to_excel_and_download(df_to_download, export_option, var)
                
                # Tampilkan tombol unduh di kolom terpisah
                with col_btn_download:
                    st.download_button(
                        label=f"⬇️ Unduh Excel ({export_option} Baris)",
                        data=excel_data,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="download_excel_final"
                    )

            except Exception as e:
                st.error(f"Terjadi kesalahan saat memproses data variabel '{var}'. Kesalahan: {e}")
                st.session_state['show_preview_clicked'] = False # Reset state on error
        
        # --- Informasi Dataset (Selalu Tampil) ---
        st.markdown("---")
        st.subheader("Informasi Dataset (Metadata)")
        st.code(str(ds), language='text') 

    except Exception as e:
        st.error(f"Gagal memuat file NetCDF. Pastikan file berformat .nc yang valid. Kesalahan: {e}")

# Di luar blok if uploaded_file is not None:
else:
    st.cache_resource.clear()
    # Bersihkan state saat tidak ada file, penting untuk reset
    st.session_state['processed_df'] = None
    st.session_state['selected_var'] = None
    st.session_state['show_preview_clicked'] = False
    st.info("Silakan unggah file NetCDF (.nc) Anda di atas untuk memulai.")