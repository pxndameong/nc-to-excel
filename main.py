import streamlit as st
import xarray as xr
import pandas as pd
import io

# Judul aplikasi
st.title("NC File to Excel Converter")
st.markdown("Unggah file NetCDF (.nc) Anda, lalu atur kolom dan baris dengan cara memilih dimensi.")

if 'ds' not in st.session_state:
    st.session_state.ds = None

# Unggah file
uploaded_file = st.file_uploader("Pilih file NetCDF (.nc)", type="nc")

if uploaded_file is not None and st.session_state.ds is None:
    try:
        # Membaca file NC ke dalam session state
        st.session_state.ds = xr.open_dataset(uploaded_file)
        st.success("File NetCDF berhasil dimuat! Sekarang, atur output Excel Anda.")
    except Exception as e:
        st.error(f"Gagal memuat file NetCDF. Pastikan file berformat .nc yang valid. Kesalahan: {e}")

if st.session_state.ds:
    ds = st.session_state.ds

    # Menampilkan informasi dataset
    st.subheader("Informasi Dataset")
    st.write(ds)
    
    # Pilih variabel
    variables = list(ds.data_vars)
    selected_var = st.selectbox("Pilih variabel yang akan diubah ke Excel", variables)
    
    if selected_var:
        # Dapatkan semua dimensi dari variabel yang dipilih
        all_dims = list(ds[selected_var].dims)
        
        st.subheader("Atur Kolom dan Baris")
        st.markdown("Pilih dimensi untuk kolom (headers) dan baris (index).")

        # --- Bagian 'Drag and Drop' Tiruan ---
        
        # Opsi untuk kolom
        available_for_cols = all_dims
        selected_cols = st.multiselect(
            "Pilih dimensi untuk Kolom",
            options=available_for_cols,
            key="col_select"
        )
        
        # Opsi untuk baris
        # Opsi yang tersedia untuk baris adalah semua dimensi dikurangi yang sudah dipilih untuk kolom
        available_for_rows = [dim for dim in all_dims if dim not in selected_cols]
        selected_rows = st.multiselect(
            "Pilih dimensi untuk Baris",
            options=available_for_rows,
            key="row_select",
            default=available_for_rows  # Default semua dimensi yang tersisa
        )
        
        # Tombol untuk melihat pratinjau dan mengunduh
        if st.button("Proses dan Tampilkan"):
            try:
                # Mengonversi dan mereshape data
                df = ds[selected_var].to_dataframe()
                
                if selected_cols:
                    df = df.pivot(index=selected_rows, columns=selected_cols, values=selected_var).reset_index()
                    # Flatten multi-level columns
                    df.columns = ['_'.join(map(str, col)).strip('_') for col in df.columns.values]
                else:
                    # Jika tidak ada kolom yang dipilih, hanya reset index
                    df = df.reset_index()

                st.subheader("Pratinjau Data")
                st.dataframe(df.head(10))

                # Tombol untuk mengunduh
                st.subheader("Unduh File Excel")
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                    df.to_excel(writer, index=False, sheet_name=selected_var)

                st.download_button(
                    label="📥 Unduh File Excel",
                    data=excel_buffer.getvalue(),
                    file_name=f"{selected_var}_data.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Terjadi kesalahan saat memproses data. Pastikan konfigurasi dimensi Anda benar. Kesalahan: {e}")