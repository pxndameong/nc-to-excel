import streamlit as st
import xarray as xr
import pandas as pd
import io

# Judul aplikasi
st.title("NC File to Excel Converter")
st.markdown("Unggah file NetCDF (.nc) Anda untuk diubah menjadi file Excel (.xlsx).")

# Unggah file
uploaded_file = st.file_uploader("Pilih file NetCDF (.nc)", type="nc")

if uploaded_file is not None:
    # Membaca file NC
    try:
        with xr.open_dataset(uploaded_file) as ds:
            st.success("File NetCDF berhasil dimuat!")

            # Menampilkan informasi dataset
            st.subheader("Informasi Dataset")
            st.write(ds)

            # Pilih variabel untuk diubah
            variables = list(ds.data_vars)
            selected_var = st.selectbox("Pilih variabel yang akan diubah ke Excel", variables)

            if selected_var:
                # Mengonversi variabel ke DataFrame
                try:
                    df = ds[selected_var].to_dataframe()

                    # Mengatur ulang indeks agar koordinat menjadi kolom
                    df = df.reset_index()

                    # Menampilkan pratinjau data
                    st.subheader(f"Pratinjau Data dari Variabel '{selected_var}'")
                    st.write(df.head())

                    # Tombol untuk mengunduh file Excel
                    st.subheader("Unduh File Excel")

                    # Membuat buffer in-memory untuk file Excel
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
                    st.error(f"Terjadi kesalahan saat mengonversi data: {e}")

    except Exception as e:
        st.error(f"Gagal memuat file NetCDF. Pastikan file berformat .nc yang valid. Kesalahan: {e}")