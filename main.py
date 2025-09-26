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

# 1. Gunakan st.cache_resource untuk objek xarray.Dataset (non-serializable/complex resource)
@st.cache_resource(show_spinner="Memuat file NetCDF...")
def load_netcdf_file(file_bytes: bytes) -> xr.Dataset:
    """
    Memuat file NetCDF menggunakan xarray.open_dataset dari bytes file yang diunggah.
    """
    # xr.open_dataset dapat menerima file-like object seperti BytesIO
    # Kita menggunakan BytesIO untuk membaca data dari bytes yang diterima
    with xr.open_dataset(BytesIO(file_bytes)) as ds:
        # Kita perlu memuat data (atau setidaknya memuat header/metadata)
        # untuk memastikan ds bisa diakses setelah fungsi selesai
        return ds.load() 

# 2. Gunakan st.cache_data untuk hasil konversi (Pandas DataFrame)
# Tambahkan garis bawah (_) pada argumen 'data_array' untuk mengabaikan hashing
@st.cache_data(show_spinner="Mempersiapkan data variabel...")
def convert_to_dataframe(_data_array: xr.DataArray) -> pd.DataFrame:
    """
    Mengubah xarray.DataArray menjadi Pandas DataFrame.
    Streamlit akan mengabaikan 'data_array' saat membuat hash.
    """
    df = _data_array.to_dataframe().reset_index()
    return df

# --- Aplikasi Streamlit ---

st.title("NC File Viewer 🔎")
st.markdown("Unggah file **NetCDF (.nc)** Anda untuk melihat informasi dataset dan pratinjau data variabel.")

# Unggah file
uploaded_file = st.file_uploader("Pilih file NetCDF (.nc)", type="nc")

if uploaded_file is not None:
    
    # Baca file sebagai bytes sebelum dimasukkan ke fungsi caching
    file_bytes = uploaded_file.getvalue()
    
    try:
        # Muat Dataset menggunakan cache resource
        ds = load_netcdf_file(file_bytes)
        
        st.success("File NetCDF berhasil dimuat! 🎉")
        
        # ---
        
        ## Informasi Dataset
        
        st.subheader("Informasi Dataset")
        # st.code lebih rapi daripada st.write untuk output xarray
        st.code(str(ds), language='text') 
        
        st.markdown("---")
        
        ## Data Variabel
        
        st.subheader("Data Variabel")
        
        # Filter variabel yang memiliki data (bukan hanya koordinat atau bnds)
        # Ini penting agar hanya variabel yang ingin dilihat yang muncul di dropdown
        variables = list(ds.data_vars.keys())
        
        if variables:
            selected_var = st.selectbox(
                "Pilih variabel untuk melihat data", 
                variables,
                key="var_select" 
            )
            
            if selected_var:
                try:
                    data_array = ds[selected_var]
                    
                    # Konversi DataArray ke DataFrame (menggunakan cache data)
                    # Karena kita menggunakan _data_array, Streamlit akan menggunakan 
                    # hash dari argumen lain (yang tidak ada) + hash internal Streamlit
                    # Ini akan bekerja, dan cache akan di-reset saat 'selected_var' diubah 
                    # karena script me-rerun dan ds[selected_var] berubah.
                    df = convert_to_dataframe(data_array) 
                    
                    st.write(f"**Pratinjau 5 baris pertama dari variabel '{selected_var}' (Total Baris: {len(df):,}):**")
                    st.dataframe(df.head(10), use_container_width=True) # Tampilkan 10 baris agar lebih informatif
                    
                    st.markdown("---")
                    
                    # Kolom untuk menampilkan statistik deskriptif
                    col1, col2 = st.columns([1, 2])

                    with col1:
                        if st.checkbox("Tampilkan semua data", help="Tampilkan semua data (hati-hati, bisa lambat untuk file besar)"):
                            st.dataframe(df, use_container_width=True)
                    
                    with col2:
                        st.markdown(f"**Statistik Deskriptif ({selected_var}):**")
                        st.dataframe(df[selected_var].describe().to_frame().T, use_container_width=True)


                except Exception as e:
                    st.error(f"Terjadi kesalahan saat menampilkan data untuk variabel '{selected_var}': {e}")
        else:
            st.warning("Dataset ini tidak memiliki variabel data yang dapat ditampilkan.")
            
    except Exception as e:
        # st.exception(e) # Gunakan ini jika ingin debugging lebih detail
        st.error(f"Gagal memuat file NetCDF. Pastikan file berformat .nc yang valid. Kesalahan: {e}")