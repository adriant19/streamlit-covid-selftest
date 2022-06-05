import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build


@st.experimental_singleton
def connect_to_gsheet():

    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],  # get secret keys from saved secrets
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )

    return build("sheets", "v4", credentials=credentials, cache_discovery=False).spreadsheets()
