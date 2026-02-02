import streamlit as st
import pandas as pd
import re
from datetime import datetime, timedelta

# ===============================
# PAGE CONFIG
# ===============================
st.set_page_config(page_title="Delivery Dashboard", layout="wide")
st.title("📦 Delivery Dashboard")

# ===============================
# GLOBAL STYLE
# ===============================
st.markdown("""
<style>
.order-card {
    background-color: #ffffff;
    color: #000000;
    padding: 16px;
    border-radius: 10px;
    margin-bottom: 12px;
    border: 1px solid #e0e0e0;
}
.order-meta {
    font-size: 14px;
    color: #333333;
}
</style>
""", unsafe_allow_html=True)

# ===============================
# CONFIG
# ===============================
CSV_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1SuOaiRQTYPLwt51n9a8vmHDLz-AG9fFM8Hhp1B7a-FM/"
    "export?format=csv&gid=754482935"
)
ALERT_BEFORE = timedelta(hours=2)

# ===============================
# LOAD DATA
# ===============================
@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    df = pd.read_csv(CSV_URL)

    df["Requested Delivery Date"] = pd.to_datetime(
        df["Requested Delivery Date"],
        errors="coerce",
        dayfirst=True
    )
    df = df[df["Requested Delivery Date"].notna()]

    def extract_time(text):
        if pd.isna(text):
            return "23:59"
        text = str(text)
        m = re.search(r"(\d{1,2})[:.](\d{2})", text)
        if m:
            h, mnt = m.groups()
            return f"{int(h):02d}:{mnt}"
        m = re.search(r"บ่าย\s*(\d{1,2})", text)
        if m:
            return f"{int(m.group(1)) + 12:02d}:00"
        return "23:59"

    df["delivery_time"] = pd.to_datetime(
        df["Order Remarks"].apply(extract_time),
        format="%H:%M",
        errors="coerce"
    ).dt.time

    df["delivery_time"] = df["delivery_time"].fillna(
        datetime.strptime("23:59", "%H:%M").time()
    )

    df["delivery_datetime"] = df.apply(
        lambda r: datetime.combine(
            r["Requested Delivery Date"], r["delivery_time"]
        ),
        axis=1
    )

    return df

# ===============================
# HELPERS
# ===============================
def get_order_icon(delivery_dt, now):
    diff = delivery_dt - now
    if diff <= ALERT_BEFORE:
        return "🚨"
    elif delivery_dt.date() == now.date():
        return "⏰"
    else:
        return "📅"

def render_cards(df_orders, now):
    for _, r in df_orders.iterrows():
        icon = get_order_icon(r["delivery_datetime"], now)
        st.markdown(f"""
        <div class="order-card">
            <strong>{icon} 📄 {r.get('SO Number','')}</strong><br>
            🧾 {r.get('Product','')}<br>
            <div class="order-meta">
                👤 ลูกค้า: {r.get('Customers','ไม่ระบุ')}<br>
                ⏰ เวลาส่ง: {r['delivery_time']}
            </div>
        </div>
        """, unsafe_allow_html=True)

# ===============================
# LOAD
# ===============================
df = load_data()
now = datetime.now()
today = now.date()
tomorrow = today + timedelta(days=1)
end_7 = today + timedelta(days=7)

pending = df[df["delivery_datetime"] >= now]

today_df = pending[pending["Requested Delivery Date"].dt.date == today]
tomorrow_df = pending[pending["Requested Delivery Date"].dt.date == tomorrow]
week_df = pending[
    (pending["Requested Delivery Date"].dt.date > tomorrow) &
    (pending["Requested Delivery Date"].dt.date <= end_7)
]

near_df = pending[(pending["delivery_datetime"] - now) <= ALERT_BEFORE]

# ===============================
# SUMMARY
# ===============================
c1, c2, c3 = st.columns(3)
c1.metric("📦 วันนี้ต้องส่ง", len(today_df))
c2.metric("🚨 ใกล้ถึงเวลา (≤2ชม.)", len(near_df))
c3.metric("📊 ยังไม่ส่งทั้งหมด", len(pending))

st.divider()
st.info(
    "ℹ️ **หมายเหตุเรื่องเวลา 23:59**  \n"
    "หากออเดอร์ใดแสดงเวลาเป็น **23:59** "
    "หมายความว่าออเดอร์นั้น **ยังไม่ได้ระบุเวลาจัดส่งไว้ในเอกสาร**  \n"
    "ระบบจึงตั้งค่าเริ่มต้นเป็น 23:59 เพื่อให้ออเดอร์ยังแสดงในระบบ "
    "และไม่กระทบการแจ้งเตือน กรุณาตรวจสอบรายละเอียดเพิ่มเติมในเอกสารต้นทาง",
    icon="ℹ️"
)

# ===============================
# SEARCH
# ===============================
search = st.text_input("🔍 ค้นหา (SO Number / ลูกค้า / สินค้า)")

if search:
    pending = pending[
        pending["SO Number"].astype(str).str.contains(search, case=False, na=False) |
        pending["Customers"].astype(str).str.contains(search, case=False, na=False) |
        pending["Product"].astype(str).str.contains(search, case=False, na=False)
    ]

# ===============================
# TABS
# ===============================
tab_card, tab_table = st.tabs(["🧩 มุมมองการ์ด", "📊 มุมมองตาราง"])

with tab_card:
    st.subheader("📅 วันนี้ / พรุ่งนี้ / 7 วัน")
    render_cards(pending.sort_values("delivery_datetime"), now)

with tab_table:
    st.subheader("📊 ตารางออเดอร์ (สแกนเร็ว)")
    st.dataframe(
        pending[[
            "SO Number",
            "Product",
            "Customers",
            "Requested Delivery Date",
            "delivery_time"
        ]].sort_values("Requested Delivery Date"),
        use_container_width=True
    )

# ===============================
# WEB ALERT
# ===============================
if not near_df.empty:
    st.toast(
        f"🚨 มี {len(near_df)} ออเดอร์ใกล้ถึงเวลาส่ง!",
        icon="🚨"
    )
