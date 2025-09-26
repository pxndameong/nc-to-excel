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

# 1. Fungsi Caching untuk Dataset (Resource)
@st.cache_resource(show_spinner="Memuat file NetCDF...")
def load_netcdf_file(file_bytes: bytes) -> xr.Dataset:
    """
    Memuat file NetCDF menggunakan xarray.open_dataset dari bytes file.
    Menggunakan st.cache_resource untuk objek xarray.Dataset yang kompleks.
    """
    with xr.open_dataset(BytesIO(file_bytes)) as ds:
        # PENTING: Gunakan .load() untuk memastikan data ditarik ke memori.
        return ds.load() 

# 2. Fungsi Caching untuk Konversi ke DataFrame (Data)
@st.cache_data(show_spinner="Mempersiapkan data variabel...")
def convert_to_dataframe(var_name: str, _data_array: xr.DataArray) -> pd.DataFrame:
    """
    Mengubah xarray.DataArray menjadi Pandas DataFrame.
    'var_name' adalah kunci caching yang andal.
    '_data_array' diabaikan dari hashing untuk mencegah error.
    """
    # Muat DataArray secara eksplisit sebelum konversi
    _data_array.load() 
    
    # Konversi ke DataFrame dan reset index (koordinat menjadi kolom)
    df = _data_array.to_dataframe().reset_index()
    return df

# 3. Fungsi Download Excel
def convert_to_excel_and_download(df: pd.DataFrame, num_rows: str, var_name: str) -> tuple[bytes, str]:
    """Mengubah DataFrame menjadi file Excel (.xlsx) dengan batasan baris tertentu."""
    
    # Tentukan batas ekspor
    if num_rows.lower() == 'all':
        df_export = df
        suffix = "ALL"
    else:
        try:
            limit = int(num_rows) 
            df_export = df.head(limit)
            suffix = f"Top{limit}"
        except ValueError:
            # Fallback jika input tidak valid
            df_export = df.head(100)
            suffix = "Top100"

    output = BytesIO()
    # Pastikan 'xlsxwriter' terinstal
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_export.to_excel(writer, index=False, sheet_name=var_name)
    
    processed_data = output.getvalue()
    return processed_data, f"{var_name}_{suffix}.xlsx"

# ====================================================================
# B. APLIKASI STREAMLIT UTAMA
# ====================================================================

st.title("NC File Viewer 🔎")
st.markdown("Unggah file **NetCDF (.nc)** Anda, lalu gunakan **Sidebar** untuk mengonfigurasi tampilan data.")

# --- Unggah File ---
uploaded_file = st.file_uploader("Pilih file NetCDF (.nc)", type="nc")

if uploaded_file is not None:
    
    # Ambil bytes dari file yang diunggah
    file_bytes = uploaded_file.getvalue()
    
    try:
        # Muat Dataset (sekali berkat caching)
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
            st.subheader("Pengaturan Pratinjau")
            preview_options = ["10", "50", "100", "500", "All"]
            selected_preview = st.selectbox(
                "Jumlah Baris Pratinjau:",
                preview_options,
                index=0, # Default 10 baris
                key="sidebar_preview_rows"
            )

            # 3. Pengaturan Ekspor
            st.subheader("Pengaturan Ekspor Excel")
            export_options = ["All", "1000", "10000", "50000"]
            selected_export = st.selectbox(
                "Jumlah Baris Ekspor:",
                export_options,
                index=0, # Default All
                key="sidebar_export_rows",
                help="Pilih jumlah baris yang akan dimasukkan dalam file Excel yang diunduh."
            )
            
            # 4. Tombol Submit
            submit_button = st.button("Terapkan Konfigurasi", type="primary")

        # --- Tampilan Utama Hasil ---

        if submit_button:
            st.subheader(f"Hasil Konfigurasi Data: `{selected_var}`")
            
            try:
                # 1. Konversi Data ke DataFrame (sekali berkat caching)
                data_array = ds[selected_var]
                # Panggil fungsi dengan _data_array
                df = convert_to_dataframe(selected_var, data_array) 
                total_rows = len(df)

                # --- Informasi & Statistik ---
                col_info, col_stat = st.columns([1, 2])
                
                with col_info:
                    st.metric(label="Total Baris Data", value=f"{total_rows:,}")
                
                with col_stat:
                    st.markdown(f"**Statistik Deskriptif ({selected_var}):**")
                    st.dataframe(df[selected_var].describe().to_frame().T, use_container_width=True)

                st.markdown("---")
                
                # --- Tampilkan Pratinjau Data ---
                st.subheader("Tabel Pratinjau")
                
                if selected_preview.lower() == 'all':
                    st.info(f"Menampilkan **SEMUA** {total_rows:,} baris data.")
                    st.dataframe(df, use_container_width=True)
                else:
                    limit = int(selected_preview)
                    st.info(f"Menampilkan **{limit:,}** baris teratas dari data.")
                    st.dataframe(df.head(limit), use_container_width=True)

                # --- Unduh Excel ---
                st.markdown("---")
                st.subheader("Opsi Unduh")
                
                excel_data, filename = convert_to_excel_and_download(df, selected_export, selected_var)
                
                st.download_button(
                    label=f"⬇️ Unduh Data '{selected_var}' ({selected_export} Baris) sebagai XLSX",
                    data=excel_data,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_excel_final"
                )

            except Exception as e:
                # Tampilkan error di UI untuk debugging cepat
                st.error(f"Terjadi kesalahan saat memproses data variabel '{selected_var}'. Kesalahan: {e}")
        
        # --- Informasi Dataset (Selalu Tampil) ---
        st.markdown("---")
        st.subheader("Informasi Dataset (Metadata)")
        st.code(str(ds), language='text') 

    except Exception as e:
        # Jika terjadi error saat memuat file (misalnya, file rusak)
        st.error(f"Gagal memuat file NetCDF. Pastikan file berformat .nc yang valid. Kesalahan: {e}")

# Di luar blok if uploaded_file is not None:
else:
    # Bersihkan cache resource saat tidak ada file terunggah
    st.cache_resource.clear()
    st.info("Silakan unggah file NetCDF (.nc) Anda di atas untuk memulai.")