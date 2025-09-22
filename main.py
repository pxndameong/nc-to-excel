import streamlit as st
import xarray as xr
import pandas as pd

# Judul aplikasi
st.title("NC File Viewer 🔎")
st.markdown("Unggah file NetCDF (.nc) Anda, lalu klik **'Process'** untuk melihat isinya.")

# Unggah file
uploaded_file = st.file_uploader("Pilih file NetCDF (.nc)", type="nc")

# Menggunakan state untuk melacak apakah tombol process sudah ditekan
if uploaded_file is not None:
    # Menampilkan tombol "Process"
    if st.button("Process"):
        st.session_state['process_clicked'] = True
    
    # Kondisi untuk menampilkan data hanya jika tombol process sudah ditekan
    if 'process_clicked' in st.session_state and st.session_state['process_clicked']:
        # Membaca file NC
        try:
            # Menggunakan xarray untuk membuka file NetCDF
            ds = xr.open_dataset(uploaded_file)
            
            st.success("File NetCDF berhasil dimuat! 🎉")
            
            # ---
            
            ## Informasi Dataset (Metadata)
            
            st.subheader("Informasi Dataset")
            # Menampilkan representasi string dari dataset, yang berisi dimensi, koordinat, variabel, dan atribut global
            st.write(ds)
            
            # ---
            
            ## Data Variabel
            
            st.subheader("Data Variabel")
            
            # Membuat list dari semua variabel data yang ada di dataset
            variables = list(ds.data_vars)
            
            if variables:
                # Dropdown menu untuk memilih variabel yang ingin dilihat
                selected_var = st.selectbox("Pilih variabel yang ingin Anda lihat datanya", variables)
                
                if selected_var:
                    # Mengubah data variabel yang dipilih menjadi DataFrame untuk pratinjau
                    try:
                        df = ds[selected_var].to_dataframe()
                        # Mereset indeks agar koordinat menjadi kolom, sehingga lebih mudah dibaca
                        df = df.reset_index()
                        
                        st.write(f"**Pratinjau 5 baris pertama dari variabel '{selected_var}':**")
                        # Menampilkan 5 baris pertama dari DataFrame
                        st.dataframe(df.head())
                        
                        # Opsi untuk menampilkan data lengkap (jika tidak terlalu besar)
                        st.markdown("---")
                        if st.button("Tampilkan semua data", help="Tampilkan semua data (hati-hati, bisa lambat untuk file besar)"):
                            st.write(df)
                            
                    except Exception as e:
                        st.error(f"Terjadi kesalahan saat menampilkan data: {e}")
            else:
                st.warning("Dataset tidak memiliki variabel data.")
                
        except Exception as e:
            st.error(f"Gagal memuat file NetCDF. Pastikan file berformat .nc yang valid. Kesalahan: {e}")