import streamlit as st
import xarray as xr
import pandas as pd

# Set konfigurasi halaman (opsional, tapi baik untuk tampilan)
st.set_page_config(
    page_title="NC File Viewer",
    layout="wide" 
)

# --- Fungsi Caching ---

# Menggunakan cache data untuk menyimpan dataset xarray agar tidak dimuat ulang
@st.cache_data(show_spinner="Memuat file NetCDF...")
def load_netcdf_file(file_object):
    """
    Memuat file NetCDF menggunakan xarray.open_dataset.
    File_object adalah BytesIO dari file yang diunggah.
    """
    # xr.open_dataset dapat menerima file-like object
    ds = xr.open_dataset(file_object)
    return ds

# Menggunakan cache data untuk menyimpan DataFrame agar tidak dikonversi ulang
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
    # 1. Muat file sekali dan cache hasilnya
    try:
        # Panggil fungsi caching untuk memuat dataset
        ds = load_netcdf_file(uploaded_file)
        
        st.success("File NetCDF berhasil dimuat! 🎉")
        
        # ---
        
        ## Informasi Dataset (Metadata)
        
        st.subheader("Informasi Dataset")
        # Menampilkan representasi string dari dataset
        st.code(str(ds), language='text') 
        # Menggunakan st.code agar output format xarray lebih rapi
        
        st.markdown("---")
        
        ## Data Variabel
        
        st.subheader("Data Variabel")
        
        # Membuat list dari semua variabel data
        variables = list(ds.data_vars)
        
        if variables:
            # 2. Dropdown menu untuk memilih variabel
            selected_var = st.selectbox(
                "Pilih variabel untuk melihat data", 
                variables,
                key="var_select" # Tambahkan key untuk identifikasi state
            )
            
            if selected_var:
                # 3. Muat/Konversi data variabel yang dipilih ke DataFrame (dan cache hasilnya)
                try:
                    data_array = ds[selected_var]
                    df = convert_to_dataframe(data_array)
                    
                    st.write(f"**Pratinjau 5 baris pertama dari variabel '{selected_var}':**")
                    # Tampilkan 5 baris pertama
                    st.dataframe(df.head(), use_container_width=True)
                    
                    # Opsi untuk menampilkan data lengkap 
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
    # Menghapus cache saat file baru diunggah atau file lama dihapus
    st.cache_data.clear()