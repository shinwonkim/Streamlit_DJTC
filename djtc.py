## 회사 컴퓨터 메모리 부족으로 인한 시각화  방법
## 클러스터링을 활용하여 메모리 부족 해결 
## 이것도 안된다면 지도 시각화는 회사 컴퓨터로 불가능 
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import mysql.connector
from mysql.connector import Error
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import folium_static
from streamlit.components.v1 import html
import plotly.graph_objects as go
import numpy as np


# MySQL 데이터베이스 연결 설정
def create_connection():
    connection = None
    try:
        connection = mysql.connector.connect(
            host="172.16.2.56",  # 서버의 호스트 주소
            user="djtc",        # MySQL 사용자 이름
            password="EBIG",    # MySQL 비밀번호
            database="djtcdb"   # 연결할 데이터베이스 이름
        )
        if connection.is_connected():
            st.success("Successfully connected to the database")
    except Error as e:
        st.error(f"The error '{e}' occurred")
    
    return connection

# 데이터베이스에서 데이터 가져오기
def get_data(query):
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)
    result = None
    try:
        cursor.execute(query)
        result = cursor.fetchall()
    except Error as e:
        st.error(f"The error '{e}' occurred")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
    return result

# Streamlit 애플리케이션
st.title("교통약자 이용자 현황 대시보드")

# 탭 설정
tabs = ["일별 분석","월별 분석", "최적 차고지 결과"]
selected_tab = st.sidebar.selectbox("교통약자 지원차량 데이터분석", tabs)

# 일별 분석 페이지
if selected_tab == "일별 분석":
    st.header("일별 분석")
    # SQL 쿼리 작성
    query = "SELECT * FROM `A27P1Y_00_A27_02_전처리데이터_행정동수정_좌표기반_G1`"

    # 데이터 가져오기
    data = get_data(query)
    if data:    
        # 데이터를 DataFrame으로 변환
        df = pd.DataFrame(data)

        # 데이터 샘플 출력
        st.write("Data Sample:", df.head())
        st.write("Data Info:", df.info())

        # '승차일시' 컬럼을 datetime 형식으로 변환
        df['승차일시'] = pd.to_datetime(df['승차일시'], errors='coerce')

        # 변환된 데이터에서 유효한 날짜만 필터링
        df = df.dropna(subset=['승차일시'])

        # 일별 데이터 프레임 생성
        df['date'] = df['승차일시'].dt.date

        # 일별 이용자 수와 이용 건수 집계
        daily_users = df.groupby('date')['회원ID'].nunique().reset_index(name='users')
        daily_rides = df.groupby('date').size().reset_index(name='rides')
        daily_usage = df.groupby('date')['회원ID'].count().reset_index(name='usage')

        # 날짜 선택
        selected_date = st.date_input("날짜를 선택하세요.", datetime.now().date())
        previous_date = selected_date - timedelta(days=1)

        # 선택한 날짜의 데이터 필터링
        selected_day_users = daily_users[daily_users['date'] == selected_date]
        selected_day_rides = daily_rides[daily_rides['date'] == selected_date]
        selected_day_usage = daily_usage[daily_usage['date'] == selected_date]
        
        previous_day_users = daily_users[daily_users['date'] == previous_date]
        previous_day_rides = daily_rides[daily_rides['date'] == previous_date]
        previous_day_usage = daily_usage[daily_usage['date'] == previous_date]

        if not selected_day_users.empty:
            users_today = selected_day_users.iloc[0]['users']
            rides_today = selected_day_rides.iloc[0]['rides']
            usage_today = selected_day_usage.iloc[0]['usage']
        else:
            users_today = 0
            rides_today = 0
            usage_today = 0

        if not previous_day_users.empty:
            users_yesterday = previous_day_users.iloc[0]['users']
            rides_yesterday = previous_day_rides.iloc[0]['rides']
            usage_yesterday = previous_day_usage.iloc[0]['usage']
        else:
            users_yesterday = 0
            rides_yesterday = 0
            usage_yesterday = 0

        # 전일 대비 증감 계산
        users_change = int(users_today - users_yesterday)  # int로 변환
        rides_change = int(rides_today - rides_yesterday)  # int로 변환

        # 일일 보고 형태 표 생성
        summary_data = {
            '구분': ['총 건수', '이용자수', '이용자 이용횟수'],
            '전일 (A)': [rides_yesterday, users_yesterday, usage_yesterday / users_yesterday if users_yesterday != 0 else 0],
            '당일 (B)': [rides_today, users_today, usage_today / users_today if users_today != 0 else 0],
            '전일대비(B-A)': [rides_today - rides_yesterday, users_today - users_yesterday, 
                             (usage_today / users_today if users_today != 0 else 0) - (usage_yesterday / users_yesterday if users_yesterday != 0 else 0)]
        }
        summary_df = pd.DataFrame(summary_data)
        st.write("일일 보고 형태 표")
        st.table(summary_df)

        # 일별 현황 표시
        col1, col2 = st.columns(2)
        with col1:
            st.metric("일일 이용자 수", users_today, users_change)
        with col2:
            st.metric("일일 이용 건수", rides_today, rides_change)

        # 수요 공급 시각화
        # '예약시간'에서 시간만 추출
        df['예약_시'] = df['예약시간'].dt.hour

        # 선택한 날짜의 시간대별 데이터 필터링
        selected_date_data = df[df['date'] == selected_date]

        # 시간대별 기사 수와 회원 수 계산
        driver_count = selected_date_data.groupby('예약_시')['기사ID'].nunique().reset_index()
        user_count = selected_date_data.groupby('예약_시')['회원ID'].nunique().reset_index()

        # 라인 플롯 생성
        fig3 = go.Figure()

        # 첫 번째 라인 플롯 추가 (시간대별 운전자수)
        fig3.add_trace(go.Scatter(
            x=driver_count["예약_시"],
            y=driver_count["기사ID"],
            mode='lines+markers',
            line=dict(color='darkblue', width=3),
            marker=dict(size=6, color='red', line=dict(width=2, color='white')),
            name='시간대별 운전자수'
        ))

        # 두 번째 라인 플롯 추가 (시간대별 이용자수)
        fig3.add_trace(go.Scatter(
            x=user_count["예약_시"],
            y=user_count["회원ID"],
            mode='lines+markers',
            line=dict(color='darkgreen', width=3),
            marker=dict(size=6, color='orange', line=dict(width=2, color='white')),
            name='시간대별 이용자수'
        ))

        # 레이아웃 업데이트 및 버튼 추가
        fig3.update_layout(
            title={
                'text': f"<b>{selected_date} 시간대별 수요 & 공급 </b>",
                'font': {
                    'family': "fantasy",  # 제목 폰트 패밀리 변경
                    'size': 20,  # 제목 폰트 크기
                    'color': "black"  # 제목 폰트 색상
                }
            },
            xaxis_title={
                'text': "시간대",
                'font': {
                    'family': "Courier New, monospace",  # x축 제목 폰트 패밀리 변경
                    'size': 15,  # x축 제목 폰트 크기
                    'color': "black"  # x축 제목 폰트 색상
                }
            },
            yaxis_title={
                'text': "수 {단위 : 명}",
                'font': {
                    'family': "Courier New, monospace",  # y축 제목 폰트 패밀리 변경
                    'size': 15,  # y축 제목 폰트 크기
                    'color': "black"  # y축 제목 색상 
                }
            }
        )
        fig3.update_xaxes(tickmode='array', tickvals=np.arange(0, 24), tickformat="d")
        fig3.update_yaxes(tickformat="d")

        # 그래프 출력
        st.plotly_chart(fig3)
        
    else:
        st.write("데이터가 없습니다.")
        

# 월별 분석 페이지
elif selected_tab == "월별 분석":
    st.header("월별 분석")
    
    query = "SELECT * FROM `A27P1Y_00_A27_02_전처리데이터_행정동수정_좌표기반_G1`"

    data = get_data(query)
    
    def get_color(count):
        if count < 10:
            return 'lightblue'
        elif count < 20:
            return 'blue'
        elif count < 50:
            return 'darkblue'
        else:
            return 'purple'


    if data:
        df = pd.DataFrame(data)
        st.write("Initial Data:", df.head())  # 데이터프레임 초기 상태 출력
        df['승차일시'] = pd.to_datetime(df['승차일시'], errors='coerce')
        df = df.dropna(subset=['승차일시', '출발지_X좌표_수정', '출발지_Y좌표_수정'])
        df['year_month'] = df['승차일시'].dt.to_period('M').astype(str)

        month_options = df['year_month'].unique()
        selected_month = st.selectbox("월을 선택하세요", month_options)

        monthly_data = df[df['year_month'] == selected_month]

        # '승차일시'에서 일자만 추출
        monthly_data['day'] = monthly_data['승차일시'].dt.date

        # 일별 이용자 수와 이용 건수 집계
        daily_users = monthly_data.groupby('day')['회원ID'].nunique().reset_index(name='users')
        daily_rides = monthly_data.groupby('day').size().reset_index(name='rides')
        
        # 선택된 월의 총 이용자 수와 총 이용 건수 계산
        total_users = daily_users['users'].sum()
        total_rides = daily_rides['rides'].sum()

        # 전월 대비 증감 계산 (이전 월 데이터 필요)
        previous_month = (datetime.strptime(selected_month + '-01', '%Y-%m-%d') - pd.DateOffset(months=1)).strftime('%Y-%m')
        previous_month_data = df[df['year_month'] == previous_month]
        previous_daily_users = previous_month_data.groupby(previous_month_data['승차일시'].dt.date)['회원ID'].nunique().reset_index(name='users')
        previous_daily_rides = previous_month_data.groupby(previous_month_data['승차일시'].dt.date).size().reset_index(name='rides')
        previous_total_users = int(previous_daily_users['users'].sum())
        previous_total_rides = int(previous_daily_rides['rides'].sum())

        users_change = int(total_users - previous_total_users)
        rides_change = int(total_rides - previous_total_rides)

        # 월별 현황 표시
        col1, col2 = st.columns(2)
        with col1:
            st.metric("월별 총 이용자 수", total_users, users_change)
        with col2:
            st.metric("월별 총 이용 건수", total_rides, rides_change)

        location_counts_si_gun_gu = monthly_data['출발지_시군구'].value_counts().nlargest(10)
        location_counts_eup_myun_dong = monthly_data['출발지_읍면동'].value_counts().nlargest(10)


        monthly_data = df[df['year_month'] == selected_month]
        location_counts_si_gun_gu = monthly_data['출발지_시군구'].value_counts().nlargest(10)
        location_counts_eup_myun_dong = monthly_data['출발지_읍면동'].value_counts().nlargest(10)

        m = folium.Map(location=[36.3504, 127.3845], zoom_start=11)
        marker_cluster = MarkerCluster().add_to(m)

        for idx, row in monthly_data.iterrows():
            if pd.notna(row['출발지_X좌표_수정']) and pd.notna(row['출발지_Y좌표_수정']):
                count = location_counts_si_gun_gu.get(row['출발지_시군구'], 0)
                folium.CircleMarker(
                    location=[row['출발지_Y좌표_수정'], row['출발지_X좌표_수정']],
                    radius=7,
                    color=get_color(count),
                    fill=True,
                    fill_color=get_color(count),
                    fill_opacity=0.7,
                    popup=f"{row['출발지_시군구']}{row['출발지_읍면동']}: {count}건"
                ).add_to(marker_cluster)

        folium_static(m)

        # 상위 10개 출발지 시군구 바 그래프
        fig_si_gun_gu = px.bar(
            location_counts_si_gun_gu.reset_index(name='count').rename(columns={'index': '출발지_시군구'}),
            x='출발지_시군구',
            y='count',
            labels={'출발지_시군구': '출발지_시군구', 'count': '건수'},
            title="Top 10 출발지 시군구",
            color='count',
            color_continuous_scale='greens',  # 초록색 그라데이션
            range_color=[0, location_counts_si_gun_gu.max()]  # 색상 범위
        )
        st.plotly_chart(fig_si_gun_gu, use_container_width=True)

        # 상위 10개 출발지 읍면동 바 그래프
        fig_eup_myun_dong = px.bar(
            location_counts_eup_myun_dong.reset_index(name='count').rename(columns={'index': '출발지_읍면동'}),
            x='출발지_읍면동',
            y='count',
            labels={'출발지_읍면동': '출발지_읍면동', 'count': '건수'},
            title="Top 10 출발지 읍면동",
            color='count',
            color_continuous_scale='greens',  # 초록색 그라데이션
            range_color=[0, location_counts_eup_myun_dong.max()]  # 색상 범위
        )
        st.plotly_chart(fig_eup_myun_dong, use_container_width=True)
        
        # '예약시간' 컬럼을 datetime 형식으로 변환
        monthly_data['예약시간'] = pd.to_datetime(monthly_data['예약시간'], errors='coerce')

        # '예약시간'에서 시간만 추출
        monthly_data['예약_시'] = monthly_data['예약시간'].dt.hour

        # 시간대별 기사 수와 회원 수 계산
        driver_count = monthly_data.groupby('예약_시')['기사ID'].nunique().reset_index()
        user_count = monthly_data.groupby('예약_시')['회원ID'].nunique().reset_index()

        # 라인 플롯 생성
        fig3 = go.Figure()

        # 첫 번째 라인 플롯 추가 (시간대별 운전자수)
        fig3.add_trace(go.Scatter(
            x=driver_count["예약_시"],
            y=driver_count["기사ID"],
            mode='lines+markers',
            line=dict(color='darkblue', width=3),
            marker=dict(size=6, color='red', line=dict(width=2, color='white')),
            name='시간대별 운전자수'
        ))

        # 두 번째 라인 플롯 추가 (시간대별 이용자수)
        fig3.add_trace(go.Scatter(
            x=user_count["예약_시"],
            y=user_count["회원ID"],
            mode='lines+markers',
            line=dict(color='darkgreen', width=3),
            marker=dict(size=6, color='orange', line=dict(width=2, color='white')),
            name='시간대별 이용자수'
        ))

        # 레이아웃 업데이트 및 버튼 추가
        fig3.update_layout(
            title={
                'text': f"<b>{selected_month} 시간대별 수요 & 공급 </b>",
                'font': {
                    'family': "fantasy",  # 제목 폰트 패밀리 변경
                    'size': 20,  # 제목 폰트 크기
                    'color': "black"  # 제목 폰트 색상
                }
            },
            xaxis_title={
                'text': "시간대",
                'font': {
                    'family': "Courier New, monospace",  # x축 제목 폰트 패밀리 변경
                    'size': 15,  # x축 제목 폰트 크기
                    'color': "black"  # x축 제목 폰트 색상
                }
            },
            yaxis_title={
                'text': "수 {단위 : 명}",
                'font': {
                    'family': "Courier New, monospace",  # y축 제목 폰트 패밀리 변경
                    'size': 15,  # y축 제목 폰트 크기
                    'color': "black"  # y축 제목 폰트 색상
                }
            }
        )
        fig3.update_xaxes(tickmode='array', tickvals=np.arange(0, 24), tickformat="d")
        fig3.update_yaxes(tickformat="d")

        # 그래프 출력
        st.plotly_chart(fig3)
        
    else:
        st.write("데이터가 없습니다.")
                
# 지도 시각화 대시보드 페이지
elif selected_tab == "최적 차고지 결과":
    st.markdown("<h2 style='font-size:24px;'>최적 차고지 결과 대시보드</h2>", unsafe_allow_html=True)


    col1, col2 = st.columns([3, 1])
    
    # 지도 시각화
    with col1:
        # HTML 파일을 읽어서 삽입
        with open("최적차고지.html", "r", encoding="utf-8") as file:
            html_data = file.read()
        html(html_data, height=600)
    
    # 출발지 수요 상위 10위 
    with col2:
        st.markdown("<h3 style='font-size:17px;'>출발지 수요 TOP 10</h3>", unsafe_allow_html=True)
        top10_dong = pd.DataFrame({
            '동이름': ['유성구 한밭대로', '중구 동서대로', '대덕구 신일동', '동구 비룡동', '서구 원정동', '동구 장척동'],
            'cars': [32, 24, 21, 21, 8, 5]
        })
        styled_table = top10_dong.style.set_table_styles(
            [{
                'selector': 'thead th',
                'props': [('background-color', '#4CAF50'), ('color', 'white'), ('font-weight', 'bold')]
            }, {
                'selector': 'tbody tr:nth-child(even)',
                'props': [('background-color', '#f2f2f2')]
            }, {
                'selector': 'tbody tr:hover',
                'props': [('background-color', '#ddd')]
            }]
        ).set_properties(**{
            'text-align': 'center',
            'font-size': '13px',
            'border': '1px solid black'
        })
        st.dataframe(styled_table)

