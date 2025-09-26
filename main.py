import streamlit as st
import xarray as xr
import pandas as pd
from io import BytesIO

# Set konfigurasi halaman
st.set_page_config(
    page_title="NC File Viewer",
    layout="wide" 
)

# --- Fungsi Caching ---

# Gunakan st.cache_resource untuk objek xarray.Dataset
@st.cache_resource(show_spinner="Memuat file NetCDF...")
def load_netcdf_file(file_bytes: bytes) -> xr.Dataset:
    """Memuat file NetCDF menggunakan xarray.open_dataset dari bytes file yang diunggah."""
    with xr.open_dataset(BytesIO(file_bytes)) as ds:
        return ds.load() 

# Gunakan st.cache_data untuk hasil konversi data (Pandas DataFrame)
@st.cache_data(show_spinner="Mempersiapkan data variabel...")
def convert_to_dataframe(_data_array: xr.DataArray) -> pd.DataFrame:
    """Mengubah xarray.DataArray menjadi Pandas DataFrame."""
    df = _data_array.to_dataframe().reset_index()
    return df

# --- Fungsi Download Excel ---

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
            # Fallback jika input tidak valid
            df_export = df.head(100)
            suffix = "Top100"

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_export.to_excel(writer, index=False, sheet_name=var_name)
    
    processed_data = output.getvalue()
    return processed_data, f"{var_name}_{suffix}.xlsx"

# --- Aplikasi Streamlit ---

st.title("NC File Viewer 🔎")
st.markdown("Unggah file **NetCDF (.nc)** Anda, lalu gunakan **Sidebar** untuk mengonfigurasi tampilan data.")

# Unggah file
uploaded_file = st.file_uploader("Pilih file NetCDF (.nc)", type="nc")

# Logika aplikasi berjalan jika file diunggah
if uploaded_file is not None:
    
    # Baca file sebagai bytes
    file_bytes = uploaded_file.getvalue()
    
    try:
        # Muat Dataset menggunakan cache resource
        ds = load_netcdf_file(file_bytes)
        st.success("File NetCDF berhasil dimuat! 🎉 Sekarang, konfigurasikan tampilan di Sidebar.")
        
        variables = list(ds.data_vars.keys())

        # --- Bagian Sidebar untuk Konfigurasi ---
        with st.sidebar:
            st.header("⚙️ Konfigurasi Data")
            
            # 1. Pemilihan Variabel
            selected_var = st.selectbox(
                "Pilih variabel data:", 
                variables,
                key="sidebar_var_select" 
            )

            # --- Pengaturan Pratinjau ---
            st.subheader("Pengaturan Pratinjau")
            preview_options = ["5", "10", "50", "100", "All"]
            selected_preview = st.selectbox(
                "Jumlah Baris Pratinjau:",
                preview_options,
                index=1, # Default 10 baris
                key="sidebar_preview_rows",
                help="Pilih jumlah baris yang akan ditampilkan di layar utama."
            )

            # --- Pengaturan Ekspor ---
            st.subheader("Pengaturan Ekspor Excel")
            export_options = ["All", "1000", "10000", "50000"]
            selected_export = st.selectbox(
                "Jumlah Baris Ekspor:",
                export_options,
                index=0, # Default All
                key="sidebar_export_rows",
                help="Pilih jumlah baris yang akan dimasukkan dalam file Excel yang diunduh."
            )
            
            # 2. Tombol Submit (Terapkan Konfigurasi)
            # Tombol ini akan mengaktifkan logika tampilan data
            submit_button = st.button("Terapkan Konfigurasi", type="primary")

        # --- Tampilan Utama Data ---

        if submit_button and selected_var:
            st.subheader(f"Hasil Konfigurasi Data: `{selected_var}`")
            
            try:
                # 1. Konversi data dan dapatkan total baris
                data_array = ds[selected_var]
                df = convert_to_dataframe(data_array) 
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
                
                # Tentukan batas pratinjau
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
                
                # Hasilkan data Excel berdasarkan konfigurasi ekspor
                excel_data, filename = convert_to_excel_and_download(df, selected_export, selected_var)
                
                st.download_button(
                    label=f"⬇️ Unduh Data '{selected_var}' ({selected_export} Baris) sebagai XLSX",
                    data=excel_data,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_excel_final"
                )

            except Exception as e:
                st.error(f"Terjadi kesalahan saat memproses data variabel '{selected_var}': {e}")
        
        # --- Informasi Dataset (Selalu Tampil) ---
        st.markdown("---")
        st.subheader("Informasi Dataset (Metadata)")
        st.code(str(ds), language='text') 

    except Exception as e:
        st.error(f"Gagal memuat file NetCDF. Pastikan file berformat .nc yang valid. Kesalahan: {e}")

# Di luar blok if uploaded_file is not None:
else:
    # Bersihkan cache saat tidak ada file terunggah
    st.cache_resource.clear()