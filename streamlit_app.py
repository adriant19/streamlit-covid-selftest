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
curr_year, curr_week, _ = datetime.datetime.today().date().isocalendar()


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

    return df.sort_values(["Year", "Week", "Log Datetime"], ascending=[False, False, True])


def get_weeks(conn) -> pd.DataFrame:
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

    df = pd.DataFrame(values["values"])
    df.columns = df.iloc[0]
    df = df[1:].astype({
        "week_number": int,
        "start_date": "datetime64[ns]",
        "end_date": "datetime64[ns]"
    })

    # get active weeks that can be selected

    active_weeks = df[df["week_number"] <= curr_week].sort_values("week_number", ascending=False)["week_number"].values

    return df.set_index("week_number"), active_weeks


def get_users(conn) -> list:
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

    # if existing, then amend else append

    check = get_data(conn)

    check_dict = check.set_index(
        check.apply(
            lambda x: f"{x['Year']}-{x['Week']}-{x['Member']}",
            axis=1
        )
    ).to_dict("index")

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

    days_col = df.apply(lambda x: pd.Series(x["Days"].split(", ")), axis=1).fillna("")

    df1 = pd.concat([df[["Year", "Week", "Member", "Result"]], days_col], axis=1).set_index(["Year", "Week", "Member", "Result"])
    df2 = pd.DataFrame(df1.stack()).rename(columns={0: "Days"}).reset_index(level=4, drop=True).reset_index()

    df3 = df2[(df2["Week"] == int(week)) & (df2["Days"] != "")]

    plot_df = pd.merge(names.rename("Member"), df3, how="left", on="Member")

    plot_df["Legend"] = np.where(plot_df["Days"].isna(), "Unreported", plot_df["Result"])

    fig = (
        alt.Chart(plot_df, title=f"Week {week} - Self Test Reporting")
        .mark_circle(size=200)
        .encode(
            x="Member",
            y=alt.Y("Days", sort=["Mon", "Tue", "Wed", "Thu", "Fri"]),
            color=alt.Color("Legend", scale=alt.Scale(range=["steelblue", "#D35400", "chartreuse"], domain=["Unreported", "Positive (T)", "Negative (C)"]))
        )
        .properties(height=500)
        .interactive()
    )

    return fig


# -- header setup --------------------------------------------------------------

header1, header2 = st.columns((1, 3))

with header1:
    st.text("___")
    st.image(Image.open("shopee_logo_en_email.png"), width=200)

with header2:
    st.markdown(f"""# Marketing Analytics
    \nThis app records the team's self reported test kit results for COVID-19 (per week).
    \n*now*: `{datetime.datetime.now(tz)}`
    """)

st.write("***")

# -- sidebar setup -------------------------------------------------------------

weeks_df, active_weeks = get_weeks(connection.connect_to_gsheet())

with st.sidebar:

    # -- perform login

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

            #  --submission form -----------------------------------------------

            with st.form(key="annotation"):

                st.subheader("User Input Function")

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

                st.success("☑️ Self test results submitted")
        else:
            st.error("Incorrect username & password")

# -- body setup ----------------------------------------------------------------

# get data - regardless if authentication performed

df = get_data(connection.connect_to_gsheet())

if current_user is None:
    pass

else:
    if verified:

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

if st.button("Rerun App"):
    st.experimental_show()
