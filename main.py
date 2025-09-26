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

# Gunakan st.cache_resource untuk objek xarray.Dataset (non-serializable/complex resource)
@st.cache_resource(show_spinner="Memuat file NetCDF...")
def load_netcdf_file(file_bytes: bytes) -> xr.Dataset:
    """Memuat file NetCDF menggunakan xarray.open_dataset dari bytes file yang diunggah."""
    with xr.open_dataset(BytesIO(file_bytes)) as ds:
        # Muat data untuk memastikan ds bisa diakses setelah fungsi selesai
        return ds.load() 

# Gunakan st.cache_data untuk hasil konversi data (Pandas DataFrame)
@st.cache_data(show_spinner="Mempersiapkan data variabel...")
def convert_to_dataframe(_data_array: xr.DataArray) -> pd.DataFrame:
    """
    Mengubah xarray.DataArray menjadi Pandas DataFrame.
    Garis bawah (_) mengabaikan argumen dari mekanisme hashing Streamlit.
    """
    df = _data_array.to_dataframe().reset_index()
    return df

# --- Fungsi Download Excel ---

def convert_to_excel_and_download(df: pd.DataFrame, num_rows: str, var_name: str) -> bytes:
    """
    Mengubah DataFrame menjadi file Excel (.xlsx) dengan batasan baris tertentu.
    """
    if num_rows == 'all':
        df_export = df
        suffix = "ALL"
    else:
        # Konversi ke integer, pastikan sudah divalidasi
        limit = int(num_rows) 
        df_export = df.head(limit)
        suffix = f"Top{limit}"

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_export.to_excel(writer, index=False, sheet_name=var_name)
    
    processed_data = output.getvalue()
    return processed_data, f"{var_name}_{suffix}.xlsx"

# --- Aplikasi Streamlit ---

st.title("NC File Viewer 🔎")
st.markdown("Unggah file **NetCDF (.nc)** Anda untuk melihat informasi dataset, mengatur pratinjau, dan mengunduh data.")

# Unggah file
uploaded_file = st.file_uploader("Pilih file NetCDF (.nc)", type="nc")

if uploaded_file is not None:
    
    # Baca file sebagai bytes
    file_bytes = uploaded_file.getvalue()
    
    try:
        # Muat Dataset menggunakan cache resource
        ds = load_netcdf_file(file_bytes)
        
        st.success("File NetCDF berhasil dimuat! 🎉")
        
        # ---
        
        ## Informasi Dataset
        
        st.subheader("Informasi Dataset")
        st.code(str(ds), language='text') 
        
        st.markdown("---")
        
        ## Data Variabel
        
        st.subheader("Pratinjau & Ekspor Data Variabel")
        
        variables = list(ds.data_vars.keys())
        
        if variables:
            
            # Pengaturan Pratinjau dan Ekspor dalam kolom
            col1, col2, col3 = st.columns([1.5, 1, 1])

            with col1:
                selected_var = st.selectbox(
                    "Pilih variabel data:", 
                    variables,
                    key="var_select" 
                )
            
            if selected_var:
                try:
                    data_array = ds[selected_var]
                    df = convert_to_dataframe(data_array) 
                    
                    total_rows = len(df)
                    
                    with col2:
                        # Opsi untuk Tampilan/Pratinjau
                        preview_options = ["5", "10", "50", "100", "All"]
                        selected_preview = st.selectbox(
                            f"Baris Pratinjau (Total: {total_rows:,})",
                            preview_options,
                            index=1, # Default 10 baris
                            key="preview_rows"
                        )
                    
                    with col3:
                         # Opsi untuk Ekspor
                        export_options = ["All", "100", "1000", "10000"]
                        selected_export = st.selectbox(
                            "Baris Ekspor Excel:",
                            export_options,
                            index=0, # Default All
                            key="export_rows",
                            help="Pilih jumlah baris yang akan diunduh ke Excel."
                        )
                    
                    # --- Tampilkan Pratinjau ---
                    st.markdown(f"**Pratinjau Variabel '{selected_var}':**")
                    
                    if selected_preview == 'All':
                        st.dataframe(df, use_container_width=True)
                    else:
                        limit = int(selected_preview)
                        st.dataframe(df.head(limit), use_container_width=True)

                    # --- Unduh Excel ---
                    st.markdown("---")
                    
                    excel_data, filename = convert_to_excel_and_download(df, selected_export, selected_var)
                    
                    st.download_button(
                        label=f"⬇️ Unduh Data '{selected_var}' ({selected_export} Baris) sebagai XLSX",
                        data=excel_data,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="download_excel_button"
                    )
                    
                    # --- Statistik ---
                    st.markdown("---")
                    st.markdown(f"**Statistik Deskriptif ({selected_var}):**")
                    st.dataframe(df[selected_var].describe().to_frame().T, use_container_width=True)


                except Exception as e:
                    st.error(f"Terjadi kesalahan saat menampilkan data untuk variabel '{selected_var}': {e}")
        else:
            st.warning("Dataset ini tidak memiliki variabel data yang dapat ditampilkan.")
            
    except Exception as e:
        st.error(f"Gagal memuat file NetCDF. Pastikan file berformat .nc yang valid. Kesalahan: {e}")