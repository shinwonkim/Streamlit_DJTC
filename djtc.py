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
tabs = ["일별 분석","월별 분석", "지도 시각화 대시보드"]
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

        # 일별 현황 표시
        col1, col2 = st.columns(2)
        with col1:
            st.metric("일일 이용자 수", users_today, users_change)
        with col2:
            st.metric("일일 이용 건수", rides_today, rides_change)

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
    else:
        st.write("데이터가 없습니다.")
        

# 월별 분석 페이지
elif selected_tab == "월별 분석":
    st.header("월별 분석")
    
    query = "SELECT * FROM `A27P1Y_00_A27_02_전처리데이터_행정동수정_좌표기반_G1`"

    data = get_data(query)
    
if data:
    # 데이터를 DataFrame으로 변환
    df = pd.DataFrame(data)

    # '승차일시' 컬럼을 datetime 형식으로 변환
    df['승차일시'] = pd.to_datetime(df['승차일시'], errors='coerce')

    # 변환된 데이터에서 유효한 날짜만 필터링
    df = df.dropna(subset=['승차일시'])

    # 월별 데이터 프레임 생성
    df['month'] = df['승차일시'].dt.to_period('M')

    # 월별 이용자 수와 이용 건수 집계
    monthly_users = df.groupby('month')['회원ID'].nunique().reset_index(name='users')
    monthly_rides = df.groupby('month').size().reset_index(name='rides')
    monthly_distance = df.groupby('month')['이동거리'].mean().reset_index(name='avg_distance')
    monthly_cost = df.groupby('month')['승차운임비용'].mean().reset_index(name='avg_cost')

    # 월 선택
    month_list = monthly_users['month'].astype(str).tolist()
    selected_month = st.selectbox("월을 선택하세요.", month_list, index=len(month_list)-1)
    selected_month_data = df[df['month'].astype(str) == selected_month]

    # 선택된 월에 대한 정보 출력
    st.subheader(f"{selected_month}의 분석 결과")
    selected_month_users = monthly_users[monthly_users['month'].astype(str) == selected_month]['users'].iloc[0]
    selected_month_rides = monthly_rides[monthly_rides['month'].astype(str) == selected_month]['rides'].iloc[0]
    st.write(f"이용자 수: {selected_month_users}, 이용 건수: {selected_month_rides}")
        
    # 평균 이동거리 및 운임비용 출력
    avg_distance = monthly_distance[monthly_distance['month'].astype(str) == selected_month]['avg_distance'].iloc[0]
    avg_cost = monthly_cost[monthly_cost['month'].astype(str) == selected_month]['avg_cost'].iloc[0]
    st.write(f"평균 이동 거리: {avg_distance:.2f} km, 평균 운임 비용: {avg_cost:.2f} 원")

    # 월별 이용자 수 및 이용 건수 시각화
    fig = px.line(monthly_users, x='month', y='users', title='월별 이용자 수')
    st.plotly_chart(fig)

    fig2 = px.line(monthly_rides, x='month', y='rides', title='월별 이용 건수')
    st.plotly_chart(fig2)

    # 선택된 월의 상세 데이터 출력
    st.subheader("상세 데이터")
    st.write(selected_month_data)
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
        df['승차일시'] = pd.to_datetime(df['승차일시'], errors='coerce')
        df = df.dropna(subset=['승차일시', '출발지_X좌표_수정', '출발지_Y좌표_수정'])
        df['year_month'] = df['승차일시'].dt.to_period('M').astype(str)

        month_options = df['year_month'].unique()
        selected_month = st.selectbox("월을 선택하세요", month_options)

        monthly_data = df[df['year_month'] == selected_month]
        location_counts_si_gun_gu = monthly_data['출발지_시군구'].value_counts().nlargest(10)
        location_counts_eup_myun_dong = monthly_data['출발지_읍면동'].value_counts().nlargest(10)

        m = folium.Map(location=[36.3504, 127.3845], zoom_start=11)
        marker_cluster = MarkerCluster().add_to(m)

        for idx, row in monthly_data.iterrows():
            if pd.notna(row['출발지_X좌표_수정']) and pd.notna(row['출발지_Y좌표_수정']):
                count = location_counts_si_gun_gu.get(row['출발지_읍면동'], 0)
                folium.CircleMarker(
                    location=[row['출발지_Y좌표_수정'], row['출발지_X좌표_수정']],
                    radius=7,
                    color=get_color(count),
                    fill=True,
                    fill_color=get_color(count),
                    fill_opacity=0.7,
                    popup=f"{row['출발지']}:"
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

        # 시간대별 운전자 수와 이용자 수 시각화
        df_may_unique = df.drop_duplicates(subset='기사ID')
        grouped_count = df_may_unique.groupby('예약_시')['기사ID'].count().reset_index()
        df_may_broad = df.drop_duplicates(subset='회원ID')
        per_count = df_may_broad.groupby('예약_시')['회원ID'].count().reset_index()

        # 라인 플롯 생성
        fig3 = go.Figure()

        # 첫 번째 라인 플롯 추가 (시간대별 운전자 수)
        fig3.add_trace(go.Scatter(
            x=grouped_count["예약_시"],
            y=grouped_count["기사ID"],
            mode='lines+markers',
            line=dict(color='darkblue', width=3),
            marker=dict(size=6, color='red', line=dict(width=2, color='white')),
            name='시간대별 운전자 수'
        ))

        # 두 번째 라인 플롯 추가 (시간대별 이용자 수)
        fig3.add_trace(go.Scatter(
            x=per_count["예약_시"],
            y=per_count["회원ID"],
            mode='lines+markers',
            line=dict(color='darkgreen', width=3),
            marker=dict(size=6, color='orange', line=dict(width=2, color='white')),
            name='시간대별 이용자 수'
        ))

        # 레이아웃 업데이트 및 버튼 추가
        fig3.update_layout(
            title={
                'text': "<b>월별 수요 & 공급 </b>",
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
                'text': "수 (단위: 명)",
                'font': {
                    'family': "Courier New, monospace",  # y축 제목 폰트 패밀리 변경
                    'size': 15,  # y축 제목 폰트 크기
                    'color': "black"  # y축 제목 폰트 색상
                }
            }
        )
        fig3.update_xaxes(tickmode='array', tickvals=np.arange(0, 24), tickformat="d")
        fig3.update_yaxes(tickformat="d")

        st.plotly_chart(fig3, use_container_width=True)
        
                
# 지도 시각화 대시보드 페이지
elif selected_tab == "지도 시각화 대시보드":
    st.header("지도 시각화 대시보드")

    # SQL 쿼리 작성
    query = "SELECT * FROM 5. 배차 이력 정보_2022"  

    # 데이터 가져오기
    raw_data = get_data(query)

    if data:    
            # 데이터를 DataFrame으로 변환
        df = pd.DataFrame(data)

        # 데이터 샘플 출력
        st.write("Data Sample:", df.head())
        st.write("Data Info:", df.info())
            

    else:
        st.write("데이터가 없습니다.")
