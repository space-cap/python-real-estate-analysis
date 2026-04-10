import streamlit as st
import pandas as pd
import altair as alt

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정 (와이드 모드)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="PRO 부동산 매매지수 대시보드", page_icon="📈", layout="wide", initial_sidebar_state="expanded")

# -----------------------------------------------------------------------------
# 2. 데이터 로드
# -----------------------------------------------------------------------------
@st.cache_data
def load_data():
    file_path = 'data/apt_price_20260408.xlsx' 
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path, header=0)
    except FileNotFoundError:
        st.error(f"⚠️ 데이터 파일을 찾을 수 없습니다: {file_path}")
        st.stop()
        
    first_col = df.columns[0]
    df.rename(columns={first_col: '지역명'}, inplace=True)
    return df

# -----------------------------------------------------------------------------
# 3. 데이터 전처리 함수
# -----------------------------------------------------------------------------
@st.cache_data
def process_growth_data_pro(df, target_regions, start_date, end_date, is_exact_match=False):
    df['clean_region'] = df['지역명'].astype(str).str.replace(r'\s+', '', regex=True)
    df['지역명'] = df['지역명'].astype(str).str.strip()
    
    clean_targets = [str(x).replace(' ', '') for x in target_regions]
    
    if is_exact_match:
        df_filtered = df[df['clean_region'].isin(clean_targets)].copy()
    else:
        pattern = '|'.join(clean_targets)
        df_filtered = df[df['clean_region'].str.contains(pattern, na=False)].copy()
        
    df_filtered['latest_val'] = pd.to_numeric(df_filtered[end_date], errors='coerce')
    df_filtered['past_val'] = pd.to_numeric(df_filtered[start_date], errors='coerce')
    
    df_filtered = df_filtered.dropna(subset=['latest_val', 'past_val'])
    df_filtered = df_filtered.drop_duplicates(subset=['clean_region'], keep='first')
    
    # 상승률 계산
    df_filtered['상승률'] = ((df_filtered['latest_val'] - df_filtered['past_val']) / df_filtered['past_val']) * 100
    df_result = df_filtered.dropna(subset=['상승률']).sort_values(by='상승률', ascending=False)
    
    date_columns = [col for col in df.columns if col not in ['지역명', 'clean_region'] and not str(col).startswith('Unnamed')]
    
    start_idx = date_columns.index(start_date)
    end_idx = date_columns.index(end_date)
    # in case dates were flipped
    if start_idx > end_idx:
        start_idx, end_idx = end_idx, start_idx
        
    selected_dates = date_columns[start_idx:end_idx+1]
    
    trend_df = df_filtered.set_index('지역명')[selected_dates].T
    
    return df_result, trend_df

# -----------------------------------------------------------------------------
# 4. 대시보드 UI (PRO 버전)
# -----------------------------------------------------------------------------
def main():
    st.title("📈 PRO 부동산 매매가격지수 분석 대시보드")
    st.markdown("사용자 맞춤형 기간 설정 및 시계열 데이터 시각화 분석 도구입니다. 🔍 기능을 활용하여 원하는 인사이트를 도출해보세요.")
    
    df = load_data()
    
    date_columns = [col for col in df.columns if col not in ['지역명', 'clean_region'] and not str(col).startswith('Unnamed')]

    # --- 사이드바 설정 ---
    with st.sidebar:
        st.header("⚙️ 분석 조건 설정")
        
        region_type = st.selectbox(
            "📍 분석할 지역 그룹을 선택하세요", 
            ("서울 25개 자치구", "경기도 주요 시·군", "전국 주요 광역시/도")
        )
        
        st.markdown("---")
        st.subheader("📅 변동 기간 설정")
        if len(date_columns) < 2:
            st.error("데이터에 분석 가능한 날짜 컬럼이 부족합니다.")
            st.stop()
            
        start_date, end_date = st.select_slider(
            "비교 시작 월과 종료 월 드래그",
            options=date_columns,
            value=(date_columns[-13] if len(date_columns) >= 13 else date_columns[0], date_columns[-1]) 
        )
    
    # 시작일과 종료일이 같을 경우
    if start_date == end_date:
        st.warning("⚠️ 시작 월과 종료 월이 동일합니다. 비교를 위해 서로 다른 기간을 선택해주세요.")
        return

    # 날짜 순서 보정
    s_idx, e_idx = date_columns.index(start_date), date_columns.index(end_date)
    if s_idx > e_idx:
        start_date, end_date = end_date, start_date

    # --- 지역 그룹별 타겟 리스트 ---
    is_exact = False
    if region_type == "서울 25개 자치구":
        target_list = ['종로구', '중구', '용산구', '성동구', '광진구', '동대문구', '중랑구', '성북구', '강북구', '도봉구', '노원구', '은평구', '서대문구', '마포구', '양천구', '강서구', '구로구', '금천구', '영등포구', '동작구', '관악구', '서초구', '강남구', '송파구', '강동구']
    elif region_type == "경기도 주요 시·군":
        target_list = ['수원시', '성남시', '의정부시', '안양시', '부천시', '광명시', '평택시', '동두천시', '안산시', '고양시', '과천시', '구리시', '남양주시', '오산시', '시흥시', '군포시', '의왕시', '하남시', '용인시', '파주시', '이천시', '안성시', '김포시', '화성시', '광주시', '양주시', '포천시', '여주시', '연천군', '가평군', '양평군']
        is_exact = True 
    else:
        target_list = ['전국', '서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종']
        is_exact = True

    # --- 데이터 연산 ---
    with st.spinner("데이터 분석 중..."):
        result_df, trend_df = process_growth_data_pro(df, target_list, start_date, end_date, is_exact_match=is_exact)
    
    if result_df.empty:
        st.warning("선택하신 조건에 해당하는 데이터가 없습니다.")
        return

    # 탭 구성: 메인 대시보드 / 상세 데이터
    tab1, tab2 = st.tabs(["📊 대시보드", "📝 상세 데이터"])

    with tab1:
        # --- 🌟 1. 최상단 핵심 요약 지표 (KPI Cards) ---
        st.markdown("### 💡 핵심 요약 지표")
        
        top_region = result_df.iloc[0]
        worst_region = result_df.iloc[-1]
        avg_growth = result_df['상승률'].mean()
        
        up_count = len(result_df[result_df['상승률'] > 0])
        down_count = len(result_df[result_df['상승률'] < 0])
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(label="🏆 최고 상승 지역", value=top_region['지역명'], delta=f"{top_region['상승률']:.2f}%")
        with col2:
            st.metric(label="📉 최저 하락 지역", value=worst_region['지역명'], delta=f"{worst_region['상승률']:.2f}%", delta_color="inverse")
        with col3:
            st.metric(label="📈 상승 vs 하락", value=f"{up_count} 상승 / {down_count} 하락", delta=f"평균 {avg_growth:.2f}% 변동", delta_color="normal" if avg_growth > 0 else "inverse")
        with col4:
            st.metric(label="🗓️ 분석 기간", value=f"{start_date}", delta=f"~ {end_date}", delta_color="off")
            
        st.divider()

        # --- 🌟 2. 랭킹 차트 ---
        st.markdown(f"### 🏅 지역별 상승률 랭킹 TOP 10 ({start_date} ~ {end_date})")
        
        top_n = min(10, len(result_df))
        top10_df = result_df.head(top_n)
        
        # Interactive chart with Altair
        base = alt.Chart(top10_df).encode(
            x=alt.X('상승률:Q', title='변동률 (%)'),
            y=alt.Y('지역명:N', sort='-x', title=''),
            color=alt.condition(
                alt.datum.상승률 > 0,
                alt.value('#ef4444'),  # red for positive in real estate
                alt.value('#3b82f6')   # blue for negative
            ),
            tooltip=['지역명', alt.Tooltip('상승률:Q', format='.2f')]
        )
        
        bars = base.mark_bar(cornerRadiusEnd=4)
        text = base.mark_text(
            align='left',
            baseline='middle',
            dx=3, # Nudges text to right
        ).encode(
            text=alt.Text('상승률:Q', format='.2f')
        ).transform_filter(
            alt.datum.상승률 > 0
        )
        
        text_neg = base.mark_text(
            align='right',
            baseline='middle',
            dx=-3, # Nudges text to left
        ).encode(
            text=alt.Text('상승률:Q', format='.2f')
        ).transform_filter(
            alt.datum.상승률 <= 0
        )
        
        chart = (bars + text + text_neg).properties(height=400).configure_axis(
            grid=False,
            labelFontSize=12,
            titleFontSize=14
        ).interactive()
        
        st.altair_chart(chart, use_container_width=True)

        st.divider()

        # --- 🌟 3. 반응형 시계열 추이 차트 ---
        st.markdown("### 📈 주도 지역 시계열 추이 분석 (TOP 5)")
        st.caption("👈 범례를 클릭하거나 그래프 영역을 드래그하여 상세하게 분석해보세요.")
        
        top5_regions = top10_df['지역명'].head(5).tolist()
        
        st.line_chart(trend_df[top5_regions], height=400, use_container_width=True)

    with tab2:
        st.markdown(f"### 📝 전체 지역 데이터 ({start_date} ~ {end_date})")
        st.caption("표의 열을 클릭하여 정렬하거나, 아래 버튼을 눌러 엑셀(CSV) 형식으로 저장할 수 있습니다.")
        
        display_df = result_df[['지역명', 'past_val', 'latest_val', '상승률']].copy()
        display_df.rename(columns={
            'past_val': f'{start_date} 지수',
            'latest_val': f'{end_date} 지수',
            '상승률': '변동률(%)'
        }, inplace=True)
        
        st.dataframe(
            display_df.style.format({
                f'{start_date} 지수': '{:,.1f}',
                f'{end_date} 지수': '{:,.1f}',
                '변동률(%)': '{:+.2f}%'
            }).background_gradient(cmap='vlag', subset=['변동률(%)']), 
            use_container_width=True, 
            height=500
        )
        
        csv = display_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 CSV 파일 다운로드",
            data=csv,
            file_name=f'real_estate_analysis_{start_date}_to_{end_date}.csv',
            mime='text/csv',
        )

if __name__ == '__main__':
    main()