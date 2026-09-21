"""
Tasty Food — Staff Selection Commission
Control Room Meal Ordering System (Streamlit Version)
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import json
import io
import time
from supabase import create_client, Client

# ============================================================
# CONFIG
# ============================================================
st.set_page_config(
    page_title="Tasty Food — SSC",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

ADMIN_ID = "SANJANA"
KV_KEY = "tastyfood"
KV_ADMIN_KEY = "tastyfood_admin"
CONTACT_NAME = "Sanjana Chattopadhyay"
CONTACT_MOBILE = "8336816585"
ORG_NAME = "Staff Selection Commission"

QTY_ITEMS = [
    "roti", "banana", "boil egg", "boiled/fried egg", "dim toste", "toste ghuguni",
    "puri", "bhatura", "naan", "butter naan", "garlic naan", "tandoori roti",
    "aloo paratha", "paneer paratha", "samosa", "kachori", "idli", "vada",
    "egg roll", "gulab jamun", "rasgulla", "sandesh", "rasmalai",
]

DEFAULT_MENU = {
    "Breakfast": [
        "DIM TOSTE", "GHUGHNI", "TOSTE GHUGUNI", "BANANA", "BOIL EGG",
        "Kachuri", "Chola Bhatura", "Sandwich", "Idli", "Dhosa", "Others (Remarks)"
    ],
    "Lunch": {
        "Veg": [
            "DIM TOSTE", "TOSTE GHUGUNI", "Roti", "Dim Tadka", "Veg Thali",
            "Paneer Butter Masala", "Shahi Paneer", "Kadai Paneer", "Palak Paneer",
            "Matar Paneer", "Chole (Chickpea Curry)", "Rajma", "Dal Tadka",
            "Dal Makhani", "Aloo Gobi", "Aloo Matar", "Mix Veg", "Baingan Bharta",
            "Bhindi Masala", "Tandoori Roti", "Naan", "Butter Naan", "Garlic Naan",
            "Aloo Paratha", "Paneer Paratha", "Puri", "Bhatura"
        ],
        "Non-Veg": [
            "DIM TOSTE", "TOSTE GHUGUNI", "Roti", "Chicken Stew (with leg piece)",
            "Roti + Chicken Curry", "Chicken Curry", "Chicken Masala", "Butter Chicken",
            "Kadai Chicken", "Chicken Tikka", "Tandoori Chicken", "Chicken 65",
            "Chicken Korma", "Chicken Do Pyaza", "Chicken Thali", "Roti + Mutton Curry",
            "Mutton Curry", "Mutton Rogan Josh", "Mutton Korma", "Mutton Keema",
            "Mutton Kosha", "Mutton Thali", "Fish Thali", "Fish Curry", "Fish Fry",
            "Fish Masala", "Fish Kalia", "Fish Tikka", "Mustard Fish", "Fish Cutlet",
            "Egg Thali", "Egg Curry", "Egg Masala", "Egg Bhurji", "Egg Omelette",
            "Egg Roll", "Boiled/Fried Egg", "Prawn Curry", "Prawn Masala", "Prawn Fry",
            "Chilli Prawns", "Crab Curry", "Crab Masala"
        ],
        "Rice Veg": [
            "Steamed Rice", "Jeera Rice", "Veg Pulao", "Lemon Rice", "Curd Rice",
            "Veg Biryani", "Paneer Biryani", "Fried Rice (Veg)"
        ],
        "Rice Non-Veg": [
            "Chicken Biryani", "Mutton Biryani", "Fish Biryani", "Egg Biryani",
            "Prawn Biryani", "Fish/Prawn Biryani", "Chicken Fried Rice", "Egg Fried Rice"
        ],
    },
    "Other": [
        "Samosa", "Kachori", "Pakora", "Dhokla", "Poha", "Upma", "Idli",
        "Masala Dosa", "Vada", "Pav Bhaji", "Gulab Jamun", "Rasgulla", "Jalebi",
        "Kheer", "Gajar Ka Halwa", "Rasmalai", "Sandesh", "Cold Drinks",
        "Others (Remarks)"
    ],
}

# ============================================================
# HELPERS
# ============================================================
def seed_menu():
    m = {}
    for k, v in DEFAULT_MENU.items():
        if k == "Lunch":
            m["Lunch"] = {p: [{"name": n, "available": True} for n in items] for p, items in v.items()}
        else:
            m[k] = [{"name": n, "available": True} for n in v]
    return m


def normalize_state(raw):
    raw = raw if isinstance(raw, dict) else {}
    out = {
        "orders": raw.get("orders", []) if isinstance(raw.get("orders"), list) else [],
        "menu": None,
        "meta": raw.get("meta", {}),
    }
    menu = raw.get("menu")
    ok = (
        isinstance(menu, dict)
        and isinstance(menu.get("Breakfast"), list)
        and isinstance(menu.get("Other"), list)
        and isinstance(menu.get("Lunch"), dict)
    )
    out["menu"] = menu if ok else seed_menu()

    normalized_orders = []
    for o in out["orders"]:
        items = []
        for it in o.get("items", []) or []:
            if isinstance(it, dict):
                nm = str(it.get("name", "")).strip()
                try:
                    q = int(it.get("qty", 1))
                except Exception:
                    q = 1
                if q < 1:
                    q = 1
                if nm:
                    items.append({"name": nm, "qty": q})
            else:
                nm = str(it).strip()
                if nm:
                    items.append({"name": nm, "qty": 1})
        normalized_orders.append({
            "id": o.get("id") or f"{int(time.time()*1000)}-{id(o)}",
            "name": o.get("name", ""),
            "mobile": o.get("mobile", ""),
            "meal": o.get("meal", "-"),
            "preference": o.get("preference", "-"),
            "items": items,
            "remarks": o.get("remarks", ""),
            "date": o.get("date", ""),
            "time": o.get("time", ""),
            "timestamp": o.get("timestamp", ""),
            "status": o.get("status", "Pending"),
            "reply": o.get("reply", ""),
            "source": o.get("source", "member"),
        })
    out["orders"] = normalized_orders
    return out


def normalize_admin(raw):
    raw = raw if isinstance(raw, dict) else {}
    rates = raw.get("itemRates", {}) if isinstance(raw.get("itemRates"), dict) else {}
    clean = {}
    for k, v in rates.items():
        try:
            fv = float(v)
            if fv > 0:
                clean[k] = fv
        except Exception:
            pass
    misc = []
    for m in raw.get("miscExpenses", []) or []:
        try:
            amt = float(m.get("amount", 0))
        except Exception:
            amt = 0
        if m.get("description") and amt > 0:
            misc.append({
                "id": m.get("id") or f"{int(time.time()*1000)}-{id(m)}",
                "date": m.get("date", today_str()),
                "description": m.get("description", ""),
                "amount": amt,
                "timestamp": m.get("timestamp", datetime.now().isoformat()),
            })
    return {"itemRates": clean, "miscExpenses": misc, "meta": raw.get("meta", {})}


def today_str():
    return datetime.now().strftime("%d/%m/%Y")


def now_time():
    return datetime.now().strftime("%H:%M")


def local_iso(d: date):
    return d.strftime("%Y-%m-%d")


def ddmm_to_date(s):
    try:
        return datetime.strptime(s, "%d/%m/%Y").date()
    except Exception:
        return None


def date_to_ddmm(d: date):
    return d.strftime("%d/%m/%Y") if d else ""


def allows_qty(name):
    n = str(name or "").lower().strip()
    if n in QTY_ITEMS:
        return True
    if "roti" in n and "+" in n:
        return True
    return False


def is_remarks_item(n):
    import re
    return bool(re.search(r"others?\s*\(remarks?\)", str(n), re.I))


def money(n):
    try:
        return f"₹{float(n):.2f}"
    except Exception:
        return "₹0.00"


def get_date_bounds(kind):
    today = date.today()
    if kind == "all":
        return None, None
    if kind == "today":
        return today, today
    if kind == "yesterday":
        y = today - timedelta(days=1)
        return y, y
    if kind == "week":
        mon = today - timedelta(days=today.weekday())
        return mon, today
    if kind == "month":
        return today.replace(day=1), today
    if kind == "lastmonth":
        first_this = today.replace(day=1)
        last_prev = first_this - timedelta(days=1)
        return last_prev.replace(day=1), last_prev
    return None, None


def in_date_range(date_str, from_d, to_d):
    d = ddmm_to_date(date_str)
    if not d:
        return False
    if from_d and d < from_d:
        return False
    if to_d and d > to_d:
        return False
    return True


# ============================================================
# SUPABASE
# ============================================================
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    if not url or not key:
        return None
    return create_client(url, key)


def cloud_read(key):
    sb = get_supabase()
    if not sb:
        return None
    try:
        res = sb.table("kv_store").select("value").eq("key", key).execute()
        if res.data:
            return res.data[0]["value"]
    except Exception as e:
        st.warning(f"Cloud read failed: {e}")
    return None


def cloud_write(key, value):
    sb = get_supabase()
    if not sb:
        st.error("Supabase not configured. Add credentials in secrets.toml")
        return False
    try:
        sb.table("kv_store").upsert(
            {"key": key, "value": value, "updated_at": datetime.now().isoformat()}
        ).execute()
        return True
    except Exception as e:
        st.error(f"Cloud save failed: {e}")
        return False


# ============================================================
# SESSION STATE / DATA LOADING
# ============================================================
def init_session():
    defaults = {
        "logged_in": False,
        "is_admin": False,
        "member": None,
        "state": None,
        "admin_state": None,
        "page": "welcome",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def load_all_data():
    raw = cloud_read(KV_KEY)
    st.session_state.state = normalize_state(raw)
    raw_admin = cloud_read(KV_ADMIN_KEY)
    st.session_state.admin_state = normalize_admin(raw_admin)


def save_state():
    st.session_state.state["meta"] = {"updated": datetime.now().isoformat()}
    cloud_write(KV_KEY, st.session_state.state)


def save_admin_state():
    st.session_state.admin_state["meta"] = {"updated": datetime.now().isoformat()}
    cloud_write(KV_ADMIN_KEY, st.session_state.admin_state)


# ============================================================
# UI HELPERS
# ============================================================
def header(title, subtitle=""):
    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg,#172554,#1e3a8a);color:#fff;
                    padding:14px 20px;border-radius:12px;margin-bottom:18px;
                    box-shadow:0 8px 24px -8px rgba(30,58,138,.4)">
            <div style="font-size:18px;font-weight:800;letter-spacing:-.3px">{title}</div>
            <div style="font-size:11px;color:#cbd5e1;letter-spacing:1.2px;text-transform:uppercase">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def badge(status):
    colors = {
        "Pending": ("#fef3c7", "#92400e"),
        "Confirmed": ("#ecfdf5", "#065f46"),
        "Back for Correction": ("#fff7ed", "#9a3412"),
        "Rejected": ("#fef2f2", "#991b1b"),
    }
    bg, fg = colors.get(status, ("#f1f5f9", "#334155"))
    return f'<span style="background:{bg};color:{fg};padding:3px 9px;border-radius:20px;font-size:11px;font-weight:700">{status}</span>'


# ============================================================
# PAGES
# ============================================================
def page_welcome():
    st.markdown(
        """
        <div style="text-align:center;padding:30px 0 10px">
            <div style="display:inline-block;width:92px;height:92px;border-radius:50%;
                        background:linear-gradient(135deg,#ea580c,#f59e0b);
                        color:#fff;font-weight:800;font-size:24px;line-height:92px;
                        box-shadow:0 10px 20px rgba(30,58,138,.28)">SSC</div>
            <div style="font-size:11px;color:#c2410c;font-weight:800;text-transform:uppercase;
                        letter-spacing:1.6px;margin-top:14px">Staff Selection Commission</div>
            <div style="font-size:28px;font-weight:800;color:#1e3a8a;letter-spacing:-.5px">Tasty Food</div>
            <div style="font-size:13px;color:#64748b;margin-top:5px">Control Room Meal Ordering System</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("👥  Control Room Member", use_container_width=True, type="primary"):
            st.session_state.page = "member_login"
            st.rerun()
    with col2:
        if st.button("🔐  Administrator", use_container_width=True):
            st.session_state.page = "admin_login"
            st.rerun()

    st.markdown(
        """
        <div style="text-align:center;font-size:11px;color:#94a3b8;margin-top:30px;line-height:1.7">
            Secured by Supabase · Rates visible to Administrator only<br>
            <b style="color:#1e3a8a">Staff Selection Commission · Government of India</b>
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_member_login():
    header("Member Details", "Enter once per session")
    with st.form("member_form"):
        name = st.text_input("Full Name", placeholder="e.g. Shri Sanjoy Paul")
        mobile = st.text_input("Mobile Number", placeholder="10-digit mobile", max_chars=15)
        c1, c2 = st.columns(2)
        with c1:
            back = st.form_submit_button("← Back", use_container_width=True)
        with c2:
            submit = st.form_submit_button("Continue →", use_container_width=True, type="primary")

    if back:
        st.session_state.page = "welcome"
        st.rerun()

    if submit:
        if len(name.strip()) < 2:
            st.error("Enter your full name")
        elif len("".join(filter(str.isdigit, mobile))) < 10:
            st.error("Enter a valid 10-digit mobile")
        else:
            st.session_state.member = {"name": name.strip(), "mobile": mobile.strip()}
            st.session_state.logged_in = True
            st.session_state.is_admin = False
            st.session_state.page = "member"
            load_all_data()
            st.rerun()


def page_admin_login():
    header("Administrator Access", "Enter the access ID to continue")
    with st.form("admin_form"):
        aid = st.text_input("Access ID", type="password")
        c1, c2 = st.columns(2)
        with c1:
            back = st.form_submit_button("← Back", use_container_width=True)
        with c2:
            submit = st.form_submit_button("Unlock", use_container_width=True, type="primary")

    if back:
        st.session_state.page = "welcome"
        st.rerun()

    if submit:
        if aid.strip().upper() != ADMIN_ID.upper():
            st.error("Invalid access ID")
        else:
            st.session_state.logged_in = True
            st.session_state.is_admin = True
            st.session_state.page = "admin"
            load_all_data()
            st.rerun()


def page_member():
    state = st.session_state.state
    member = st.session_state.member

    col1, col2, col3 = st.columns([4, 1, 1])
    with col1:
        header("Tasty Food", f"Member · {member['name']} · {member['mobile']}")
    with col3:
        if st.button("Sign out", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.member = None
            st.session_state.page = "welcome"
            st.rerun()

    tab1, tab2 = st.tabs(["🍽️ New Order", "📋 My Orders"])

    with tab1:
        meal = st.radio("Meal Category", ["Breakfast", "Lunch", "Other"], horizontal=True)
        pref = "Veg"
        if meal == "Lunch":
            pref = st.radio("Preference", ["Veg", "Non-Veg", "Rice Veg", "Rice Non-Veg"], horizontal=True)

        menu = state["menu"]
        if meal == "Lunch":
            items = menu["Lunch"].get(pref, [])
        else:
            items = menu.get(meal, [])
        available = [it for it in items if it["available"]]

        search = st.text_input("🔍 Search items", "")
        if search:
            available = [it for it in available if search.lower() in it["name"].lower()]

        if not available:
            st.info("No items available in this category.")
        else:
            selected = {}
            with st.container():
                for it in available:
                    nm = it["name"]
                    c1, c2 = st.columns([4, 1])
                    with c1:
                        checked = st.checkbox(nm, key=f"chk_{meal}_{pref}_{nm}")
                    with c2:
                        if checked and allows_qty(nm):
                            qty = st.number_input("Qty", min_value=1, max_value=99, value=1,
                                                  key=f"qty_{meal}_{pref}_{nm}", label_visibility="collapsed")
                            selected[nm] = qty
                        elif checked:
                            selected[nm] = 1

        remarks = st.text_area("Remarks", placeholder="Any special instruction or dish you want…")

        if st.button("Submit Order", type="primary", use_container_width=True):
            if not selected:
                st.error("Select at least one item")
            elif any(is_remarks_item(n) for n in selected) and not remarks.strip():
                st.error('Please add remarks for "Others"')
            else:
                order = {
                    "id": f"{int(time.time()*1000)}",
                    "name": member["name"],
                    "mobile": member["mobile"],
                    "meal": meal,
                    "preference": pref if meal == "Lunch" else "-",
                    "items": [{"name": n, "qty": q} for n, q in selected.items()],
                    "remarks": remarks.strip(),
                    "date": today_str(),
                    "time": now_time(),
                    "timestamp": datetime.now().isoformat(),
                    "status": "Pending",
                    "reply": "",
                    "source": "member",
                }
                state["orders"].append(order)
                save_state()
                st.success("Order placed successfully!")
                st.rerun()

    with tab2:
        if st.button("↻ Refresh", key="refresh_mine"):
            load_all_data()
            st.rerun()
        mine = [o for o in state["orders"]
                if o["mobile"] == member["mobile"] or (not o["mobile"] and o["name"] == member["name"])]
        mine.sort(key=lambda o: o.get("timestamp", ""), reverse=True)
        if not mine:
            st.info("No orders yet.")
        else:
            for o in mine:
                with st.expander(f"{o['date']} · {o['meal']} · {o['status']}"):
                    st.markdown(badge(o["status"]), unsafe_allow_html=True)
                    st.write(f"**Time:** {o['time']}")
                    st.write(f"**Preference:** {o['preference']}")
                    items_str = ", ".join(f"{it['name']} ×{it['qty']}" if it['qty'] > 1 else it['name'] for it in o["items"])
                    st.write(f"**Items:** {items_str}")
                    if o["remarks"]:
                        st.info(f"📝 {o['remarks']}")
                    if o["reply"]:
                        st.warning(f"**Admin:** {o['reply']}")


def page_admin():
    state = st.session_state.state
    admin_state = st.session_state.admin_state

    col1, col2, col3 = st.columns([4, 1, 1])
    with col1:
        header("Administrator Console", "Staff Selection Commission")
    with col2:
        if st.button("↻ Sync", use_container_width=True):
            load_all_data()
            st.rerun()
    with col3:
        if st.button("Sign out", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.is_admin = False
            st.session_state.page = "welcome"
            st.rerun()

    tabs = st.tabs(["📋 Orders", "✍️ Manual", "💰 Expenditure", "💬 Reminder", "🍽️ Menu", "💾 Data"])

    # -------- ORDERS --------
    with tabs[0]:
        pending = sum(1 for o in state["orders"] if o["status"] == "Pending")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total", len(state["orders"]))
        c2.metric("Pending", pending)
        c3.metric("Confirmed", sum(1 for o in state["orders"] if o["status"] == "Confirmed"))
        c4.metric("Rejected", sum(1 for o in state["orders"] if o["status"] == "Rejected"))

        st.markdown("### 📅 Date Range")
        ranges = ["All Time", "Today", "Yesterday", "This Week", "This Month", "Last Month"]
        quick = st.radio("Quick range", ranges, index=1, horizontal=True, label_visibility="collapsed")
        kind_map = {"All Time": "all", "Today": "today", "Yesterday": "yesterday",
                    "This Week": "week", "This Month": "month", "Last Month": "lastmonth"}
        from_d, to_d = get_date_bounds(kind_map[quick])

        cat = st.radio("Category", ["All", "Breakfast", "Lunch", "Other"], horizontal=True)
        status_filter = st.selectbox("Status", ["All", "Pending", "Confirmed", "Back for Correction", "Rejected"])
        search = st.text_input("🔍 Search name or mobile")

        orders = state["orders"][:]
        if cat != "All":
            orders = [o for o in orders if o["meal"] == cat]
        if status_filter != "All":
            orders = [o for o in orders if o["status"] == status_filter]
        if search:
            orders = [o for o in orders if search.lower() in o["name"].lower() or search in o["mobile"]]
        orders = [o for o in orders if in_date_range(o["date"], from_d, to_d)]
        orders.sort(key=lambda o: o.get("timestamp", ""), reverse=True)

        st.write(f"**{len(orders)} orders** in range")

        for o in orders:
            with st.expander(f"{o['date']} {o['time']} · {o['name']} · {o['meal']} · {o['status']}"):
                st.markdown(badge(o["status"]), unsafe_allow_html=True)
                st.write(f"**Mobile:** {o.get('mobile') or '—'}")
                st.write(f"**Preference:** {o['preference']}")
                items_str = ", ".join(f"{it['name']} ×{it['qty']}" if it['qty'] > 1 else it['name'] for it in o["items"])
                st.write(f"**Items:** {items_str}")
                if o["remarks"]:
                    st.info(f"📝 {o['remarks']}")
                if o["reply"]:
                    st.warning(f"**Reply:** {o['reply']}")

                if o["source"] != "admin":
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        if st.button("✅ Confirm", key=f"cf_{o['id']}"):
                            o["status"] = "Confirmed"
                            o["reply"] = "Order confirmed. Thank you!"
                            save_state()
                            st.rerun()
                    with c2:
                        msg = st.text_input("Correction msg", key=f"cm_{o['id']}", label_visibility="collapsed",
                                            placeholder="Correction reason")
                        if st.button("🔄 Correct", key=f"co_{o['id']}"):
                            if not msg.strip():
                                st.error("Enter a message")
                            else:
                                o["status"] = "Back for Correction"
                                o["reply"] = msg.strip()
                                save_state()
                                st.rerun()
                    with c3:
                        msg2 = st.text_input("Reject msg", key=f"rm_{o['id']}", label_visibility="collapsed",
                                             placeholder="Reject reason")
                        if st.button("❌ Reject", key=f"ro_{o['id']}"):
                            if not msg2.strip():
                                st.error("Enter a message")
                            else:
                                o["status"] = "Rejected"
                                o["reply"] = msg2.strip()
                                save_state()
                                st.rerun()
                    with c4:
                        if st.button("🗑️ Delete", key=f"del_{o['id']}"):
                            state["orders"] = [x for x in state["orders"] if x["id"] != o["id"]]
                            save_state()
                            st.rerun()
                else:
                    if st.button("🗑️ Delete", key=f"del_{o['id']}"):
                        state["orders"] = [x for x in state["orders"] if x["id"] != o["id"]]
                        save_state()
                        st.rerun()

        # Export
        st.markdown("---")
        if st.button("📥 Export Orders (CSV)"):
            df = orders_to_df(orders)
            csv = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button("Download CSV", csv,
                               file_name=f"SSC_Orders_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                               mime="text/csv")

    # -------- MANUAL --------
    with tabs[1]:
        st.subheader("Manual Order Entry")
        name = st.text_input("Member Name *", key="man_name")
        mobile = st.text_input("Mobile (optional)", key="man_mobile")
        meal = st.radio("Meal", ["Breakfast", "Lunch", "Other"], horizontal=True, key="man_meal")
        pref = "Veg"
        if meal == "Lunch":
            pref = st.radio("Preference", ["Veg", "Non-Veg", "Rice Veg", "Rice Non-Veg"],
                            horizontal=True, key="man_pref")

        menu = state["menu"]
        if meal == "Lunch":
            items = menu["Lunch"].get(pref, [])
        else:
            items = menu.get(meal, [])

        selected = {}
        for it in items:
            nm = it["name"]
            c1, c2 = st.columns([4, 1])
            with c1:
                checked = st.checkbox(nm, key=f"man_{meal}_{pref}_{nm}")
            with c2:
                if checked and allows_qty(nm):
                    qty = st.number_input("Qty", 1, 99, 1, key=f"manq_{meal}_{pref}_{nm}",
                                          label_visibility="collapsed")
                    selected[nm] = qty
                elif checked:
                    selected[nm] = 1

        remarks = st.text_area("Remarks", key="man_remarks")

        if st.button("Place Manual Order", type="primary", use_container_width=True):
            if len(name.strip()) < 2:
                st.error("Enter member name")
            elif not selected:
                st.error("Select at least one item")
            else:
                order = {
                    "id": f"{int(time.time()*1000)}",
                    "name": name.strip(),
                    "mobile": mobile.strip(),
                    "meal": meal,
                    "preference": pref if meal == "Lunch" else "-",
                    "items": [{"name": n, "qty": q} for n, q in selected.items()],
                    "remarks": remarks.strip(),
                    "date": today_str(),
                    "time": now_time(),
                    "timestamp": datetime.now().isoformat(),
                    "status": "Confirmed",
                    "reply": "Manually entered by admin",
                    "source": "admin",
                }
                state["orders"].append(order)
                save_state()
                st.success("Manual order placed")
                st.rerun()

    # -------- EXPENDITURE --------
    with tabs[2]:
        exp_tabs = st.tabs(["💰 Item Rates", "📝 Misc Expenses", "📊 Reports"])

        with exp_tabs[0]:
            st.subheader("Item Rates")
            all_items = set()
            for it in state["menu"].get("Breakfast", []):
                all_items.add(it["name"])
            for it in state["menu"].get("Other", []):
                all_items.add(it["name"])
            for p, arr in state["menu"].get("Lunch", {}).items():
                for it in arr:
                    all_items.add(it["name"])
            names = sorted(all_items)

            search = st.text_input("🔍 Search items", key="rate_search")
            if search:
                names = [n for n in names if search.lower() in n.lower()]

            new_rates = {}
            for nm in names:
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.write(nm)
                with c2:
                    val = st.number_input("Rate", min_value=0.0, step=1.0,
                                          value=float(admin_state["itemRates"].get(nm, 0.0)),
                                          key=f"rate_{nm}", label_visibility="collapsed")
                    if val > 0:
                        new_rates[nm] = round(val, 2)

            if st.button("💾 Save All Rates", type="primary"):
                admin_state["itemRates"] = new_rates
                save_admin_state()
                st.success("Rates saved")
                st.rerun()

        with exp_tabs[1]:
            st.subheader("Add Misc Expense")
            misc_date = st.date_input("Date", value=date.today())
            desc = st.text_input("Description *", placeholder="e.g. Sweets for farewell")
            amt = st.number_input("Amount (₹) *", min_value=0.0, step=1.0)

            if st.button("＋ Add Expense", type="primary"):
                if len(desc.strip()) < 3:
                    st.error("Enter a description")
                elif amt <= 0:
                    st.error("Enter a valid amount")
                else:
                    admin_state["miscExpenses"].append({
                        "id": f"{int(time.time()*1000)}",
                        "date": date_to_ddmm(misc_date),
                        "description": desc.strip(),
                        "amount": round(amt, 2),
                        "timestamp": datetime.now().isoformat(),
                    })
                    save_admin_state()
                    st.success("Expense added")
                    st.rerun()

            st.markdown("### History")
            miscs = sorted(admin_state["miscExpenses"],
                           key=lambda m: (ddmm_to_date(m["date"]) or date.min), reverse=True)
            if miscs:
                total = sum(m["amount"] for m in miscs)
                st.write(f"**{len(miscs)} entries · Total {money(total)}**")
                for m in miscs:
                    c1, c2, c3, c4 = st.columns([1, 3, 1, 1])
                    c1.write(m["date"])
                    c2.write(m["description"])
                    c3.write(money(m["amount"]))
                    with c4:
                        if st.button("✕", key=f"delmisc_{m['id']}"):
                            admin_state["miscExpenses"] = [x for x in admin_state["miscExpenses"] if x["id"] != m["id"]]
                            save_admin_state()
                            st.rerun()
            else:
                st.info("No misc expenses yet")

        with exp_tabs[2]:
            st.subheader("Expenditure Report")
            ranges = ["All Time", "Today", "This Week", "This Month", "Last Month"]
            quick = st.radio("Range", ranges, index=1, horizontal=True, key="rpt_range")
            from_d, to_d = get_date_bounds(kind_map[quick])

            confirmed = [o for o in state["orders"]
                         if o["status"] == "Confirmed" and in_date_range(o["date"], from_d, to_d)]
            miscs = [m for m in admin_state["miscExpenses"]
                     if in_date_range(m["date"], from_d, to_d)]

            item_qty = {}
            item_cost = {}
            order_cost_total = 0.0
            total_qty = 0
            unrated = set()

            for o in confirmed:
                oc = 0.0
                for it in o["items"]:
                    q = it["qty"]
                    r = admin_state["itemRates"].get(it["name"], 0.0)
                    item_qty[it["name"]] = item_qty.get(it["name"], 0) + q
                    item_cost[it["name"]] = item_cost.get(it["name"], 0.0) + r * q
                    total_qty += q
                    oc += r * q
                    if r == 0:
                        unrated.add(it["name"])
                order_cost_total += oc

            misc_total = sum(m["amount"] for m in miscs)
            grand = order_cost_total + misc_total

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Confirmed", len(confirmed))
            c2.metric("Items", total_qty)
            c3.metric("Order Cost", money(order_cost_total))
            c4.metric("Misc Cost", money(misc_total))
            st.metric("GRAND TOTAL", money(grand))

            if unrated:
                st.warning(f"⚠️ Unrated items: {', '.join(sorted(unrated))}")

            st.markdown("#### Item-wise Breakdown")
            if item_qty:
                rows = []
                for nm in sorted(item_qty):
                    r = admin_state["itemRates"].get(nm, 0.0)
                    rows.append({
                        "Item": nm,
                        "Qty": item_qty[nm],
                        "Rate": f"₹{r:.2f}" if r else "not set",
                        "Amount": f"₹{item_cost[nm]:.2f}",
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True)

            st.markdown("#### Misc Expenses")
            if miscs:
                st.dataframe(pd.DataFrame([
                    {"Date": m["date"], "Description": m["description"], "Amount": f"₹{m['amount']:.2f}"}
                    for m in miscs
                ]), use_container_width=True)

            if st.button("📥 Export Expenditure CSV"):
                buf = io.StringIO()
                buf.write(f"{ORG_NAME} — TASTY FOOD\n")
                buf.write("Expenditure Report\n")
                buf.write(f"Range,{quick}\n")
                buf.write(f"Generated,{today_str()} {now_time()}\n\n")
                buf.write("SUMMARY\n")
                buf.write(f"Confirmed Orders,{len(confirmed)}\n")
                buf.write(f"Total Items,{total_qty}\n")
                buf.write(f"Order Cost,{order_cost_total:.2f}\n")
                buf.write(f"Misc Cost,{misc_total:.2f}\n")
                buf.write(f"GRAND TOTAL,{grand:.2f}\n\n")
                buf.write("ITEM-WISE\nItem,Qty,Rate,Amount\n")
                for nm in sorted(item_qty):
                    r = admin_state["itemRates"].get(nm, 0.0)
                    buf.write(f"{nm},{item_qty[nm]},{r:.2f},{item_cost[nm]:.2f}\n")
                st.download_button(
                    "Download Expenditure CSV",
                    buf.getvalue().encode("utf-8-sig"),
                    file_name=f"SSC_Expenditure_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                )

    # -------- REMINDER --------
    with tabs[3]:
        st.subheader("WhatsApp Reminder")
        wa_meal = st.radio("Meal", ["Breakfast", "Lunch"], horizontal=True, key="wa_meal")
        wa_name = st.text_input("Member Name (optional)", placeholder="Leave blank for generic")
        name_disp = wa_name.strip() or "<<Member name>>"
        msg = (
            f"🍽️ *Tasty Food — Staff Selection Commission*\n"
            f"*Meal Order Reminder*\n\n"
            f"Dear {name_disp},\n\n"
            f"Please place your order for *{wa_meal}* today, or else you will be provided a survival meal. 🍱\n\n"
            f"👉 Place your order here: {st.secrets.get('APP_URL', 'https://your-app.streamlit.app')}\n\n"
            f"For any help or to add an item to the menu, contact:\n"
            f"📞 {CONTACT_NAME} — {CONTACT_MOBILE}\n\n"
            f"— Tasty Food Admin\n"
            f"Staff Selection Commission"
        )
        st.text_area("Preview", msg, height=280)
        c1, c2 = st.columns(2)
        with c1:
            st.code(msg, language=None)
            st.caption("Copy the code block above")
        with c2:
            st.link_button(
                "💬 Open WhatsApp",
                f"https://wa.me/?text={msg.replace(' ', '%20').replace(chr(10), '%0A')}",
                use_container_width=True,
            )

    # -------- MENU --------
    with tabs[4]:
        st.subheader("Menu Management")
        m_meal = st.radio("Meal", ["Breakfast", "Lunch", "Other"], horizontal=True, key="menu_meal")
        m_pref = "Veg"
        if m_meal == "Lunch":
            m_pref = st.radio("Sub-category", ["Veg", "Non-Veg", "Rice Veg", "Rice Non-Veg"],
                              horizontal=True, key="menu_pref")

        menu = state["menu"]
        if m_meal == "Lunch":
            items = menu["Lunch"].get(m_pref, [])
        else:
            items = menu.get(m_meal, [])

        new_name = st.text_input("➕ Add new item", key="new_item")
        if st.button("Add Item"):
            if len(new_name.strip()) < 2:
                st.error("Enter a valid name")
            elif any(x["name"].lower() == new_name.strip().lower() for x in items):
                st.error("Item already exists")
            else:
                items.append({"name": new_name.strip(), "available": True})
                if m_meal == "Lunch":
                    menu["Lunch"][m_pref] = items
                else:
                    menu[m_meal] = items
                save_state()
                st.success(f"Added: {new_name}")
                st.rerun()

        st.markdown("### Items")
        for i, it in enumerate(items):
            c1, c2, c3, c4 = st.columns([1, 3, 1, 1])
            with c1:
                new_avail = st.checkbox("", value=it["available"], key=f"av_{m_meal}_{m_pref}_{i}")
            c2.write(it["name"] if it["available"] else f"~~{it['name']}~~")
            with c3:
                new_nm = st.text_input("Rename", value=it["name"], key=f"rn_{m_meal}_{m_pref}_{i}",
                                       label_visibility="collapsed")
            with c4:
                if st.button("🗑️", key=f"dl_{m_meal}_{m_pref}_{i}"):
                    items.pop(i)
                    if m_meal == "Lunch":
                        menu["Lunch"][m_pref] = items
                    else:
                        menu[m_meal] = items
                    save_state()
                    st.rerun()

            if new_avail != it["available"] or new_nm != it["name"]:
                it["available"] = new_avail
                if new_nm.strip() and new_nm != it["name"]:
                    old = it["name"]
                    it["name"] = new_nm.strip()
                    if old in admin_state["itemRates"] and it["name"] not in admin_state["itemRates"]:
                        admin_state["itemRates"][it["name"]] = admin_state["itemRates"].pop(old)
                        save_admin_state()
                if m_meal == "Lunch":
                    menu["Lunch"][m_pref] = items
                else:
                    menu[m_meal] = items
                save_state()
                st.rerun()

    # -------- DATA --------
    with tabs[5]:
        st.subheader("💾 Data & Settings")
        size = len(json.dumps(state)) + len(json.dumps(admin_state))
        st.write(f"**Storage used:** {size/1024:.2f} KB")
        st.progress(min(1.0, size / (500 * 1024 * 1024)))

        st.markdown("### Export")
        c1, c2 = st.columns(2)
        with c1:
            df = orders_to_df(state["orders"])
            csv = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button("📥 Orders CSV", csv,
                               file_name=f"SSC_Orders_{datetime.now().strftime('%Y%m%d')}.csv",
                               mime="text/csv", use_container_width=True)
        with c2:
            backup = json.dumps({
                "exportedAt": datetime.now().isoformat(),
                "orders": state["orders"],
                "menu": state["menu"],
                "itemRates": admin_state["itemRates"],
                "miscExpenses": admin_state["miscExpenses"],
            }, indent=2, ensure_ascii=False)
            st.download_button("🗄️ Full Backup JSON", backup,
                               file_name=f"SSC_Backup_{datetime.now().strftime('%Y%m%d')}.json",
                               mime="application/json", use_container_width=True)

        st.markdown("### Import")
        up = st.file_uploader("Restore from JSON backup", type=["json"])
        if up and st.button("Restore"):
            try:
                data = json.loads(up.read())
                state["orders"].extend(data.get("orders", []))
                if data.get("menu"):
                    state["menu"] = data["menu"]
                if data.get("itemRates"):
                    admin_state["itemRates"] = data["itemRates"]
                if data.get("miscExpenses"):
                    admin_state["miscExpenses"].extend(data["miscExpenses"])
                save_state()
                save_admin_state()
                st.success("Restored")
                st.rerun()
            except Exception as e:
                st.error(f"Restore failed: {e}")

        st.markdown("### Danger Zone")
        if st.button("🧹 Clear All Orders", type="secondary"):
            state["orders"] = []
            save_state()
            st.success("Orders cleared")
            st.rerun()
        if st.button("🗑️ Reset Everything", type="secondary"):
            state["orders"] = []
            state["menu"] = seed_menu()
            admin_state["itemRates"] = {}
            admin_state["miscExpenses"] = []
            save_state()
            save_admin_state()
            st.success("Reset complete")
            st.rerun()


def orders_to_df(orders):
    rows = []
    for i, o in enumerate(orders, 1):
        items = "; ".join(f"{it['name']} x{it['qty']}" if it['qty'] > 1 else it['name'] for it in o["items"])
        qty = sum(it["qty"] for it in o["items"])
        rows.append({
            "Sl": i,
            "Date": o["date"],
            "Time": o["time"],
            "Name": o["name"],
            "Mobile": o["mobile"],
            "Meal": o["meal"],
            "Preference": o["preference"],
            "Items": items,
            "Total Qty": qty,
            "Status": o["status"],
            "Source": o["source"],
            "Remarks": o["remarks"],
            "Admin Reply": o["reply"],
        })
    return pd.DataFrame(rows)


# ============================================================
# MAIN
# ============================================================
def main():
    init_session()

    if not st.session_state.state:
        load_all_data()

    page = st.session_state.page

    if page == "welcome":
        page_welcome()
    elif page == "member_login":
        page_member_login()
    elif page == "admin_login":
        page_admin_login()
    elif page == "member":
        page_member()
    elif page == "admin":
        page_admin()
    else:
        page_welcome()


if __name__ == "__main__":
    try:
        st.write("🟢 Boot started")
        st.write("Secrets loaded:", "SUPABASE_URL" in st.secrets if hasattr(st, "secrets") else "no secrets")
        main()
        st.write("🟢 Boot completed")
    except Exception as e:
        import traceback
        st.error(f"❌ Crash: {type(e).__name__}: {e}")
        st.code(traceback.format_exc())
