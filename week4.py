import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pymssql
from datetime import datetime, timedelta    
today = datetime.now()

if "data" not in st.session_state:
    st.session_state.data = None
if 'forsale' not in st.session_state:
    st.session_state.forsale = None
if 'deal' not in st.session_state:
    st.session_state.deal = None

st.title("第四周：SQL查詢與資料視覺化(2)")
user = st.sidebar.text_input("SQL使用者名稱", value="M07927")
password = st.sidebar.text_input("請輸入密碼", type="password")

st.sidebar.markdown('---')

START_YEAR = st.sidebar.number_input("開始年份", min_value=2010, max_value=today.year, value=2021, step=1)
START_QUARTER = st.sidebar.number_input("開始季", min_value=1, max_value=4, value=1, step=1)
END_YEAR = st.sidebar.number_input("結束年份", min_value=START_YEAR, max_value=today.year, value=START_YEAR, step=1)
if START_YEAR == END_YEAR:
    END_QUARTER = st.sidebar.number_input("結束季", min_value=START_QUARTER, max_value=4, value=START_QUARTER, step=1)
else:
    END_QUARTER = st.sidebar.number_input("結束季", min_value=1, max_value=4, value=1, step=1)

START_DATE = f"{START_YEAR:04d}{START_QUARTER*3-2:02d}"  
END_DATE = f"{END_YEAR:04d}{END_QUARTER*3:02d}"
btn_SQL = st.sidebar.button("執行SQL查詢")

if btn_SQL==True:
    try:
        conn = pymssql.connect(
                server='10.11.144.102',
                user=f'{user}',
                password= f'{password}',
                database='DB_DIGITECH',
                as_dict=True
            )
        cursor = conn.cursor()
        st.success("SQL連線成功！") 

        quarter_list = []
        for year in range(START_YEAR, END_YEAR + 1):
            start_q = START_QUARTER if year == START_YEAR else 1
            end_q = END_QUARTER if year == END_YEAR else 4
            for quarter in range(start_q, end_q + 1):
                quarter_list.append(f"{year - 1911}Q{quarter}")
        
        ### 動態調整資料表名稱[折價明細] ###
        cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
        tables = sorted([item['TABLE_NAME'] for item in cursor.fetchall() if item['TABLE_NAME'].startswith('T_折價')])

        cursor.execute(f"SELECT * FROM {tables[-1]} WHERE [成交年月] between {START_DATE} and {END_DATE}")
        
        st.session_state.data= pd.DataFrame(cursor.fetchall())
        
        ### 動態調整資料表名稱[待售新成屋] ###
        cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
        tables = sorted([item['TABLE_NAME'] for item in cursor.fetchall() if item['TABLE_NAME'].endswith('待售新成屋')])

        cursor.execute(f"""SELECT * FROM {tables[-1]} 
                            WHERE CAST(年度 AS VARCHAR) + 季 in ({quarter_list})
                                AND 區 = '全區'
                        """.replace("[","" ).replace("]","" ))
        
        st.session_state.forsale= pd.DataFrame(cursor.fetchall())

        ### 動態調整資料表名稱[成交] ###
        cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
        tables = sorted([item['TABLE_NAME'] for item in cursor.fetchall() if item['TABLE_NAME'].startswith('D_GIS_十二都')])
        
        cursor.execute(f"""SELECT * FROM {tables[-1]} 
                            WHERE 交易年月 between {START_DATE} and {END_DATE} """)
        
        st.session_state.deal= pd.DataFrame(cursor.fetchall())

    except pymssql.Error as e:
        st.error(f"SQL連線失敗: {e}")  

     

if st.session_state.data is not None:
    
    
    tab1, tab2 = st.tabs(["SQL查詢", "資料視覺化"])
    with tab1:
        city_options = sorted(st.session_state.data['縣市'].unique().tolist())
        city = st.selectbox("請選擇縣市", options=city_options)    
        dist_options = sorted(st.session_state.data[st.session_state.data['縣市'] == city]['鄉鎮市區'].unique().tolist())
        # HW1 : 新增全區選項  [TIPS: 使用list append() 方法將 '全區' 加入到縣市選項中]
        dist_options.insert(0, '全區')
        dist = st.selectbox("請選擇鄉鎮市區", options=dist_options)
        data = st.session_state.data[(st.session_state.data['縣市'] == city) & (st.session_state.data['鄉鎮市區'] == dist)] if dist != '全區' else st.session_state.data[st.session_state.data['縣市'] == city]
        st.metric(label="資料筆數", value=len(data))
        st.dataframe(st.session_state.deal)

        
    with tab2:
        c1, c2, c3, c4 = st.columns([4,1,4,1])  
        with c1:
            Y_axis = st.selectbox("X軸", options=['成交單價','開價單價','銷售天期','折價率'])
        with c3:
            available_options = ['成交單價','開價單價','銷售天期','折價率']
            available_options.remove(Y_axis)
            colY_axis = st.selectbox("副X軸", options=available_options)
        with c2:
            Y_color = st.color_picker("", value="#000000")
        with c4:
            colY_color = st.color_picker("", value="#6F6D6D")
        
        b1,b2,b3 = st.columns([1,1,3])
        with b1:
            btn_count = st.checkbox("交易件數")
        with b2:
            btn_daterange = st.checkbox("切換X軸")
        
        # HW2: 新增一個按鈕，讓使用者自行選擇用'成交季'或是'成交年月'作為X軸的分組依據  
        X_axis = '成交季' if btn_daterange else '成交年月'
        X_axis_deal = '交易季' if btn_daterange else '交易年月'
        
        # [折價明細]進行groupby計算平均值
        average_value = data.groupby(X_axis).agg({  
            '開價單價': 'mean',
            '銷售天期': 'mean',
            '折價率': 'mean',
            '縣市': 'count' if btn_count else 'first'
        }).reset_index()   
        
        # [GIS成交資料]進行groupby計算平均值
        average_deal = st.session_state.deal.groupby(X_axis_deal).agg({
            '合併單價': 'mean'}).reset_index().rename(columns={X_axis_deal: X_axis, '合併單價': '成交單價'})
        
        # 轉換日期格式  
        if not btn_daterange:
            average_value[X_axis] = pd.to_datetime(average_value[X_axis], format='%Y%m') 
            average_deal[X_axis] = pd.to_datetime(average_deal[X_axis], format='%Y%m') 
        
        # 合併兩個DataFrame 
        merge_df = pd.merge(average_value, average_deal, on=X_axis, how='outer')
        

        with st.expander("查看數據"):
            st.dataframe(merge_df) 
            st.write(merge_df.dtypes)

        fig = make_subplots(specs=[[{"secondary_y": True}]])  
        if btn_count:
            fig.add_trace(go.Bar(
            x=merge_df[X_axis],
            y=merge_df['縣市'],
            name='交易件數',
            marker_color='#6F6D6D',
            opacity=0.6
            ), secondary_y=btn_count) 

        fig.add_trace(go.Scatter(
            x=merge_df[X_axis],
            y=merge_df[Y_axis],
            name=Y_axis,
            marker_color=Y_color
        ), secondary_y=False)  
        fig.add_trace(go.Scatter(
            x=merge_df[X_axis],
            y=merge_df[colY_axis],
            name=colY_axis,
            marker_color=colY_color
        ), secondary_y=not(btn_count)) 
                
        fig.update_layout(
            title=f"{Y_axis} 與 {colY_axis} 的平均值",
            xaxis_title=X_axis,
            template='plotly_white'
        )  
        fig.update_yaxes(title_text=Y_axis, secondary_y=False)
        fig.update_yaxes(title_text='交易件數' if btn_count else colY_axis  , secondary_y=True)

        st.plotly_chart(fig, use_container_width=True)
        