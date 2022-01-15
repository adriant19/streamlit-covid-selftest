import streamlit as st
from googleapiclient.discovery import Resource
from google.oauth2 import service_account
from googleapiclient.discovery import build
import config

import datetime
import pytz
import pandas as pd
import numpy as np
import altair as alt

# -- global variables, settings & connection setup -----------------------------

st.set_page_config(page_title="COVID Self Test Reporting", layout="wide", page_icon="☠️")

tz = pytz.timezone("Asia/Kuala_Lumpur")
curr_year, curr_week, _ = datetime.datetime.now(tz).date().isocalendar()


@st.experimental_singleton
def connect_to_gsheet():

    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],  # get secret keys from saved secrets
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )

    return build("sheets", "v4", credentials=credentials, cache_discovery=False).spreadsheets()


# -- update data ---------------------------------------------------------------

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

    active_weeks = list(filter(lambda x: x <= curr_week, weeks_df["week_number"].tolist()))

    return weeks_df.set_index("week_number"), sorted(active_weeks, reverse=True)


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


def add_entry(conn, row) -> None:
    """ Add entry to dB

    :param conn: existing connection via google api v4
    :param row: row details to be submitted into dB
    :return: extracted list of weeks and active weeks (less than current week)
    """

    values = (
        conn.values().append(
            spreadsheetId=config.SPREADSHEET_ID,
            range=f"{config.SHEET_NAME}!A:F",
            body=dict(values=row),
            valueInputOption="USER_ENTERED",
        ).execute()
    )


def get_graph(df, names):
    """ Generate altair graph

    :param df: base data points for plot
    :param names: list of names to plot against
    :return: figure of altair graph
    """

    # unwrap data by days for visualisation

    df1 = pd.concat([
        df[["Year", "Week", "Member", "Result"]],
        df.apply(lambda x: pd.Series(x["Days"].split(", ")), axis=1).fillna("")
    ], axis=1).set_index(["Year", "Week", "Member", "Result"])

    df2 = pd.DataFrame(df1.stack()).rename(columns={0: "Days"}).reset_index(level=4, drop=True).reset_index()

    plot_df = pd.merge(
        names.rename("Member"),
        df2[(df2["Week"] == int(select_week)) & (df2["Year"] == int(select_year))],
        how="left", on="Member"
    ).query("Days != ''").fillna(value={"Days": ""})

    plot_df["Legend"] = np.where(
        (plot_df["Result"].isna()) & (plot_df["Days"] == ""),
        "Untested", plot_df["Result"]
    )

    fig = (
        alt.Chart(plot_df, title=f"Week {select_week} - Self Test Reporting")
        .configure_axis(grid=True)
        .mark_circle(size=200)
        .encode(
            x="Member",
            y=alt.Y("Days", sort=["Mon", "Tue", "Wed", "Thu", "Fri"]),
            color=alt.Color("Legend", scale=alt.Scale(range=["#FFC300", "#C70039", "chartreuse"], domain=["Untested", "Positive (T)", "Negative (C)"]))
        )
        .properties(height=500)
    )

    return fig


# -- get data (regardless if authentication performed) -------------------------

df = get_data(connect_to_gsheet())
names, users = get_users(connect_to_gsheet())
weeks_df, active_weeks = get_weeks()

# -- header setup --------------------------------------------------------------

st.subheader("""COVID-19 self-test declaration tracker""")

with st.expander("Description"):
    st.write(
        """
        **Streamlit dashboard by Adrian Tan**\n
        *! login using username: 'admin' and password: 'admin' for preview purposes.*
        
        - This app records the team's self reported test kit results for COVID-19 (per week).
        - Each year-week only can have one entry for each uniq. user.
        - Note: feature to resubmit as an amendment was not implemented.
        ***
        """
    )

    st.text(
        """
        Changelog
        ---
        [Pending] logic to amend entry rows if a user is resubmitting for a given year and week
        [Done] Only submits new entries if have not declared by user for a given year-week
        [Done] Graph now captures users that have not declared status
        """
    )

st.write("***")

# -- sidebar setup -------------------------------------------------------------

with st.sidebar:

    # -- perform login -------------------------------------------------------------

    with st.expander("🔒 User Login", expanded=True):
        username = st.text_input("Username")
        password = st.text_input("Password")

    current_user = users.get(username)  # verifies if existing user

    if username == "" and password == "":
        st.info("Key in username & password")

    else:
        if current_user["Password"] if current_user is not None else None == password:
            current_user_name = current_user["Name"]
            st.success(f"Logged in as {current_user_name}")

#  --submission form -----------------------------------------------------------

            with st.form(key="annotation"):
                st.subheader("User Input Function")

                # fields needed

                col1, col2 = st.columns(2)

                with col1:
                    week = st.selectbox(
                        "Week Number",
                        active_weeks,
                        index=0,
                        help="week to report self test"
                    )

                with col2:
                    date = st.date_input(
                        "Self Test Date",
                        max_value=datetime.datetime.now(tz).date(),
                        help="date of self test taken"
                    )

                days = st.multiselect(
                    "Days in Office",
                    ["Mon", "Tue", "Wed", "Thu", "Fri"],  # options
                    ["Tue", "Thu"],  # default
                    help="days in week where office visit will be undertaken"
                )

                remark = st.text_area("Remark:", value="", help="any remarks to be given (if applicable)")
                outcome = st.radio("COVID Test Result", ("Negative (C)", "Positive (T)"), index=0)
                submit = st.form_submit_button(label="Submit")

            if submit:
                start_date, end_date = list(weeks_df.to_dict("index")[week].values())

                # add entry (or overwrite existing) upon submission

                # if existing, then amend else append

                checker = df.apply(lambda x: f"{x['Year']}-{x['Week']}-{x['Member']}", axis=1).tolist() if not df.empty else [None]

                if f"{date.year}-{week}-{current_user_name}" not in checker:
                    add_entry(
                        connect_to_gsheet(),
                        [[
                            datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M"),
                            str(date.year),
                            str(week),
                            str(start_date.date()),
                            str(end_date.date()),
                            current_user_name,
                            str(date),
                            ', '.join(days),
                            remark,
                            outcome
                        ]]
                    )

                else:
                    pass

                st.success("☑️ Self test results submitted")

        else:
            st.error("Incorrect username & password")

# -- body setup ----------------------------------------------------------------

if current_user is None:
    pass

else:
    if current_user["Password"] == password:

        col1, col2, col3 = st.columns((4, 1, 1))

        with col1:
            select_week = st.select_slider(
                "Week Number",
                weeks_df.index.tolist(),
                value=max(active_weeks),
                help="filter graph by week number"
            )

        with col2:
            select_year = st.selectbox("Year", [2021, curr_year], index=1)

        with col3:
            st.write("")
            st.write("")
            if st.button("Refresh"):
                st.experimental_show()

        if df.empty:
            pass
        else:

            st.altair_chart(
                get_graph(df, names=names),
                use_container_width=True
            )

        st.write(f"""### Records *(Source: [Gsheet]({config.GSHEET_URL}))*""")

        # style table: create non-current week as opague

        st.dataframe(df.style.apply(
            lambda s: ((df["Year"] <= curr_year) & (df["Week"] < curr_week))
            .map({True: "opacity: 20%;", False: ""})
        ))

        with st.expander("Ref. Table: Week Number-Dates"):
            st.dataframe(weeks_df)
