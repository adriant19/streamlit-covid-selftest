import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build

from PIL import Image
import datetime
import pytz
import pandas as pd

# settings

SCOPE = "https://www.googleapis.com/auth/spreadsheets"
SPREADSHEET_ID = "1PjqMD8kJYjFSJduuX0rwor2Eej6O_qnjc5Ol81jG5T0"
SHEET_NAME = "dB"
GSHEET_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}"


# create connection

def connect_to_gsheet():

    credentials = service_account.Credentials.from_service_account_file(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )

    service = build("sheets", "v4", credentials=credentials)

    return service.spreadsheets()


def get_data(conn) -> pd.DataFrame:

    pass


# page setup

st.set_page_config(layout="wide", page_icon="☠️")
header1, header2 = st.columns((1, 3))
header1.image(Image.open("shopee_logo_en_email.png"), width=200)
header2.title("Marketing Analytics", anchor="top")
header2.markdown(f"""
This app receives the team's self reported test kit results for covid-19 for tracking purposes.
""")
st.write("***")

with st.sidebar:

    st.header("User Input Function")
    st.write(datetime.datetime.now(pytz.timezone("Asia/Kuala_Lumpur")))

    with st.form(key="annotation"):

        st.write(
            pd.date_range(
                '2022-01-01', '2022-12-31',
                freq='W-MON'
            ).to_series(name='start_of_week').reset_index(drop=True)
        )

        week = st.selectbox("Week Number", [1, 2, 3, 4], index=0)
        date = st.date_input("Self Test Date")

        days = st.multiselect(
            "Days in Week",
            ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            ["Mon", "Tue", "Wed", "Thu", "Fri"]
        )

        remark = st.text_area("Remark:")
        outcome = st.radio("Result", ("negative (C)", "positive (T)"), index=0)

        submit = st.form_submit_button(label="Submit")

    if submit:
        st.success("self test results submitted")

st.subheader("Records")
st.write(f"""Source: [Gsheet]({GSHEET_URL})""")
