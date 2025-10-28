import streamlit as st
import pandas as pd
import os
from datetime import datetime, date
from config import load_config, save_config, CONFIG_FILE
import hashlib

# --- Load configuration ---
if 'config' not in st.session_state:
    st.session_state.config = load_config()

# --- Authentication settings ---
PASSWORD_HASH = st.session_state.config["password_hash"]

# --- Authentication functions ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        
    if st.session_state.authenticated:
        return True

    password = st.sidebar.text_input("Enter password to modify data", type="password")
    if password:
        if hashlib.sha256(password.encode()).hexdigest() == PASSWORD_HASH:
            st.session_state.authenticated = True
            st.rerun()
            return True
        else:
            st.sidebar.error("Invalid password")
    return False

# --- Data persistence ---
DATA_FILE = "pocket_money_data.csv"

def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
    else:
        return pd.DataFrame(columns=["child", "amount", "reason", "timestamp"])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

def add_transaction(df, child, amount, reason):
    new_entry = {
        "child": child.strip().title(),
        "amount": amount,
        "reason": reason,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
    save_data(df)
    return df

def get_balance(df, child):
    return df[df["child"] == child]["amount"].sum()

# --- Auto Deposit Processing ---
def process_auto_deposits():
    config = st.session_state.config
    today = date.today()
    last_deposit = datetime.strptime(config["last_auto_deposit"], "%Y-%m-%d").date()
    
    # Check if we're in a new month compared to last deposit
    if (today.year, today.month) > (last_deposit.year, last_deposit.month):
        df = load_data()
        for child, amount in config["auto_deposits"].items():
            df = add_transaction(df, child, amount, "Monthly Auto Deposit")
        
        config["last_auto_deposit"] = today.strftime("%Y-%m-%d")
        save_config(config)
        return True
    return False

# --- Streamlit UI ---
st.set_page_config(page_title="Kids Pocket Money", page_icon="💰", layout="centered")

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
    }
    .stMetric {
        padding: 15px;
        border-radius: 10px;
        background-color: var(--background-color);
        border: 1px solid var(--primary-color);
    }
    div[data-testid="stDataFrame"] {
        padding: 10px;
        border-radius: 10px;
        border: 1px solid var(--primary-color);
    }
    .stSidebar {
        background-color: var(--background-color);
    }
    h1, h2, h3 {
        color: var(--text-color);
    }
    .metric-card {
        background-color: var(--background-color);
        border: 1px solid var(--primary-color);
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Kids Pocket Money Manager")

# Load data
df = load_data()

# Sidebar menu
menu = st.sidebar.radio("Menu", ["Dashboard", "Add Transaction", "Summary & Charts", "History"])

# --- Dashboard ---
if menu == "Dashboard":
    st.header("Current Balances")
    
    if df.empty:
        st.info("No data yet. Add a transaction to get started.")
    else:
        st.markdown("### Current Account Status")
        balances = df.groupby("child")["amount"].sum().reset_index().sort_values("child")
        
        # Create columns for each child
        cols = st.columns(len(balances))
        for idx, (_, row) in enumerate(balances.iterrows()):
            with cols[idx]:
                st.markdown(f"### {row['child']}")
                st.metric(
                    label="Balance",
                    value=f"R {row['amount']:,.2f}",
                    delta=f"R {df[df['child'] == row['child']].tail(1)['amount'].values[0]:,.2f} last transaction"
                )

# --- Add Transaction ---
elif menu == "Add Transaction":
    st.header("Add or Update Pocket Money")
    
    if not check_password():
        st.warning("Please enter the password to add transactions")
        st.stop()
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        kids = sorted(df["child"].unique())
        option = st.radio("Select Option", ["Choose existing", "Add new"], 
                         horizontal=True)
    
    with col2:
        if option == "Choose existing" and kids:
            child = st.selectbox("Select child", kids,
                               placeholder="Choose a child")
        else:
            child = st.text_input("Enter new child's name",
                                placeholder="Enter name")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        amount = st.number_input(
            "Amount",
            step=1.0,
            help="Positive = add funds, Negative = spend funds"
        )
    with col2:
        reason = st.text_input(
            "Reason",
            placeholder="e.g., 'Allowance', 'Candy', 'Chores'"
        )

    if st.button("Save Transaction"):
        if not str(child or "").strip():
            st.warning("Please enter a child's name.")
        elif amount == 0:
            st.warning("Amount cannot be zero.")
        else:
            df = add_transaction(df, child, amount, reason)
            st.success(f"Transaction added for {child}: {amount:+.2f}")
            st.balloons()

# --- Summary & Charts ---
elif menu == "Summary & Charts":
    st.header("Pocket Money Overview")

    if df.empty:
        st.info("No transactions yet. Add some to see the charts.")
    else:
        st.markdown("---")
        selected_child = st.selectbox("Select child", sorted(df["child"].unique()))
        
        child_data = df[df["child"] == selected_child].sort_values("timestamp")
        
        # Enhanced metrics
        total_earned = child_data[child_data["amount"] > 0]["amount"].sum()
        total_spent = child_data[child_data["amount"] < 0]["amount"].sum()
        balance = child_data["amount"].sum()
        
        st.markdown("### Financial Overview")
        cols = st.columns(3)
        with cols[0]:
            st.metric("Total Earned", f"R {total_earned:,.2f}",
                     delta="Income", delta_color="normal")
        with cols[1]:
            st.metric("Total Spent", f"R {abs(total_spent):,.2f}",
                     delta="Expenses", delta_color="inverse")
        with cols[2]:
            st.metric("Current Balance", f"R {balance:,.2f}",
                     delta=f"R {child_data['amount'].iloc[-1]:,.2f} last change")
        
        st.markdown("---")
        st.markdown("### Balance History")
        child_data["running_balance"] = child_data["amount"].cumsum()
        st.line_chart(
            child_data.set_index("timestamp")["running_balance"],
            use_container_width=True,
            height=400,
        )

        # --- Detail view ---
        with st.expander("Transaction Details"):
            st.dataframe(child_data.sort_values("timestamp", ascending=False), use_container_width=True)

# --- History ---
elif menu == "History":
    st.header("All Transactions")
    
    if df.empty:
        st.info("No data available.")
    else:
        show_all = st.checkbox("Show all children", value=True)
        if show_all:
            df_filtered = df.copy()
        else:
            selected_child = st.selectbox("Select child", sorted(df["child"].unique()))
            df_filtered = df[df["child"] == selected_child]

        st.dataframe(df_filtered.sort_values("timestamp", ascending=False), use_container_width=True)

        # Modified clear data section
        if st.session_state.authenticated:
            if "show_confirm" not in st.session_state:
                st.session_state.show_confirm = False

            if not st.session_state.show_confirm:
                if st.button("Clear All Data"):
                    st.session_state.show_confirm = True
                    st.rerun()
            else:
                st.warning("⚠️ Are you sure you want to delete ALL records? This cannot be undone.")
                col1, col2 = st.columns(2)
                if col1.button("Yes, delete everything"):
                    if os.path.exists(DATA_FILE):
                        os.remove(DATA_FILE)
                    st.session_state.show_confirm = False
                    st.rerun()
                if col2.button("No, keep my data"):
                    st.session_state.show_confirm = False
                    st.rerun()

# --- Auto Deposit Settings ---
if check_password():
    st.sidebar.markdown("---")
    st.sidebar.header("Auto Deposit Settings")
    
    config = st.session_state.config
    auto_deposits = config["auto_deposits"]
    
    # Show current auto-deposits
    st.sidebar.subheader("Current Auto-deposits")
    for child, amount in auto_deposits.items():
        st.sidebar.text(f"{child}: R{amount}")
    
    # Add new auto-deposit
    st.sidebar.subheader("Add Auto-deposit")
    new_child = st.sidebar.text_input("Child name")
    new_amount = st.sidebar.number_input("Monthly amount", min_value=0)
    
    if st.sidebar.button("Save Auto-deposit"):
        if new_child and new_amount > 0:
            auto_deposits[new_child.strip().title()] = new_amount
            save_config(config)
            st.sidebar.success("Auto-deposit configured!")
            st.rerun()

# Process auto-deposits at the start
if process_auto_deposits():
    st.success("Monthly auto-deposits have been processed!")
