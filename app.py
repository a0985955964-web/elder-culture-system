import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2.service_account import Credentials

# 設定頁面標題與佈局
st.set_page_config(page_title="課研處 - 文化協同耆老與工作費管理系統", layout="wide")

RATE_EXPERIMENTAL = 400
RATE_IMMERSIVE = 405
RATE_WORK_FEE = 196
LIMIT_WORK_HOURS_MONTH = 15

COLUMNS = [
    "日期", "申請處室", "活動型態", "年級班級", "主辦/授課教師", "人員/耆老姓名", "課程/活動/工作項目", "支領類別", "登記時數/節數", "備註"
]

# 嘗試初始化 Google Sheets 寫入權限
@st.cache_resource
def init_gsheets():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet_url = st.secrets["spreadsheet_url"]
    sh = client.open_by_url(sheet_url)
    return sh.sheet1

try:
    ws = init_gsheets()
    gsheets_connected = True
except Exception:
    gsheets_connected = False

def load_data():
    if gsheets_connected:
        try:
            records = ws.get_all_records()
            df = pd.DataFrame(records)
            for col in COLUMNS:
                if col not in df.columns:
                    df[col] = ""
            return df[COLUMNS]
        except Exception:
            return pd.DataFrame(columns=COLUMNS)
    else:
        if 'records' in st.session_state:
            return st.session_state.records
        return pd.DataFrame(columns=COLUMNS)

def save_all_to_sheets(df):
    if gsheets_connected:
        ws.clear()
        ws.append_row(COLUMNS)
        if not df.empty:
            ws.append_rows(df.astype(str).values.tolist())

# 初始化 session
if 'records' not in st.session_state or gsheets_connected:
    st.session_state.records = load_data()

st.title("🌾 課研處 - 文化協同耆老時數、鐘點費與工作費管理系統")

if gsheets_connected:
    st.success("🟢 雲端連線狀態：已雙向同步連線至 Google 試算表！新增紀錄會即時自動寫入雲端。")
else:
    st.warning("🟠 雲端連線狀態：未設定 gcp_service_account 寫入金鑰，目前新增資料僅為單次暫存。")

st.sidebar.header("📝 登錄耆老協同 / 臨時工作費紀錄")

with st.sidebar.form("entry_form", clear_on_submit=True):
    date_val = st.date_input("授課/工作日期", datetime.date.today())
    dept_val = "課研處"
    st.text_input("申請處室", value=dept_val, disabled=True)
    
    activity_type = st.selectbox("活動/計畫型態", ["一般年級文化課", "校外參訪協同", "全校性大活動", "校本課程/研習研發", "行政支援/臨時工作"])
    grade_val = st.selectbox("適用年級/對象", ["全校", "一年級", "二年級", "三年級", "四年級", "五年級", "六年級"])
    teacher_val = st.text_input("主辦/授課教師", placeholder="例如：玉如老師 / 承彥老師")
    
    elder_input = st.text_input("人員 / 耆老姓名（若多位協同請用逗號隔開）", placeholder="例如：姜耆老, 羅耆老")
    course_title = st.text_input("課程/工作項目名稱", placeholder="例如：舊北葉部落尋根參訪 / 傳統工藝協同")
    
    pay_category = st.selectbox("支領類別", [
        "實驗教育授課鐘點費 (400元/節)", 
        "沉浸式族語授課鐘點費 (405元/節)", 
        "臨時工作費 (196元/小時，每月限15小時)"
    ])
    
    hours_val = st.number_input("登記時數 / 節數 (每一位耆老個別認列)", min_value=0.5, max_value=20.0, value=1.0, step=0.5)
    note_val = st.text_input("備註", placeholder="例如：課研處專案多位耆老同時入場協同")
    
    submitted = st.form_submit_button("新增紀錄")

if submitted:
    if not teacher_val or not elder_input:
        st.sidebar.error("⚠️ 請填寫主辦/授課教師與人員/耆老姓名！")
    else:
        date_str = date_val.strftime("%Y-%m-%d")
        month_str = date_val.strftime("%Y-%m")
        
        raw_elders = elder_input.replace("、", ",").replace(" ", "").split(",")
        elder_list = [e.strip() for e in raw_elders if e.strip()]
        
        new_rows = []
        for single_elder in elder_list:
            if "工作費" in pay_category:
                existing_work_hrs = pd.to_numeric(st.session_state.records[
                    (st.session_state.records["日期"].astype(str).str.startswith(month_str)) & 
                    (st.session_state.records["人員/耆老姓名"] == single_elder) & 
                    (st.session_state.records["支領類別"].astype(str).str.contains("工作費"))
                ]["登記時數/節數"], errors="coerce").sum()
                
                if existing_work_hrs + hours_val > LIMIT_WORK_HOURS_MONTH:
                    st.warning(f"⚠️ 警示：【{single_elder}】在【{month_str} 月】已有 {existing_work_hrs} 小時工作費紀錄！加上本次 {hours_val} 小時將超過每月 15 小時上限。")
            
            row_dict = {
                "日期": date_str,
                "申請處室": dept_val,
                "活動型態": activity_type,
                "年級班級": grade_val,
                "主辦/授課教師": teacher_val,
                "人員/耆老姓名": single_elder,
                "課程/工作項目名稱": course_title,
                "支領類別": pay_category,
                "登記時數/節數": hours_val,
                "備註": note_val
            }
            new_rows.append(row_dict)
            
            if gsheets_connected:
                ws.append_row([str(row_dict[c]) for c in COLUMNS])
                
        new_data = pd.DataFrame(new_rows)
        st.session_state.records = pd.concat([st.session_state.records, new_data], ignore_index=True)
        st.sidebar.success(f"✅ 已成功新增並即時同步 {len(elder_list)} 筆紀錄至 Google 雲端！")
        st.rerun()

tab1, tab2, tab3 = st.tabs(["📋 明細管理與編輯", "📊 自然月結與費用清冊", "📈 處室與人員時數統計"])

with tab1:
    st.subheader("明細資料表")
    if not st.session_state.records.empty:
        display_df = st.session_state.records.copy()
        display_df.index = range(1, len(display_df) + 1)
        
        edited_df = st.data_editor(
            display_df,
            use_container_width=True,
            num_rows="dynamic",
            key="records_editor"
        )
        
        col_btn1, col_btn2 = st.columns([1, 4])
        with col_btn1:
            if st.button("💾 儲存修改內容至 Google 雲端"):
                st.session_state.records = edited_df.reset_index(drop=True)
                save_all_to_sheets(st.session_state.records)
                st.success("✅ 修改已成功同步至 Google 試算表！")
                st.rerun()
                
        with col_btn2:
            if st.button("🗑️ 清空所有紀錄（慎用）"):
                st.session_state.records = pd.DataFrame(columns=COLUMNS)
                save_all_to_sheets(st.session_state.records)
                st.success("✅ 所有紀錄已清空！")
                st.rerun()
    else:
        st.info("目前尚無登記紀錄，請由左側邊欄輸入資料。")

with tab2:
    st.subheader("🗓️ 自然月結算與費用分攤清冊")
    if not st.session_state.records.empty:
        df = st.session_state.records.copy()
        df["月份"] = pd.to_datetime(df["日期"]).dt.strftime("%Y-%m")
        month_list = sorted(df["月份"].unique())
        selected_month = st.selectbox("選擇結算月份", month_list)
        
        m_df = df[df["月份"] == selected_month].copy()
        summary_list = []
        for idx, row in m_df.iterrows():
            try:
                h = float(row["登記時數/節數"])
            except Exception:
                h = 0.0
            p_cat = str(row["支領類別"])
            exp_h, imm_h, work_h = 0.0, 0.0, 0.0
            
            if "沉浸式" in p_cat:
                imm_h = h
            elif "實驗教育" in p_cat:
                exp_h = h
            elif "工作費" in p_cat:
                work_h = h
                
            summary_list.append({
                "人員/耆老姓名": row["人員/耆老姓名"],
                "申請處室": row["申請處室"],
                "沉浸式節數": imm_h,
                "實驗教育節數": exp_h,
                "工作費小時數": work_h,
                "沉浸式金額": imm_h * RATE_IMMERSIVE,
                "實驗教育金額": exp_h * RATE_EXPERIMENTAL,
                "工作費金額": work_h * RATE_WORK_FEE,
                "總金額": (imm_h * RATE_IMMERSIVE) + (exp_h * RATE_EXPERIMENTAL) + (work_h * RATE_WORK_FEE)
            })
        
        summary_df = pd.DataFrame(summary_list)
        if not summary_df.empty:
            final_person_summary = summary_df.groupby("人員/耆老姓名").agg({
                "沉浸式節數": "sum", "實驗教育節數": "sum", "工作費小時數": "sum",
                "沉浸式金額": "sum", "實驗教育金額": "sum", "工作費金額": "sum", "總金額": "sum"
            }).reset_index()
            
            final_person_summary["工作費狀態"] = final_person_summary["工作費小時數"].apply(
                lambda x: "⚠️超過每月15小時上限" if x > LIMIT_WORK_HOURS_MONTH else "正常"
            )
            
            dept_summary = summary_df.groupby("申請處室").agg({
                "沉浸式金額": "sum", "實驗教育金額": "sum", "工作費金額": "sum", "總金額": "sum"
            }).reset_index()
            
            final_person_summary.index = range(1, len(final_person_summary) + 1)
            dept_summary.index = range(1, len(dept_summary) + 1)
            
            st.write(f"### 📍 {selected_month} 月份 - 個人領據發放清冊")
            st.dataframe(final_person_summary, use_container_width=True)
            
            st.write(f"### 🏢 {selected_month} 月份 - 處室經費分攤總計")
            st.dataframe(dept_summary, use_container_width=True)
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("實驗教育總額 (400元/節)", f"NT$ {final_person_summary['實驗教育金額'].sum():,.0f}")
            col2.metric("沉浸式總額 (405元/節)", f"NT$ {final_person_summary['沉浸式金額'].sum():,.0f}")
            col3.metric("工作費總額 (196元/時)", f"NT$ {final_person_summary['工作費金額'].sum():,.0f}")
            col4.metric("本月應發放總金額", f"NT$ {final_person_summary['總金額'].sum():,.0f}")

            output_filename = f"{selected_month}_課研處經費分攤表與清冊.xlsx"
            m_df_export = m_df.copy()
            m_df_export.index = range(1, len(m_df_export) + 1)
            
            with pd.ExcelWriter(output_filename, engine='openpyxl') as writer:
                final_person_summary.to_excel(writer, index=True, sheet_name="個人領據清冊")
                dept_summary.to_excel(writer, index=True, sheet_name="處室分攤表")
                m_df_export.to_excel(writer, index=True, sheet_name="當月明細")
                
            with open(output_filename, "rb") as file:
                st.download_button(
                    label="📥 下載本月經費分攤表與清冊 (Excel)",
                    data=file,
                    file_name=output_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    else:
        st.info("尚無資料可供結算。")

with tab3:
    st.subheader("📈 處室、項目與人員時數統計")
    if not st.session_state.records.empty:
        df = st.session_state.records.copy()
        df["登記時數/節數"] = pd.to_numeric(df["登記時數/節數"], errors="coerce").fillna(0)
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.write("#### 1. 課研處累積申請總時數/節數")
            st_dept = df.groupby("申請處室")["登記時數/節數"].sum().reset_index()
            st_dept.index = range(1, len(st_dept) + 1)
            st.dataframe(st_dept, use_container_width=True)
            
        with col_b:
            st.write("#### 2. 各計畫/活動型態分布")
            st_act = df.groupby("活動型態")["登記時數/節數"].sum().reset_index()
            st_act.index = range(1, len(st_act) + 1)
            st.dataframe(st_act, use_container_width=True)

        st.write("#### 3. 個人支領類別與總時數/節數")
        st_person = df.groupby(["人員/耆老姓名", "支領類別"])["登記時數/節數"].sum().unstack(fill_value=0).reset_index()
        st_person.index = range(1, len(st_person) + 1)
        st.dataframe(st_person, use_container_width=True)
    else:
        st.info("尚無統計數據。")
