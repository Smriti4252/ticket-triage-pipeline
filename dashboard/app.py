# app.py
# Streamlit Dashboard for Ticket Triage System
# Reads data from FastAPI endpoints and displays analytics

import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# ── Config ────────────────────────────────────────────────────────────
API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="Ticket Triage Dashboard",
    page_icon="🎫",
    layout="wide"
)

# ── Helper Functions ──────────────────────────────────────────────────
def fetch_stats():
    """Fetch aggregated stats from API."""
    try:
        response = requests.get(f"{API_BASE}/stats")
        return response.json()
    except Exception as e:
        st.error(f"API connection failed: {e}")
        return None


def fetch_tickets(status=None, category=None, priority=None):
    """Fetch tickets from API with optional filters."""
    try:
        params = {}
        if status:
            params['status'] = status
        if category:
            params['category'] = category
        if priority:
            params['priority'] = priority

        response = requests.get(f"{API_BASE}/tickets", params=params)
        data = response.json()
        return pd.DataFrame(data['tickets'])
    except Exception as e:
        st.error(f"Failed to fetch tickets: {e}")
        return pd.DataFrame()


def update_status(ticket_id, new_status):
    """Update ticket status via API."""
    try:
        response = requests.patch(
            f"{API_BASE}/tickets/{ticket_id}/status",
            json={"status": new_status}
        )
        return response.status_code == 200
    except:
        return False


# ── Header ────────────────────────────────────────────────────────────
st.title("🎫 Ticket Triage Dashboard")
st.caption("AI-powered support ticket classification and prioritization")

# ── Fetch Data ────────────────────────────────────────────────────────
stats = fetch_stats()

if not stats:
    st.warning("Could not connect to API. Make sure FastAPI server is running on port 8000.")
    st.stop()

# ── KPI Cards ─────────────────────────────────────────────────────────
st.subheader("Overview")
col1, col2, col3, col4 = st.columns(4)

total = stats['total']
high_count = next((x['count'] for x in stats['by_priority'] if x['priority'] == 'HIGH'), 0)
bug_count = next((x['count'] for x in stats['by_category'] if x['category'] == 'bug'), 0)
new_count = next((x['count'] for x in stats['by_status'] if x['status'] == 'new'), 0)

col1.metric("Total Tickets", total)
col2.metric("High Priority", high_count, delta="Needs attention", delta_color="inverse")
col3.metric("Bug Reports", bug_count)
col4.metric("Open (New)", new_count)

st.divider()

# ── Charts Row ────────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Tickets by Category")
    cat_df = pd.DataFrame(stats['by_category'])
    if not cat_df.empty:
        fig = px.pie(
            cat_df,
            names='category',
            values='count',
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("Tickets by Priority")
    pri_df = pd.DataFrame(stats['by_priority'])
    if not pri_df.empty:
        color_map = {'HIGH': '#FF4B4B', 'MEDIUM': '#FFA500', 'LOW': '#00CC96'}
        fig = px.bar(
            pri_df,
            x='priority',
            y='count',
            color='priority',
            color_discrete_map=color_map,
            text='count'
        )
        fig.update_traces(textposition='outside')
        fig.update_layout(showlegend=False, xaxis_title="Priority", yaxis_title="Count")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(pri_df, use_container_width=True, height=400)

st.divider()

# ── Ticket Queue ──────────────────────────────────────────────────────
st.subheader("Ticket Queue")

# Filters
filter_col1, filter_col2, filter_col3 = st.columns(3)

with filter_col1:
    filter_priority = st.selectbox(
        "Filter by Priority",
        ["All", "HIGH", "MEDIUM", "LOW"]
    )

with filter_col2:
    filter_category = st.selectbox(
        "Filter by Category",
        ["All", "billing", "bug", "feature_request", "account_issue", "general"]
    )

with filter_col3:
    filter_status = st.selectbox(
        "Filter by Status",
        ["All", "new", "in_review", "assigned", "resolved"]
    )

# Fetch filtered tickets
df = fetch_tickets(
    priority=filter_priority if filter_priority != "All" else None,
    category=filter_category if filter_category != "All" else None,
    status=filter_status if filter_status != "All" else None
)

if df.empty:
    st.info("No tickets found for selected filters.")
else:
    # Color code priority
    def color_priority(val):
        colors = {'HIGH': 'background-color: #FFE0E0', 'MEDIUM': 'background-color: #FFF3CD', 'LOW': 'background-color: #E8F5E9'}
        return colors.get(val, '')

    # Show relevant columns only
    display_cols = ['ticket_id', 'subject', 'category', 'priority', 'status', 'summary', 'created_at']
    display_df = df[display_cols] if all(c in df.columns for c in display_cols) else df

    st.dataframe(
        display_df.style.map(color_priority, subset=['priority']),
        use_container_width=True,
        height=400
    )

    st.caption(f"Showing {len(df)} tickets")

st.divider()

# ── Status Update ─────────────────────────────────────────────────────
st.subheader("Update Ticket Status")

update_col1, update_col2, update_col3 = st.columns([2, 2, 1])

with update_col1:
    ticket_id_input = st.text_input("Ticket ID", placeholder="e.g. TKT-1000")

with update_col2:
    new_status = st.selectbox(
        "New Status",
        ["new", "in_review", "assigned", "resolved"]
    )

with update_col3:
    st.write("")
    st.write("")
    if st.button("Update", type="primary"):
        if ticket_id_input:
            success = update_status(ticket_id_input, new_status)
            if success:
                st.success(f"{ticket_id_input} updated to '{new_status}'")
                st.rerun()
            else:
                st.error("Update failed. Check ticket ID.")
        else:
            st.warning("Enter a ticket ID first.")

st.divider()

# ── High Priority Alert ───────────────────────────────────────────────
with st.expander("🔴 High Priority Tickets (Open)", expanded=False):
    try:
        response = requests.get(f"{API_BASE}/tickets/priority/high")
        data = response.json()
        high_df = pd.DataFrame(data['tickets'])
        if high_df.empty:
            st.success("No open HIGH priority tickets!")
        else:
            st.warning(f"{data['total']} HIGH priority tickets need attention!")
            cols = ['ticket_id', 'subject', 'category', 'status', 'summary']
            st.dataframe(
                high_df[[c for c in cols if c in high_df.columns]],
                use_container_width=True
            )
    except Exception as e:
        st.error(f"Failed to load high priority tickets: {e}")