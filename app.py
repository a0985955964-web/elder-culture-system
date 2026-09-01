import streamlit as st
import pandas as pd
import datetime

# 設定頁面標題與佈局
st.set_page_config(page_title="北葉國小 - 文化協同耆老時數與鐘點費管理系統", layout="wide")

# 費率預設
RATE_EXPERIMENTAL = 400
RATE_IMMERSIVE = 405

# 初始化資料庫紀錄
if 'records' not in st.session_state:
    st.session_state.records = pd.DataFrame(columns=[
        "日期", "週次", "年級班級", "文化教師", "耆老姓名", "課程類型", "登記節數", "備註"
    ])

st.title("🌾 屏東縣北葉國小 - 文化協同耆老時數與鐘點費管理系統")

st.sidebar.header("📝 登錄耆老協同授課紀錄")

with st.sidebar.form("entry_form", clear_on_submit=True):
    date_val = st.date_input("授課日期", datetime.date.today())
    week_val = st.number_input("教學週次（第幾週）", min_value=1, max_value=25, value=1, step=1)
    grade_val = st.selectbox("年級班級", ["一年級", "二年級", "三年級", "四年級", "五年級", "六年級"])
    teacher_val = st.text_input("文化教師姓名", placeholder="例如：玉如老師")
    elder_val = st.text_input("耆老姓名", placeholder="例如：姜耆老")
    course_type = st.selectbox("課程類型", ["實驗教育授課", "沉浸式族語授課"])
    hours_val = st.number_input("授課節數", min_value=1, max_value=5, value=1, step=1)
    note_val = st.text_input("備註", placeholder="例：傳統歌謠/工藝製作")
    
    submitted = st.form_submit_button("新增紀錄")

if submitted:
    if not teacher_val or not elder_val:
        st.sidebar.error("⚠️ 請填寫文化教師與耆老姓名！")
    else:
        date_str = date_val.strftime("%Y-%m-%d")
        
        # 檢查沉浸式每週上限 (同班同週上限 1 節)
        if course_type == "沉浸式族語授課":
            existing_imm = st.session_state.records[
                (st.session_state.records["週次"] == week_val) & 
                (st.session_state.records["年級班級"] == grade_val) & 
                (st.session_state.records["課程類型"] == "沉浸式族語授課")
            ]["登記節數"].sum()
            
            if existing_imm + hours_val > 1:
                st.warning(f"⚠️ 警示：【{grade_val}】在【第 {week_val} 週】已有 {existing_imm} 節沉浸式課程。超過 1 節部分將在月結時自動改按實驗教育鐘點費（400元/節）計算！")
        
        new_data = pd.DataFrame([{
            "日期": date_str,
            "週次": week_val,
            "年級班級": grade_val,
            "文化教師": teacher_val,
            "耆老姓名": elder_val,
            "課程類型": course_type,
            "登記節數": hours_val,
            "備註": note_val
        }])
        
        st.session_state.records = pd.concat([st.session_state.records, new_data], ignore_index=True)
        st.sidebar.success("✅ 紀錄已成功新增！")

tab1, tab2, tab3 = st.tabs(["📋 明細管理", "📊 自然月結與經費分攤", "📈 時數統計彙整"])

with tab1:
    st.subheader("明細資料表")
    if not st.session_state.records.empty:
        st.dataframe(st.session_state.records, use_container_width=True)
        if st.button("🗑️ 清空所有紀錄（慎用）"):
            st.session_state.records = pd.DataFrame(columns=[
                "日期", "週次", "年級班級", "文化教師", "耆老姓名", "課程類型", "登記節數", "備註"
            ])
            st.rerun()
    else:
        st.info("目前尚無授課紀錄，請由左側邊欄輸入資料。")

with tab2:
    st.subheader("🗓️ 自然月結算與經費分攤清冊")
    
    if not st.session_state.records.empty:
        df = st.session_state.records.copy()
        df["月份"] = pd.to_datetime(df["日期"]).dt.strftime("%Y-%m")
        
        month_list = sorted(df["月份"].unique())
        selected_month = st.selectbox("選擇結算月份", month_list)
        
        m_df = df[df["月份"] == selected_month].copy()
        
        # 精準計算每筆紀錄沉浸式與實驗教育額度
        elder_summary_list = []
        
        for (elder, week, grade), group in m_df.groupby(["耆老姓名", "週次", "年級班級"]):
            group = group.sort_values(by="日期")
            imm_used = 0
            for idx, row in group.iterrows():
                h = row["登記節數"]
                c_type = row["課程類型"]
                
                exp_h = 0
                imm_h = 0
                
                if c_type == "沉浸式族語授課":
                    if imm_used < 1:
                        allowed_imm = min(h, 1 - imm_used)
                        imm_h += allowed_imm
                        exp_h += (h - allowed_imm)
                        imm_used += allowed_imm
                    else:
                        exp_h += h
                else:
                    exp_h += h
                    
                elder_summary_list.append({
                    "耆老姓名": elder,
                    "沉浸式節數": imm_h,
                    "實驗教育節數": exp_h,
                    "沉浸式金額": imm_h * RATE_IMMERSIVE,
                    "實驗教育金額": exp_h * RATE_EXPERIMENTAL,
                    "總金額": (imm_h * RATE_IMMERSIVE) + (exp_h * RATE_EXPERIMENTAL)
                })
        
        summary_df = pd.DataFrame(elder_summary_list)
        if not summary_df.empty:
            final_summary = summary_df.groupby("耆老姓名").sum().reset_index()
            
            st.write(f"### 📍 {selected_month} 月份 - 耆老鐘點費發放與經費分攤表")
            st.dataframe(final_summary, use_container_width=True)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("實驗教育總金額 (400元/節)", f"NT$ {final_summary['實驗教育金額'].sum():,}")
            col2.metric("沉浸式總金額 (405元/節)", f"NT$ {final_summary['沉浸式金額'].sum():,}")
            col3.metric("本月應發總金額", f"NT$ {final_summary['總金額'].sum():,}")

            # 導出 Excel
            output_filename = f"{selected_month}_耆老鐘點費經費分攤表.xlsx"
            with pd.ExcelWriter(output_filename, engine='openpyxl') as writer:
                final_summary.to_excel(writer, index=False, sheet_name="經費分攤表")
                m_df.to_excel(writer, index=False, sheet_name="當月明細")
                
            with open(output_filename, "rb") as file:
                st.download_button(
                    label="📥 下載本月經費分攤表 (Excel)",
                    data=file,
                    file_name=output_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    else:
        st.info("尚無資料可供結算。")

with tab3:
    st.subheader("📈 耆老與年級時數統計")
    if not st.session_state.records.empty:
        df = st.session_state.records.copy()
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.write("#### 1. 各年級累積使用時數")
            st.dataframe(df.groupby("年級班級")["登記節數"].sum().reset_index(), use_container_width=True)
            
        with col_b:
            st.write("#### 2. 各文化教師申請時數")
            st.dataframe(df.groupby("文化教師")["登記節數"].sum().reset_index(), use_container_width=True)

        st.write("#### 3. 各耆老支援總節數")
        st.dataframe(df.groupby(["耆老姓名", "課程類型"])["登記節數"].sum().unstack(fill_value=0).reset_index(), use_container_width=True)
    else:
        st.info("尚無統計數據。")
