import streamlit as st
import connection
import config

from PIL import Image
import datetime
import pytz
import pandas as pd
import numpy as np
import altair as alt

# -- global variables, settings & connection setup -----------------------------

st.set_page_config(page_title="COVID Self Test Reporting", layout="wide", page_icon="☠️")

tz = pytz.timezone("Asia/Kuala_Lumpur")
curr_year, curr_week, _ = datetime.datetime.now(tz).date().isocalendar()


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


@st.cache(ttl=60)
def get_weeks(conn):
    """ Read weeks list from dB

    :param conn: existing connection via google api v4
    :return: extracted list of weeks and active weeks (less than current week)
    """

    values = (
        conn.values().get(
            spreadsheetId=config.SPREADSHEET_ID,
            range=f"Weeks!A:C",
        ).execute()
    )

    weeks_df = pd.DataFrame(values["values"])
    weeks_df.columns = weeks_df.iloc[0]
    weeks_df = weeks_df[1:].astype({
        "week_number": int,
        "start_date": "datetime64[ns]",
        "end_date": "datetime64[ns]"
    })

    # get active weeks that can be selected

    active_weeks = list(filter(lambda x: x <= curr_week, weeks_df["week_number"].tolist()))

    return weeks_df.set_index("week_number"), sorted(active_weeks, reverse=True)


@st.cache(ttl=60)
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

    df1 = pd.concat(
        [
            df[["Year", "Week", "Member", "Result"]],
            df.apply(lambda x: pd.Series(x["Days"].split(", ")), axis=1).fillna("")
        ],
        axis=1
    ).set_index(["Year", "Week", "Member", "Result"])

    df2 = pd.DataFrame(df1.stack()).rename(columns={0: "Days"}).reset_index(level=4, drop=True).reset_index()

    plot_df = pd.merge(
        names.rename("Member"),
        df2[df2["Week"] == int(select_week)],
        how="left", on="Member"
    ).query("Days != ''").fillna(value={"Days": ""})

    plot_df["Legend"] = np.where(
        (plot_df["Result"].isna()) & (plot_df["Days"] == ""),
        "Untested",
        plot_df["Result"]
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

df = get_data(connection.connect_to_gsheet())


# -- header setup --------------------------------------------------------------

st.markdown(f"""# Marketing Analytics
\nThis app records the team's self reported test kit results for COVID-19 (per week).
\n*now*: `{datetime.datetime.now(tz)}`
""")

st.write("***")

# -- sidebar setup -------------------------------------------------------------

weeks_df, active_weeks = get_weeks(connection.connect_to_gsheet())

with st.sidebar:
    st.image(Image.open("shopee_logo_en_email.png"), width=100)

    # -- perform login -------------------------------------------------------------

    st.subheader("🔒 User Login")
    username = st.text_input("Username")
    pwd = st.text_input("Password")

    # verifies if existing user (gets name & password)

    names, users = get_users(connection.connect_to_gsheet())
    current_user = users.get(username)

    if current_user is None:
        if username == "" and pwd == "":
            st.info("Key in username & password")
        else:
            st.error("Incorrect username & password")

    else:
        verified = current_user["Password"] == pwd
        current_user_name = current_user['Name']

        if verified:
            st.success(f"Logged in as {current_user_name}")

#  --submission form -----------------------------------------------------------

            with st.form(key="annotation"):
                st.subheader("User Input Function")

                # fields needed

                week = st.selectbox(
                    "Week Number",
                    active_weeks,
                    index=0,
                    help="week to report self test"
                )

                date = st.date_input(
                    "Self Test Date",
                    max_value=datetime.datetime.now(tz),
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

                checker = df.apply(lambda x: f"{x['Year']}-{x['Week']}-{x['Member']}", axis=1).tolist()

                if f"{date.year}-{week}-{current_user_name}" not in checker:
                    add_entry(
                        connection.connect_to_gsheet(),
                        [[
                            datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M"),
                            str(date.year),
                            week,
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
    if verified:

        select_week = st.select_slider(
            "Week Number",
            range(1, 54),
            # active_weeks.tolist(),
            value=max(active_weeks),
            help="filter graph by week number"
        )

        st.altair_chart(
            get_graph(df, names=names),
            use_container_width=True
        )

        st.write(f"""### Records *(Source: [Gsheet]({config.GSHEET_URL}))*""")

        # style table: create non-current week as opague

        st.dataframe(df.style.apply(
            lambda s: ((df["Year"] != curr_year) & (df["Week"] != curr_week))
            .map({True: "opacity: 20%;", False: ""})
        ))

        with st.expander("Ref. Table: Week Number-Dates"):
            st.dataframe(weeks_df)


# -- fallback logic: rerun app in case of errors -------------------------------

with st.expander("Changelog"):
    st.text("""
    [Pending] logic to amend entry rows if a user is resubmitting for a given year and week
    [Done] Only submits new entries if have not declared by user for a given year-week
    [Done] Graph now captures users that have not declared status
    """)

if st.button("Rerun App"):
    st.experimental_show()
