import streamlit as st
import pandas as pd
import datetime

# 設定頁面標題與佈局
st.set_page_config(page_title="北葉國小 - 文化協同耆老與工作費管理系統", layout="wide")

# 費率與上限預設
RATE_EXPERIMENTAL = 400      # 實驗教育鐘點費 (元/節)
RATE_IMMERSIVE = 405         # 沉浸式族語鐘點費 (元/節)
RATE_WORK_FEE = 196          # 臨時工作費時薪 (元/小時)
LIMIT_WORK_HOURS_MONTH = 15  # 工作費每月上限時數 (小時/月)

# 初始化資料庫紀錄
if 'records' not in st.session_state:
    st.session_state.records = pd.DataFrame(columns=[
        "日期", "週次", "申請處室", "活動型態", "年級班級", "主辦/負責人", "人員/耆老姓名", "課程/活動/工作項目", "支領類別", "登記時數/節數", "備註"
    ])

st.title("🌾 屏東縣北葉國小 - 文化協同耆老時數、鐘點費與工作費管理系統")

st.sidebar.header("📝 登錄耆老協同 / 臨時工作費紀錄")

with st.sidebar.form("entry_form", clear_on_submit=True):
    date_val = st.date_input("授課/工作日期", datetime.date.today())
    week_val = st.number_input("教學週次（第幾週）", min_value=1, max_value=25, value=1, step=1)
    
    dept_val = st.selectbox("申請處室", ["課研處/研發處（實驗教育/專案）", "教導處（年級課程）", "總務處/其他"])
    activity_type = st.selectbox("活動/計畫型態", ["一般年級文化課", "校外參訪協同", "全校性大活動", "校本課程/研習研發", "行政支援/臨時工作"])
    
    grade_val = st.selectbox("適用年級/對象", ["全校", "一年級", "二年級", "三年級", "四年級", "五年級", "六年級", "高年級", "低年級", "不限/專案"])
    teacher_val = st.text_input("主辦/負責教師", placeholder="例如：玉如老師 / 承彥老師")
    
    # 支援同時輸入一位或多位耆老
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
        st.sidebar.error("⚠️ 請填寫主辦/負責教師與人員/耆老姓名！")
    else:
        date_str = date_val.strftime("%Y-%m-%d")
        month_str = date_val.strftime("%Y-%m")
        
        # 解析多位耆老姓名 (以逗號或頓號拆分)
        raw_elders = elder_input.replace("、", ",").replace(" ", "").split(",")
        elder_list = [e.strip() for e in raw_elders if e.strip()]
        
        # 1. 檢查沉浸式每週上限 (僅針對一般年級文化課控管：同班同週上限 1 節)
        if "沉浸式" in pay_category and activity_type == "一般年級文化課":
            existing_imm = st.session_state.records[
                (st.session_state.records["週次"] == week_val) & 
                (st.session_state.records["年級班級"] == grade_val) & 
                (st.session_state.records["支領類別"].str.contains("沉浸式")) &
                (st.session_state.records["活動型態"] == "一般年級文化課")
            ]["登記時數/節數"].sum()
            
            if existing_imm + hours_val > 1:
                st.warning(f"⚠️ 警示：【{grade_val}】在【第 {week_val} 週】已有 {existing_imm} 節沉浸式課程。超過 1 節部分將在月結時自動改按實驗教育鐘點費（400元/節）計算！")
        
        # 2. 針對拆解後的每一位耆老獨立新增一筆紀錄
        new_rows = []
        for single_elder in elder_list:
            # 檢查工作費每月上限 (每人每月上限 15 小時)
            if "工作費" in pay_category:
                existing_work_hrs = st.session_state.records[
                    (st.session_state.records["日期"].str.startswith(month_str)) & 
                    (st.session_state.records["人員/耆老姓名"] == single_elder) & 
                    (st.session_state.records["支領類別"].str.contains("工作費"))
                ]["登記時數/節數"].sum()
                
                if existing_work_hrs + hours_val > LIMIT_WORK_HOURS_MONTH:
                    st.warning(f"⚠️ 警示：【{single_elder}】在【{month_str} 月】已有 {existing_work_hrs} 小時工作費紀錄！加上本次 {hours_val} 小時將超過每月 15 小時上限。")
            
            new_rows.append({
                "日期": date_str,
                "週次": week_val,
                "申請處室": dept_val,
                "活動型態": activity_type,
                "年級班級": grade_val,
                "主辦/負責人": teacher_val,
                "人員/耆老姓名": single_elder,
                "課程/工作項目名稱": course_title,
                "支領類別": pay_category,
                "登記時數/節數": hours_val,
                "備註": note_val
            })
            
        new_data = pd.DataFrame(new_rows)
        st.session_state.records = pd.concat([st.session_state.records, new_data], ignore_index=True)
        st.sidebar.success(f"✅ 已成功為 {len(elder_list)} 位人員/耆老新增紀錄！")

tab1, tab2, tab3 = st.tabs(["📋 明細管理", "📊 自然月結與費用清冊", "📈 處室與人員時數統計"])

with tab1:
    st.subheader("明細資料表")
    if not st.session_state.records.empty:
        st.dataframe(st.session_state.records, use_container_width=True)
        if st.button("🗑️ 清空所有紀錄（慎用）"):
            st.session_state.records = pd.DataFrame(columns=[
                "日期", "週次", "申請處室", "活動型態", "年級班級", "主辦/負責人", "人員/耆老姓名", "課程/工作項目名稱", "支領類別", "登記時數/節數", "備註"
            ])
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
        
        # 計算費用邏輯
        summary_list = []
        
        for idx, row in m_df.iterrows():
            h = row["登記時數/節數"]
            p_cat = row["支領類別"]
            
            exp_h = 0
            imm_h = 0
            work_h = 0
            
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
            # 1. 個人清冊
            final_person_summary = summary_df.groupby("人員/耆老姓名").agg({
                "沉浸式節數": "sum",
                "實驗教育節數": "sum",
                "工作費小時數": "sum",
                "沉浸式金額": "sum",
                "實驗教育金額": "sum",
                "工作費金額": "sum",
                "總金額": "sum"
            }).reset_index()
            
            # 檢查是否有超過 15 小時工作費者
            final_person_summary["工作費狀態"] = final_person_summary["工作費小時數"].apply(
                lambda x: "⚠️超過每月15小時上限" if x > LIMIT_WORK_HOURS_MONTH else "正常"
            )
            
            # 2. 處室分攤清冊
            dept_summary = summary_df.groupby("申請處室").agg({
                "沉浸式金額": "sum",
                "實驗教育金額": "sum",
                "工作費金額": "sum",
                "總金額": "sum"
            }).reset_index()
            
            st.write(f"### 📍 {selected_month} 月份 - 個人領據發放清冊")
            st.dataframe(final_person_summary, use_container_width=True)
            
            st.write(f"### 🏢 {selected_month} 月份 - 處室經費分攤總計")
            st.dataframe(dept_summary, use_container_width=True)
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("實驗教育總額 (400元/節)", f"NT$ {final_person_summary['實驗教育金額'].sum():,}")
            col2.metric("沉浸式總額 (405元/節)", f"NT$ {final_person_summary['沉浸式金額'].sum():,}")
            col3.metric("工作費總額 (196元/時)", f"NT$ {final_person_summary['工作費金額'].sum():,}")
            col4.metric("本月應發放總金額", f"NT$ {final_person_summary['總金額'].sum():,}")

            # 導出 Excel
            output_filename = f"{selected_month}_費用經費分攤表與清冊.xlsx"
            with pd.ExcelWriter(output_filename, engine='openpyxl') as writer:
                final_person_summary.to_excel(writer, index=False, sheet_name="個人領據清冊")
                dept_summary.to_excel(writer, index=False, sheet_name="處室分攤表")
                m_df.to_excel(writer, index=False, sheet_name="當月明細")
                
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
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.write("#### 1. 各處室累積申請時數/節數")
            st.dataframe(df.groupby("申請處室")["登記時數/節數"].sum().reset_index(), use_container_width=True)
            
        with col_b:
            st.write("#### 2. 各計畫/活動型態分布")
            st.dataframe(df.groupby("活動型態")["登記時數/節數"].sum().reset_index(), use_container_width=True)

        st.write("#### 3. 個人支領類別與總時數/節數")
        st.dataframe(df.groupby(["人員/耆老姓名", "支領類別"])["登記時數/節數"].sum().unstack(fill_value=0).reset_index(), use_container_width=True)
    else:
        st.info("尚無統計數據。")
