import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import sqlite3
import os  # ✅ ADDED

from utils.filters import apply_filters
from utils.preprocessing import validate_dataset, preprocess_data
from utils.segmentation import segment_customers

# ✅ MUST BE FIRST
st.set_page_config(
    page_title="Customer Value Segmentation",
    layout="wide"
)

# ================= LOGIN DATABASE =================
conn = sqlite3.connect('database.db', check_same_thread=False)
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS users (
    username TEXT,
    password TEXT
)
''')
conn.commit()

def add_user(username, password):
    c.execute('INSERT INTO users VALUES (?, ?)', (username, password))
    conn.commit()

def login_user(username, password):
    c.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password))
    return c.fetchone()

# ================= USER DATA FUNCTIONS (ADDED) =================
DATA_FOLDER = "user_data"

if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

def get_user_file(username):
    return os.path.join(DATA_FOLDER, f"{username}.csv")

# ================= SESSION =================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# ================= LOGIN UI =================
menu = ["Login", "Sign Up"]
choice = st.sidebar.selectbox("Menu", menu)

if not st.session_state.logged_in:

    st.title("🔐 Customer Segmentation Login")

    if choice == "Login":
        username = st.text_input("Username")
        password = st.text_input("Password", type='password')

        if st.button("Login"):
            if login_user(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Invalid credentials")

    elif choice == "Sign Up":
        new_user = st.text_input("New Username")
        new_pass = st.text_input("New Password", type='password')

        if st.button("Sign Up"):
            add_user(new_user, new_pass)
            st.success("Account created")

    st.stop()


# ================= LOAD USER DATA (ADDED) =================
user_file = get_user_file(st.session_state.username)

if os.path.exists(user_file):
    try:
        saved_df = pd.read_csv(user_file)
        st.session_state.client_data = saved_df
    except:
        pass


# ================= YOUR ORIGINAL CODE STARTS (UNCHANGED) =================

st.markdown("""
<style>
[data-testid="metric-container"] {
    background-color: #f5f7fa;
    border-radius: 8px;
    padding: 10px;
}
</style>
""", unsafe_allow_html=True)


st.title("📊 Customer Value Segmentation System")

# -----------------------------
# Sidebar Navigation
# -----------------------------
st.sidebar.title("Navigation")
st.sidebar.write(f"👤 Logged in as: {st.session_state.username}")

# ✅ DELETE BUTTON (ADDED ONLY)
if st.sidebar.button("Delete My Data"):
    if os.path.exists(user_file):
        os.remove(user_file)
        st.session_state.client_data = None
        st.success("Your data has been deleted")

page = st.sidebar.radio(
    "Go to",
    [
        "About & Sample Data",
        "Upload Client Dataset",
        "Customer Segmentation",
        "Business Insights"
    ]
)

# -----------------------------
# Session State (store client data)
# -----------------------------
if "client_data" not in st.session_state:
    st.session_state.client_data = None


# -----------------------------
# PAGE 1: ABOUT & SAMPLE DATA
# -----------------------------
if page == "About & Sample Data":
    st.subheader("🔍 About This Application")
    st.write(
        """
        This application helps businesses identify **Low**, **Medium**, and **High Value Customers**
        based on purchase behavior using data-driven clustering.
        """
    )

    st.subheader("📁 Sample Dataset (Demo)")
    sample_df = pd.read_csv("data/sample_customer_data.csv")

    sample_segmented = segment_customers(sample_df)
    st.dataframe(sample_df.head(50))


    st.info(
        """
        📌 **Client Dataset Requirements**
        - customer_id
        - recency (days since last purchase)
        - frequency (number of purchases)
        - monetary (total spend)
        """
    )

# -----------------------------
# PAGE 2: UPLOAD CLIENT DATASET
# -----------------------------
elif page == "Upload Client Dataset":
    st.subheader("📤 Upload Client Dataset")

    uploaded_file = st.file_uploader(
        "Upload CSV file",
        type=["csv"]
    )

    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)

            df = validate_dataset(df)
            df = preprocess_data(df)

            segmented_df = segment_customers(df)

            st.subheader("📊 Quick Insights (Preview)")

            col1, col2 = st.columns(2)

            with col1:
                st.write("Customer Segment Distribution")
                st.bar_chart(segmented_df["customer_segment"].value_counts())

            with col2:
                st.write("Average Spend by Segment")
                st.bar_chart(
                    segmented_df.groupby("customer_segment")["monetary"].mean()
                )

            st.session_state.client_data = segmented_df

            # ✅ SAVE USER DATA (ADDED ONLY)
            segmented_df.to_csv(user_file, index=False)

            st.success("✅ Dataset uploaded and processed successfully!")

            st.dataframe(segmented_df.head(50))

            st.download_button(
                label="⬇️ Download Segmented Dataset",
                data=segmented_df.to_csv(index=False),
                file_name="segmented_customers.csv",
                mime="text/csv"
            )

        except Exception as e:
            st.error(str(e))

# -----------------------------
# PAGE 3: CUSTOMER SEGMENTATION
# -----------------------------
elif page == "Customer Segmentation":
    st.subheader("🧠 Customer Segmentation")

    if st.session_state.client_data is None:
        st.warning("⚠️ Please upload a client dataset first.")
    else:
        df = st.session_state.client_data

        st.sidebar.subheader("🔎 Filters")

        segment_filter = st.sidebar.multiselect(
            "Customer Segment",
            options=df["customer_segment"].unique(),
            default=df["customer_segment"].unique()
        )

        min_monetary, max_monetary = st.sidebar.slider(
            "Monetary Range",
            int(df["monetary"].min()),
            int(df["monetary"].max()),
            (
                int(df["monetary"].min()),
                int(df["monetary"].max())
            )
        )

        min_freq, max_freq = st.sidebar.slider(
            "Frequency Range",
            int(df["frequency"].min()),
            int(df["frequency"].max()),
            (
                int(df["frequency"].min()),
                int(df["frequency"].max())
            )
        )

        if "region" in df.columns:
            region_filter = st.sidebar.multiselect(
                "Region",
                options=df["region"].unique(),
                default=df["region"].unique()
            )
        else:
            region_filter = None

        if "channel" in df.columns:
            channel_filter = st.sidebar.multiselect(
                "Channel",
                options=df["channel"].unique(),
                default=df["channel"].unique()
            )
        else:
            channel_filter = None

        filtered_df = apply_filters(
            df,
            segment_filter,
            min_monetary,
            max_monetary,
            min_freq,
            max_freq
        )

        if region_filter:
            filtered_df = filtered_df[filtered_df["region"].isin(region_filter)]

        if channel_filter:
            filtered_df = filtered_df[filtered_df["channel"].isin(channel_filter)]

        st.subheader("📊 Filtered Results")
        st.dataframe(filtered_df)

        st.subheader("📊 Segment Distribution (Filtered)")
        st.bar_chart(filtered_df["customer_segment"].value_counts())

        if "region" in filtered_df.columns:
            st.subheader("📍 High-Value Customers by Region")
            st.bar_chart(
                filtered_df[filtered_df["customer_segment"] == "High Value"]["region"]
                .value_counts()
            )

        if "channel" in filtered_df.columns:
            st.subheader("🛒 High-Value Customers by Channel")
            st.bar_chart(
                filtered_df[filtered_df["customer_segment"] == "High Value"]["channel"]
                .value_counts()
            )

# -----------------------------
# PAGE 4: BUSINESS INSIGHTS (UNCHANGED)
# -----------------------------
elif page == "Business Insights":
    st.subheader("📈 Business Insights & KPIs")

    if st.session_state.client_data is None:
        st.warning("⚠️ Please upload a client dataset first.")
    else:
        df = st.session_state.client_data

        total_customers = len(df)
        high_value_count = (df["customer_segment"] == "High Value").sum()
        medium_value_count = (df["customer_segment"] == "Medium Value").sum()
        low_value_count = (df["customer_segment"] == "Low Value").sum()

        total_revenue = df["monetary"].sum()
        high_value_revenue = df[df["customer_segment"] == "High Value"]["monetary"].sum()

        col1, col2, col3 = st.columns(3)

        col1.metric("Total Customers", total_customers)
        col2.metric("High-Value Customers", high_value_count)
        col3.metric("Revenue from High-Value", f"{(high_value_revenue / total_revenue) * 100:.2f}%")

        st.subheader("📊 Revenue Contribution by Segment")

        revenue_by_segment = (
            df.groupby("customer_segment")["monetary"]
            .sum()
            .clip(lower=0)
        )

        st.bar_chart(revenue_by_segment)

        st.info(
            """
            💡 **Business Insight**  
            A small proportion of customers typically contributes a large share of total revenue.
            Businesses should prioritize **retention and personalized marketing** for high-value customers.
            """
        )

        st.subheader("🚀 Recommendations to Increase High-Value Customers")

        st.markdown("""
        ### 🎯 Key Strategies

        **1️⃣ Improve Retention**
        - Offer loyalty programs for medium-value customers
        - Personalized discounts for repeat buyers

        **2️⃣ Increase Purchase Frequency**
        - Email & SMS reminders
        - Subscription-based offers

        **3️⃣ Boost Monetary Value**
        - Bundle products
        - Upselling & cross-selling

        **4️⃣ Focus on High-Performing Regions**
        - Allocate more marketing budget to regions with more high-value customers

        **5️⃣ Strengthen Best Channels**
        - Improve UX for high-performing channels (Online / Store)
        - Promote digital channels if online performs better

        **6️⃣ Convert Medium → High Value**
        - Target medium-value customers with exclusive offers
        - Provide early-access deals
        """)

# ================= LOGOUT =================
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()
