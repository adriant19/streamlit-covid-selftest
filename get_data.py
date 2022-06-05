import streamlit as st
import pandas as pd
from googleapiclient.discovery import Resource

import config


def get_data(conn) -> pd.DataFrame:
    """ Read data from dB

    :param conn: existing connection via google api v4
    :return: extracted dataframe, sorted by year, week, log datetime
    """

    values = (
        conn.values().get(
            spreadsheetId=config.SPREADSHEET_ID,
            range=f"{config.SHEET_NAME}!{config.TAB_RANGE}",
        ).execute()
    )

    df = pd.DataFrame(values["values"]).fillna("")
    df.columns = df.iloc[0]
    df = df[1:]
    df = df.astype({"Log Datetime": "datetime64[ns]", "Year": int, "Week": int})

    return df.sort_values(["Year", "Week", "Log Datetime"], ascending=[False, False, True]).reset_index(drop=True)


@st.cache(hash_funcs={Resource: hash})  # pulled once only
def get_users(conn):
    """ Usernames and password for authentication of users

    :param conn: existing connection via google api v4
    :return: extracted list of users with username, name and password
    """

    values = (
        conn.values().get(
            spreadsheetId=config.SPREADSHEET_ID,
            range=f"Members!A:C",
        ).execute()
    )

    user_df = pd.DataFrame(values["values"]).fillna("")
    user_df.columns = user_df.iloc[0]

    return user_df[1:]["Name"], user_df[1:].set_index("Username").to_dict("index")  # exclude header row


@st.cache  # pulled once only
def get_weeks() -> tuple:
    """ Prepare weeks table

    :return: list of weeks and active weeks (less than current week)
    """

    weeks_df = pd.concat([
        pd.DataFrame(pd.date_range("2022-01-01", "2022-12-31", freq="W-MON"), columns=["start_date"]),
        pd.DataFrame(pd.date_range("2022-01-01", "2022-12-31", freq="W-MON"), columns=["end_date"]) + pd.DateOffset(days=6)
    ], axis=1)

    weeks_df.insert(0, "week_number", weeks_df["start_date"].dt.isocalendar().week)

    # get active weeks that can be selected

    active_weeks = list(filter(lambda x: x <= config.curr_week, weeks_df["week_number"].tolist()))

    return weeks_df.set_index("week_number"), sorted(active_weeks, reverse=True)
