import streamlit as st
import xarray as xr
import pandas as pd

# Set konfigurasi halaman (opsional, tapi baik untuk tampilan)
st.set_page_config(
    page_title="NC File Viewer",
    layout="wide" 
)

# --- Fungsi Caching ---

# GANTI @st.cache_data menjadi @st.cache_resource untuk objek kompleks seperti xarray.Dataset
@st.cache_resource(show_spinner="Memuat file NetCDF...")
def load_netcdf_file(file_object):
    """
    Memuat file NetCDF menggunakan xarray.open_dataset.
    """
    # xr.open_dataset dapat menerima file-like object
    ds = xr.open_dataset(file_object)
    return ds

# Gunakan @st.cache_data untuk hasil konversi data (Pandas DataFrame)
@st.cache_data(show_spinner="Mempersiapkan data variabel...")
def convert_to_dataframe(data_array):
    """
    Mengubah xarray.DataArray menjadi Pandas DataFrame.
    """
    df = data_array.to_dataframe().reset_index()
    return df

# --- Aplikasi Streamlit ---

st.title("NC File Viewer 🔎")
st.markdown("Unggah file **NetCDF (.nc)** Anda untuk melihat informasi dataset dan pratinjau data variabel.")

# Unggah file
uploaded_file = st.file_uploader("Pilih file NetCDF (.nc)", type="nc")

if uploaded_file is not None:
    try:
        # Panggil fungsi caching untuk memuat dataset
        # Objek ds sekarang di-cache sebagai "resource"
        ds = load_netcdf_file(uploaded_file)
        
        st.success("File NetCDF berhasil dimuat! 🎉")
        
        # ---
        
        ## Informasi Dataset (Metadata)
        
        st.subheader("Informasi Dataset")
        st.code(str(ds), language='text') 
        
        st.markdown("---")
        
        ## Data Variabel
        
        st.subheader("Data Variabel")
        
        variables = list(ds.data_vars)
        
        if variables:
            selected_var = st.selectbox(
                "Pilih variabel untuk melihat data", 
                variables,
                key="var_select" 
            )
            
            if selected_var:
                try:
                    data_array = ds[selected_var]
                    # DataFrame di-cache sebagai "data"
                    df = convert_to_dataframe(data_array) 
                    
                    st.write(f"**Pratinjau 5 baris pertama dari variabel '{selected_var}':**")
                    st.dataframe(df.head(), use_container_width=True)
                    
                    st.markdown("---")
                    
                    if st.checkbox("Tampilkan semua data", help="Tampilkan semua data (hati-hati, bisa lambat untuk file besar)"):
                        st.dataframe(df, use_container_width=True)

                except Exception as e:
                    st.error(f"Terjadi kesalahan saat menampilkan data untuk variabel '{selected_var}': {e}")
        else:
            st.warning("Dataset ini tidak memiliki variabel data (hanya koordinat atau atribut).")
            
    except Exception as e:
        st.error(f"Gagal memuat file NetCDF. Pastikan file berformat .nc yang valid. Kesalahan: {e}")

# Di luar blok if uploaded_file is not None:
else:
    # Ini penting untuk membersihkan cache ketika file baru diunggah
    # st.cache_resource.clear()
    pass # st.cache_resource secara otomatis membersihkan ketika hash input berubah