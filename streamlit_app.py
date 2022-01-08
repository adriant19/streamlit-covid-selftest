import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build

from PIL import Image
import datetime
import pytz
import pandas as pd
import altair as alt

# -- settings ------------------------------------------------------------------

SCOPE = "https://www.googleapis.com/auth/spreadsheets"
SPREADSHEET_ID = "1PjqMD8kJYjFSJduuX0rwor2Eej6O_qnjc5Ol81jG5T0"
SHEET_NAME = "dB"
GSHEET_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}"
TAB_RANGE = "A:I"

tz = pytz.timezone("Asia/Kuala_Lumpur")

st.set_page_config(layout="wide", page_icon="☠️")


# -- create connection ---------------------------------------------------------

@st.experimental_singleton()
def connect_to_gsheet():

    credentials = service_account.Credentials.from_service_account_info(
        {
            "type": "service_account",
            "project_id": "python2gsheet-281805",
            "private_key_id": "7d14a14b62c1979817a8bad11cd4fa925469c3a8",
            "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC9R/LBvcQi6iNM\ne9aIx+OdC3gnAyjH6Ij0LpuJrjx5U+wQQou0k4tBk3BTOJUvoBsim/jAUdkuqYF/\nBqxUJ83SLt7ZyF2e3+ony0uK/PUz0InTqG7j8FaM1nhUtSbG4bWyRSL2SlrQ4qlx\nMkamM6svlyt/vF8aBPmqxDW5F8h5MHtcRNqV323nBNe12rdcxfIFdt+wDgGgYY8g\nJ+gvQxXBJqxNTgVgCCpF7VGAnQ4B6QTWphXqGq6Z3G6s8Aa1i7YzGyoc/gJOP64L\nfvb24fKJC2Cxn+yn4vvJdKFcZMXE4mEQtVhOG0gP3BHx5pAXo6QrXztN4L1XeBwK\nqFdkIRw9AgMBAAECggEAW1UHPxMZPBusUrCCsVd6bgHlxTVSDTwYMXL33DR1u7mR\n87qYfNag4FCLZ6yq1+MylL2cBvi3ijuCX8/RgX3/Y4b4Qy/adNnou7Dtz7AFhS4A\nA2CHuXbz3Ft0jrMmddrdeJrBpwPz1E06o4M18eaGmJ0iAS3c2cpCynKI1bozIr47\nn2V/4SClfeBIxA8WZ+8UKR259CR+z6Qwxxd5t8tKAO5EQ1lVJVARipkFimwo8LsA\n6hWJDSlQTM3bEv6y2/FdqSnuTJyLDs0hSJdgkVSoIdqYOEHFC6NGp2dmLGhfPUOI\ndPj+x6PbJGYUOzdOt2kwe5OdxyIHYHxvcbEZU+lJZQKBgQDy+Ln8yn3+mKZ5yh6F\nWB2mikX0GYLY7BLyb4wSg8/kVjgHCDclVNeXQ7ZzDGvs3zgAz46rFLnNb8soEnd5\nabPWVLrFAg9PDm/oxs6I8ibmWRWqdUlYOQTXih9SxILdavdEmJ8cO5dS6TxvZlhe\n8N2f07EG70b0F3mJozz8k87swwKBgQDHbjYOmKzOSPA9hTdtcCTTQVesGNv5ucu0\n3EHGcK1w3hINnUBRyV1RjVph2rjk3ci63n1SHuwE42TDrZokDRxCYpPJ6Zm5yZwK\nW0MHEFqSQC1TlB3N9JvatBm4auZvkCjEkL/ytPfghZScroPWq/eqsCmAmPxyy5nE\n1Duj9JNC/wKBgFPEw0LPgX78nDDTKZCpn5dihtmwzfcB9UpWgQGFJnC/9RMflvus\n86N4OfgSaUdCcml9JeAABks45t8K9twKQHF9xuLTYfnMrXKg0GZQrm6uehTJ2R6s\nkenJ+iCsFb5G+bdRs1GljfeM6EQ0EfWxr4dCEf+lEV5olYOJnyYpw6bHAoGBAKnw\nAwY7GP2K75QswUdzCR4vDusqH8BTjv7ltPLIrzJ/OPj654UJxogooDzEKUt0pYh+\n8GEa0llz/zgy5ScVOOBkqbSjZwgGgP3eOGZ7jAIVx8nxa9hFOM2LLGOWTBgCyop9\nIeNKS/K5QSKmHte9oASFqkfXlT6oubYcd1nFnfq3AoGAfiCzN7UnjcwaRmlbEgA2\nCUJWVGaNAWBaMSmsOnrttBToVFncpvHUqbxvGyfoJyT5x1hqXz25u7thfkIKuldV\nlaGvQPdRCl6027tkFRC5Al2wIN5E0DTMX2Y6qJbr0AzJEIcMrY1zUsDYTMx+hjXz\nPiD+cxO2RHRU7t56HbzYNQk=\n-----END PRIVATE KEY-----\n",
            "client_email": "py2gsheet@python2gsheet-281805.iam.gserviceaccount.com",
            "client_id": "114526794528970901942",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/py2gsheet%40python2gsheet-281805.iam.gserviceaccount.com"
        },
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )

    return build("sheets", "v4", credentials=credentials).spreadsheets()


# -- update data ---------------------------------------------------------------

@st.cache(ttl=600)
def get_data(conn) -> pd.DataFrame:

    values = (
        conn.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!{TAB_RANGE}",
        ).execute()
    )

    df = pd.DataFrame(values["values"]).fillna("")
    df.columns = df.iloc[0]
    df = df[1:]

    df.sort_values(["Week", "Log Datetime"], ascending=[False, True])

    return df


def get_weeks(conn) -> pd.DataFrame:

    values = (
        conn.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"Weeks!{TAB_RANGE}",
        ).execute()
    )

    df = pd.DataFrame(values["values"])
    df.columns = df.iloc[0]
    df = df[1:]

    # get active weeks

    df["week_number"] = df["week_number"].astype(int)

    active_weeks = df[
        df["week_number"] <= datetime.datetime.today().date().isocalendar()[1]
    ].sort_values(["week_number"], ascending=[False])["week_number"].values

    df.set_index("week_number", inplace=True)

    return df, active_weeks


def get_names(conn) -> list:

    values = (
        conn.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"Members!A:A",
        ).execute()
    )

    return pd.DataFrame(values["values"])[0].values[1:]


def add_entry(conn, row) -> None:

    values = (
        conn.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A:F",
            body=dict(values=row),
            valueInputOption="USER_ENTERED",
        ).execute()
    )


def update_entry(conn, row) -> None:

    pass


def get_graph(df):

    fig = (
        alt.Chart(df, title="weekly self test reporting")
        .mark_bar()
        .encode(x="Employee", y="Days")
        .interactive()
    )

    return fig

# -- connection setup ----------------------------------------------------------


conn = connect_to_gsheet()

# -- page setup# ---------------------------------------------------------------

weeks, active_weeks = get_weeks(conn)

header1, header2 = st.columns((1, 3))

header1.write("__")
header1.image(Image.open("shopee_logo_en_email.png"), width=200)

header2.title("Marketing Analytics", anchor="top")
header2.markdown(f"""
This app receives the team's self reported test kit results for covid-19 for tracking purposes.
""")
st.write("***")

with st.sidebar:

    st.header("User Input Function")
    st.write("*now:*", datetime.datetime.now(tz))

    user = st.radio("Selected user", get_names(conn))

    with st.form(key="annotation"):

        # fields needed

        week = st.selectbox(
            "Week Number",
            active_weeks.tolist(),
            index=0,
            help="week to report self test"
        )

        date = st.date_input(
            "Self Test Date",
            max_value=datetime.datetime.now(tz),
            help="date of self test taken"
        )

        days = st.multiselect(
            "Days in Week",
            ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],  # options
            ["Mon", "Tue", "Wed", "Thu", "Fri"],  # default
            help="days in week where office visit will be undertaken"
        )

        remark = st.text_area("Remark:", value="", help="any remarks to be given (if applicable)")
        outcome = st.radio("COVID Test Result", ("Negative (C)", "Positive (T)"), index=0)

        submit = st.form_submit_button(label="Submit")

    if submit:

        start_date, end_date = list(weeks.to_dict("index")[week].values())

        # add entry (or overwrite existing) upon submission

        add_entry(
            conn,
            [[
                datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M %p"),
                week,
                start_date,
                end_date,
                user,
                str(date),
                str(days),
                remark,
                outcome
            ]]
        )

        st.success("☑️ Self test results submitted")

# -- content setup -------------------------------------------------------------

df = get_data(conn)

days_col = df.apply(lambda x: pd.Series(x["Days"].strip("][").split(", ")), axis=1).fillna("")

df1 = pd.concat([
    df,
    days_col
], axis=1)

# st.pyplot(get_graph(df))

st.write(f"""### Records *(Source: [Gsheet]({GSHEET_URL}))*""")
st.table(df)

with st.expander("Ref. Table: Week Number-Dates"):

    st.write(weeks)
