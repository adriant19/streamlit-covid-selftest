import streamlit as st
from google.oauth2 import service_account

# create connection

credentials = service_account.Credentials.from_service_account_file(
    st.secrets["gcp_service_account"],
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)

conn = connect(credentials=credentials)
