# -*- coding: utf-8 -*-
"""
Diet Tracker -- Streamlit App

Log meals from Perplexity nutrition output, visualize trends, and track body composition.
Data is stored persistently in Google Sheets.
"""

import datetime
import streamlit as st
import pandas as pd

from utils.parser import (
    parse_nutrition, extract_food_name, ALL_FIELDS, TIER1_FIELDS,
    TIER2_FIELDS, TIER3_FIELDS, DISPLAY_NAMES, UNITS,
)
from utils.sheets import (
    load_log, save_entry, delete_entry,
    load_food_library, save_to_library, delete_from_library,
    load_body_log, save_body_entry,
)
from utils.charts import (
    daily_calorie_bar, macro_area_chart, micro_trend_lines,
    macro_radar, body_weight_chart, body_fat_chart,
)

# --- Page config ---
st.set_page_config(
    page_title="Diet Tracker",
    page_icon=":green_salad:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom CSS ---
st.markdown("""
<style>
    /* Tighten spacing while clearing the fixed header */
    .block-container { padding-top: 3rem; }
    /* Progress bars */
    .stProgress > div > div > div > div {
        background-color: #3B82F6;
    }
    /* Metric cards */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 700;
    }
    /* Smaller sidebar width */
    [data-testid="stSidebar"] {
        min-width: 340px;
        max-width: 400px;
    }
</style>
""", unsafe_allow_html=True)


# --- Initialize session state ---
if "parsed_nutrients" not in st.session_state:
    st.session_state.parsed_nutrients = None
if "form_counter" not in st.session_state:
    st.session_state.form_counter = 0
if "save_success" not in st.session_state:
    st.session_state.save_success = None

# Show success toast from previous save (survives rerun)
if st.session_state.save_success:
    st.toast(st.session_state.save_success, icon=":white_check_mark:")
    st.session_state.save_success = None


def _clear_form():
    """Increment counter to reset keyed widgets and clear parsed data."""
    st.session_state.form_counter += 1
    st.session_state.parsed_nutrients = None


# Prefix for dynamic widget keys so they reset when counter changes
_k = str(st.session_state.form_counter)


# =========================================
#  SIDEBAR -- Input Panel
# =========================================
with st.sidebar:
    st.title(":green_salad: Diet Tracker")
    st.caption("Log meals - Track macros - See trends")

    st.divider()

    # -- Settings (collapsible) --
    with st.expander("Goals & Settings", expanded=False):
        calorie_goal = st.number_input("Daily Calorie Goal (kcal)", 500, 6000, 2000, step=50, key="cal_goal")
        protein_goal = st.number_input("Daily Protein Goal (g)", 10, 500, 150, step=5, key="prot_goal")
        fiber_goal = st.number_input("Daily Fiber Goal (g)", 5, 100, 30, step=1, key="fiber_goal")

    st.divider()

    # -- Meal Input --
    st.subheader("Log a Meal")

    log_date = st.date_input("Date", value=datetime.date.today(), key="log_date")
    meal_type = st.selectbox("Meal Type", ["Breakfast", "Lunch", "Dinner", "Snack"], key=f"meal_type_{_k}")
    meal_name = st.text_input("Meal Name (optional)", key=f"meal_name_{_k}", placeholder="e.g. Chicken stir-fry")

    # Inferred name from parser or library (used at save time if meal_name is blank)
    _inferred_name = ""

    # -- Source selector: paste or food library --
    input_mode = st.radio("Input Source", ["Paste from Perplexity", "Food Library"], horizontal=True, key=f"input_mode_{_k}")

    if input_mode == "Paste from Perplexity":
        raw_text = st.text_area(
            "Paste Perplexity Output",
            height=160,
            key=f"raw_text_{_k}",
            placeholder="Calories: 450 kcal | Protein: 35g | Total Fat: 15g | ...",
        )

        # Parse button for mobile (no keyboard Enter key)
        parse_clicked = st.button("Parse Nutrition", use_container_width=True, key=f"parse_btn_{_k}")

        if raw_text.strip():
            parsed = parse_nutrition(raw_text)
            st.session_state.parsed_nutrients = parsed

            # Detect food name from text (used as fallback at save time)
            auto_name = extract_food_name(raw_text)
            if auto_name:
                _inferred_name = auto_name

            # Preview
            st.markdown("**Parsed Preview:**")
            if _inferred_name and not meal_name:
                st.caption(f"Detected: {_inferred_name}")
            preview_cols = st.columns(3)
            for i, field in enumerate(TIER1_FIELDS):
                val = parsed[field]
                if val > 0:
                    col = preview_cols[i % 3]
                    col.markdown(f"**{DISPLAY_NAMES[field]}**: {val:.1f} {UNITS[field]}")

            # Show Tier 2/3 if any non-zero
            tier23_nonzero = {f: parsed[f] for f in TIER2_FIELDS + TIER3_FIELDS if parsed[f] > 0}
            if tier23_nonzero:
                with st.expander(f"+ {len(tier23_nonzero)} more nutrients"):
                    for f, v in tier23_nonzero.items():
                        st.markdown(f"**{DISPLAY_NAMES[f]}**: {v:.1f} {UNITS[f]}")
        else:
            st.session_state.parsed_nutrients = None

    else:  # Food Library
        lib_df = load_food_library()
        if lib_df.empty:
            st.info("Food Library is empty. Log meals first, then save to library.")
            st.session_state.parsed_nutrients = None
        else:
            food_options = lib_df["meal_name"].tolist()
            selected_food = st.selectbox("Select from Library", food_options, key=f"lib_select_{_k}")
            if selected_food:
                row = lib_df[lib_df["meal_name"] == selected_food].iloc[0]
                parsed = {f: float(row.get(f, 0)) for f in ALL_FIELDS}
                st.session_state.parsed_nutrients = parsed
                _inferred_name = selected_food

                st.markdown("**Selected:**")
                st.markdown(f"Calories: **{parsed['calories']:.0f}** kcal | "
                            f"P: **{parsed['protein']:.0f}**g | "
                            f"F: **{parsed['total_fat']:.0f}**g | "
                            f"C: **{parsed['total_carbs']:.0f}**g")

    st.divider()

    # -- Save options --
    also_save_to_lib = st.checkbox("Also save to Food Library", value=True, key=f"also_lib_{_k}")

    save_clicked = st.button("Save Entry", use_container_width=True, type="primary", key=f"save_btn_{_k}")

    if save_clicked:
        nutrients = st.session_state.parsed_nutrients
        # Use typed name, fall back to inferred name from parser/library
        current_meal_name = meal_name.strip() if meal_name.strip() else _inferred_name
        if nutrients is None:
            st.error("Nothing to save. Paste nutrition data or select from library.")
        else:
            entry = {
                "date": str(log_date),
                "meal_type": meal_type,
                "meal_name": current_meal_name,
            }
            entry.update(nutrients)
            try:
                save_entry(entry)
                # Also save to library if checked and meal has a name
                if also_save_to_lib and current_meal_name:
                    lib_entry = {"meal_name": current_meal_name}
                    lib_entry.update(nutrients)
                    # Check if already in library to avoid duplicates
                    existing_lib = load_food_library()
                    if existing_lib.empty or current_meal_name not in existing_lib["meal_name"].values:
                        save_to_library(lib_entry)
                st.session_state.save_success = f"Saved {meal_type} for {log_date}"
                _clear_form()
                st.rerun()
            except Exception as e:
                st.error(f"Error saving: {e}")

    st.divider()

    # -- Prompt template helper --
    with st.expander("Perplexity Prompt Template"):
        st.code(
            "Analyze this meal and return the nutrition in this exact format:\n\n"
            "Calories: X kcal | Protein: Xg | Total Fat: Xg | Saturated Fat: Xg |\n"
            "Trans Fat: Xg | Carbs: Xg | Fiber: Xg | Sugar: Xg | Added Sugar: Xg |\n"
            "Sodium: Xmg | Cholesterol: Xmg | Calcium: Xmg | Iron: Xmg |\n"
            "Potassium: Xmg | Vitamin C: Xmg | Vitamin D: Xug | Magnesium: Xmg |\n"
            "Zinc: Xmg\n\n"
            "If a value is unknown, write 0.",
            language="text",
        )


# =========================================
#  MAIN PANEL -- Tabs
# =========================================

tab_today, tab_trends, tab_library, tab_body = st.tabs(["Today", "Trends", "Food Library", "Body Log"])


# --- TAB 1: TODAY ---
with tab_today:
    log_df = load_log()
    today_str = str(log_date)

    if log_df.empty:
        today_df = pd.DataFrame()
    else:
        today_df = log_df[log_df["date"] == today_str]

    # Daily totals
    st.subheader(f"Summary for {log_date.strftime('%A, %b %d')}")

    if today_df.empty:
        st.info("No meals logged for this date. Use the sidebar to add entries.")
    else:
        total_cal = today_df["calories"].sum()
        total_prot = today_df["protein"].sum()
        total_fat = today_df["total_fat"].sum()
        total_carbs = today_df["total_carbs"].sum()
        total_fiber = today_df["fiber"].sum()

        # Metric cards
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Calories", f"{total_cal:.0f} kcal")
        m2.metric("Protein", f"{total_prot:.0f} g")
        m3.metric("Fat", f"{total_fat:.0f} g")
        m4.metric("Carbs", f"{total_carbs:.0f} g")

        # Progress bars
        st.markdown("**Goal Progress**")
        p1, p2, p3 = st.columns(3)
        with p1:
            cal_pct = min(total_cal / calorie_goal, 1.0) if calorie_goal > 0 else 0
            st.caption(f"Calories: {total_cal:.0f} / {calorie_goal}")
            st.progress(cal_pct)
        with p2:
            prot_pct = min(total_prot / protein_goal, 1.0) if protein_goal > 0 else 0
            st.caption(f"Protein: {total_prot:.0f}g / {protein_goal}g")
            st.progress(prot_pct)
        with p3:
            fib_pct = min(total_fiber / fiber_goal, 1.0) if fiber_goal > 0 else 0
            st.caption(f"Fiber: {total_fiber:.0f}g / {fiber_goal}g")
            st.progress(fib_pct)

        # Today's meal list
        st.markdown("---")
        st.markdown("**Meals Logged**")
        for idx, row in today_df.iterrows():
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([1.5, 2.5, 1.2, 1.2, 1.2])
                c1.markdown(f"**{row.get('meal_type', '')}**")
                c2.markdown(row.get("meal_name", "-"))
                c3.markdown(f"{row['calories']:.0f} kcal")
                c4.markdown(f"P: {row['protein']:.0f}g")
                c5.markdown(f"F: {row['total_fat']:.0f}g  C: {row['total_carbs']:.0f}g")


# --- TAB 2: TRENDS ---
with tab_trends:
    log_df = load_log()

    if log_df.empty:
        st.info("No data yet. Start logging meals to see trends.")
    else:
        st.subheader("Calorie Trend")
        st.plotly_chart(daily_calorie_bar(log_df, calorie_goal), use_container_width=True)

        st.subheader("Macro Breakdown")
        st.plotly_chart(macro_area_chart(log_df), use_container_width=True)

        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("Micro Trends")
            selected_micros = st.multiselect(
                "Select nutrients to plot",
                options=[f for f in TIER2_FIELDS + TIER3_FIELDS],
                default=["calcium", "iron", "potassium"],
                format_func=lambda x: DISPLAY_NAMES.get(x, x),
            )
            if selected_micros:
                st.plotly_chart(micro_trend_lines(log_df, selected_micros), use_container_width=True)
        with col_b:
            st.subheader("Nutrient Profile")
            st.plotly_chart(macro_radar(log_df), use_container_width=True)

        # CSV export
        st.divider()
        st.subheader("Export Data")
        csv_data = log_df.to_csv(index=False)
        st.download_button(
            label="Download Full Log (CSV)",
            data=csv_data,
            file_name=f"diet_log_{datetime.date.today()}.csv",
            mime="text/csv",
        )


# --- TAB 3: FOOD LIBRARY ---
with tab_library:
    st.subheader("Saved Foods")
    lib_df = load_food_library()

    if lib_df.empty:
        st.info("Your food library is empty. Save meals from the sidebar to build your library.")
    else:
        # Display table
        display_cols = ["meal_name", "calories", "protein", "total_fat", "total_carbs", "fiber"]
        display_df = lib_df[display_cols].copy()
        display_df.columns = ["Meal", "Calories", "Protein (g)", "Fat (g)", "Carbs (g)", "Fiber (g)"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        # Quick-log from library
        st.markdown("---")
        st.markdown("**Quick Log from Library**")
        qc1, qc2, qc3, qc4 = st.columns([3, 1.5, 1.5, 1.5])
        with qc1:
            quick_food = st.selectbox("Food", lib_df["meal_name"].tolist(), key="quick_food")
        with qc2:
            quick_date = st.date_input("Date", value=datetime.date.today(), key="quick_date")
        with qc3:
            quick_meal = st.selectbox("Meal", ["Breakfast", "Lunch", "Dinner", "Snack"], key="quick_meal")
        with qc4:
            if st.button("Quick Log", use_container_width=True, key="quick_log_btn"):
                food_row = lib_df[lib_df["meal_name"] == quick_food].iloc[0]
                entry = {
                    "date": str(quick_date),
                    "meal_type": quick_meal,
                    "meal_name": quick_food,
                }
                for f in ALL_FIELDS:
                    entry[f] = float(food_row.get(f, 0))
                try:
                    save_entry(entry)
                    st.success(f"Logged '{quick_food}' for {quick_date}")
                except Exception as e:
                    st.error(f"Error: {e}")

        # Delete from library
        with st.expander("Remove from Library"):
            del_food = st.selectbox("Select food to remove", lib_df["meal_name"].tolist(), key="del_food")
            if st.button("Delete", key="del_lib_btn"):
                row_idx = int(lib_df[lib_df["meal_name"] == del_food].index[0])
                # +2 because: 0-indexed DataFrame + 1 for header row + 1 for 1-based sheets
                delete_from_library(row_idx + 2)
                st.success(f"Removed '{del_food}' from library.")
                st.rerun()


# --- TAB 4: BODY LOG ---
with tab_body:
    st.subheader("Body Composition")

    col_input, col_chart = st.columns([1, 2])

    with col_input:
        st.markdown("**Log Entry**")
        body_date = st.date_input("Date", value=datetime.date.today(), key="body_date")
        body_weight = st.number_input("Weight (kg)", 30.0, 250.0, step=0.1, value=70.0, key="body_weight")
        body_fat = st.number_input("Body Fat % (optional)", 0.0, 60.0, step=0.1, value=0.0, key="body_fat")

        if st.button("Save Body Entry", use_container_width=True, key="save_body"):
            entry = {
                "date": str(body_date),
                "weight_kg": body_weight,
                "body_fat_pct": body_fat if body_fat > 0 else "",
            }
            try:
                save_body_entry(entry)
                st.success(f"Saved body data for {body_date}")
            except Exception as e:
                st.error(f"Error: {e}")

    with col_chart:
        body_df = load_body_log()
        if body_df.empty:
            st.info("No body data yet. Log your weight and body fat % to see trends.")
        else:
            st.plotly_chart(body_weight_chart(body_df), use_container_width=True)
            st.plotly_chart(body_fat_chart(body_df), use_container_width=True)

            # Display recent entries
            st.markdown("**Recent Entries**")
            recent = body_df.sort_values("date", ascending=False).head(10)
            display_body = recent[["date", "weight_kg", "body_fat_pct"]].copy()
            display_body.columns = ["Date", "Weight (kg)", "Body Fat (%)"]
            st.dataframe(display_body, use_container_width=True, hide_index=True)
