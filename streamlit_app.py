import streamlit as st
from googleapiclient.discovery import Resource

import config
from database import connect_to_gsheet
from get_data import get_data, get_users, get_weeks

import pandas as pd
import numpy as np
import altair as alt


st.set_page_config(
    page_title="COVID Self Test Reporting",
    layout="wide",
    page_icon="☠️"
)


# -- Setup ---------------------------------------------------------------------

df = get_data(connect_to_gsheet())
names, users = get_users(connect_to_gsheet())
weeks_df, active_weeks = get_weeks()


st.markdown("# COVID-19 Self-test Declaration Tracker")

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


# -- Update data ---------------------------------------------------------------

def add_entry(conn, row) -> None:
    """ Add entry to dB

    :param conn: existing connection via google api v4
    :param row: row details to be submitted into dB
    :return: extracted list of weeks and active weeks (less than current week)
    """

    conn.values().append(
        spreadsheetId=config.SPREADSHEET_ID,
        range=f"{config.SHEET_NAME}!A:F",
        body=dict(values=row),
        valueInputOption="USER_ENTERED",
    ).execute()


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


# -- Sidebar setup -------------------------------------------------------------

with st.sidebar:

    # -- Login -----------------------------------------------------------------

    with st.expander("🔒 User Login", expanded=True):
        username, password = st.text_input("Username"), st.text_input("Password")

    current_user = users.get(username)  # verifies if existing user

    if username == "" and password == "":
        st.info("Key in username & password")

    else:
        if (current_user["Password"] if current_user is not None else None) == password:
            current_user_name = current_user["Name"]
            st.success(f"Logged in as {current_user_name}")

# -- submission form -----------------------------------------------------------

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
                        max_value=config.today,
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

                # add entry (or overwrite existing) upon submission - if existing, then amend else append

                checker = df.apply(lambda x: f"{x['Year']}-{x['Week']}-{x['Member']}", axis=1).tolist() if not df.empty else [None]

                if f"{date.year}-{week}-{current_user_name}" not in checker:
                    add_entry(
                        connect_to_gsheet(),
                        [[
                            config.now.strftime("%Y-%m-%d %H:%M"),
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

                st.success("☑️ Self test results submitted")

        else:
            st.error("Incorrect username & password")


# -- Body setup ----------------------------------------------------------------

if (current_user["Password"] if current_user else None) is not None:

    col1, col2, col3 = st.columns((4, 1, 1))

    with col1:
        select_week = st.select_slider(
            "Week Number",
            weeks_df.index.tolist(),
            value=max(active_weeks),
            help="filter graph by week number"
        )

    with col2:
        select_year = st.selectbox("Year", [2021, config.curr_year], index=1)

    with col3:
        st.write("")
        st.write("")
        if st.button("Refresh"):
            st.experimental_show()

    if df.empty:
        pass

    else:
        st.altair_chart(get_graph(df, names=names), use_container_width=True)

    # style table: create non-current week as opague

    st.write(f"""### Records *(Source: [Gsheet]({config.GSHEET_URL}))*""")

    st.dataframe(df.style.apply(
        lambda s: ((df["Year"] <= config.curr_year) & (df["Week"] < config.curr_week))
        .map({True: "opacity: 20%;", False: ""})
    ))

    with st.expander("Ref. Table: Week Number-Dates"):
        st.dataframe(weeks_df)
