import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정 (와이드 모드)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="PRO 부동산 매매지수 대시보드", page_icon="📈", layout="wide")

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False
sns.set_theme(style="whitegrid", font="Malgun Gothic", font_scale=1)

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
        st.error(f"데이터 파일을 찾을 수 없습니다: {file_path}")
        st.stop()
        
    first_col = df.columns[0]
    df.rename(columns={first_col: '지역명'}, inplace=True)
    return df

# -----------------------------------------------------------------------------
# 3. 데이터 전처리 함수 (시작/종료 날짜 동적 반영)
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
        
    # 날짜 컬럼 추출 (사이드바에서 선택한 날짜 활용)
    df_filtered['latest_val'] = pd.to_numeric(df_filtered[end_date], errors='coerce')
    df_filtered['past_val'] = pd.to_numeric(df_filtered[start_date], errors='coerce')
    
    df_filtered = df_filtered.dropna(subset=['latest_val', 'past_val'])
    df_filtered = df_filtered.drop_duplicates(subset=['clean_region'], keep='first')
    
    # 상승률 계산
    df_filtered['상승률'] = ((df_filtered['latest_val'] - df_filtered['past_val']) / df_filtered['past_val']) * 100
    df_result = df_filtered.dropna(subset=['상승률']).sort_values(by='상승률', ascending=False)
    
    # 시계열 그래프용 데이터 (날짜를 행으로, 지역명을 열로 변환)
    date_columns = [col for col in df.columns if col not in ['지역명', 'clean_region'] and not str(col).startswith('Unnamed')]
    
    # 선택된 기간 사이의 컬럼만 필터링
    start_idx = date_columns.index(start_date)
    end_idx = date_columns.index(end_date)
    selected_dates = date_columns[start_idx:end_idx+1]
    
    trend_df = df_filtered.set_index('지역명')[selected_dates].T
    
    return df_result, trend_df

# -----------------------------------------------------------------------------
# 4. 대시보드 UI (PRO 버전)
# -----------------------------------------------------------------------------
def main():
    st.title("📈 PRO 부동산 매매가격지수 분석 대시보드")
    st.markdown("사용자 맞춤형 기간 설정 및 시계열 추이 분석 도구입니다.")
    
    df = load_data()
    
    # 전체 날짜 리스트 추출 (슬라이더용)
    date_columns = [col for col in df.columns if col not in ['지역명', 'clean_region'] and not str(col).startswith('Unnamed')]

    # --- 사이드바 설정 ---
    with st.sidebar:
        st.header("⚙️ 분석 설정")
        
        region_type = st.selectbox(
            "📍 분석할 지역 그룹", 
            ("서울 25개 자치구", "경기도 주요 시·군", "전국 주요 광역시/도")
        )
        
        st.markdown("---")
        st.subheader("📅 기간 설정")
        # 🌟 동적 기간 슬라이더 추가!
        start_date, end_date = st.select_slider(
            "비교할 시작 월과 종료 월을 선택하세요",
            options=date_columns,
            value=(date_columns[-13], date_columns[-1]) # 기본값: 최근 1년
        )
    
    # --- 지역 그룹별 타겟 리스트 ---
    is_exact = False
    if region_type == "서울 25개 자치구":
        target_list = ['종로구', '중구', '용산구', '성동구', '광진구', '동대문구', '중랑구', '성북구', '강북구', '도봉구', '노원구', '은평구', '서대문구', '마포구', '양천구', '강서구', '구로구', '금천구', '영등포구', '동작구', '관악구', '서초구', '강남구', '송파구', '강동구']
    elif region_type == "경기도 주요 시·군":
        target_list = ['수원시', '성남시', '의정부시', '안양시', '부천시', '광명시', '평택시', '동두천시', '안산시', '고양시', '과천시', '구리시', '남양주시', '오산시', '시흥시', '군포시', '의왕시', '하남시', '용인시', '파주시', '이천시', '안성시', '김포시', '화성시', '광주시', '양주시', '포천시', '여주시', '연천군', '가평군', '양평군']
        is_exact = True # 시 단위 정확히 매칭 (구 제외)
    else:
        target_list = ['전국', '서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종']
        is_exact = True

    # --- 데이터 연산 ---
    result_df, trend_df = process_growth_data_pro(df, target_list, start_date, end_date, is_exact_match=is_exact)
    
    if result_df.empty:
        st.warning("선택하신 조건에 해당하는 데이터가 없습니다.")
        return

    # --- 🌟 1. 최상단 핵심 요약 지표 (KPI Cards) ---
    st.markdown("### 💡 요약 지표")
    kpi1, kpi2, kpi3 = st.columns(3)
    
    top_region = result_df.iloc[0]
    avg_growth = result_df['상승률'].mean()
    worst_region = result_df.iloc[-1]
    
    kpi1.metric(label="🏆 최고 상승 지역", value=top_region['지역명'], delta=f"{top_region['상승률']:.2f}%")
    kpi2.metric(label="📊 평균 상승률", value=f"{avg_growth:.2f}%", delta=None)
    kpi3.metric(label="📉 최저/하락 지역", value=worst_region['지역명'], delta=f"{worst_region['상승률']:.2f}%", delta_color="inverse")
    
    st.divider()

    # --- 🌟 2. 랭킹 차트 & 데이터 표 ---
    st.markdown(f"### 🏅 지역별 상승률 랭킹 ({start_date} ~ {end_date})")
    
    # 상위 10개만 추출 (전국 등 10개가 안되는 경우도 처리)
    top_n = min(10, len(result_df))
    top10_df = result_df.head(top_n)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        fig, ax = plt.subplots(figsize=(10, 6))
        # 상승/하락에 따라 색상 자동 변경
        colors = ['#d62728' if x > 0 else '#1f77b4' for x in top10_df['상승률']]
        
        sns.barplot(data=top10_df, x='상승률', y='지역명', hue='지역명', palette=colors, legend=False, ax=ax)
        ax.set_xlabel('변동률 (%)', fontsize=12)
        ax.set_ylabel('')
        
        ax.axhline(0, color='black', linewidth=1.5)
        ax.spines['bottom'].set_position(('axes', 0))
        
        for p in ax.patches:
            width = p.get_width()
            x_pos = width + 0.3 if width > 0 else width - 0.5
            ha_align = 'left' if width > 0 else 'right'
            ax.text(x_pos, p.get_y() + p.get_height()/2, f"{width:.2f}%", ha=ha_align, va='center', fontweight='bold')
        
        fig.tight_layout()
        st.pyplot(fig)
        
    with col2:
        st.dataframe(result_df[['지역명', '상승률']].style.format({'상승률': '{:.2f}%'}), height=400, use_container_width=True)

    st.divider()

    # --- 🌟 3. 반응형 시계열 추이 차트 ---
    st.markdown("### 📈 주도 지역 시계열 추이 분석 (TOP 5)")
    st.caption("그래프에 마우스를 올리면 정확한 지수 수치를 확인할 수 있습니다. 드래그하여 확대/축소도 가능합니다.")
    
    # 상위 5개 지역의 이름만 추출
    top5_regions = top10_df['지역명'].head(5).tolist()
    
    # Streamlit 내장 반응형 라인 차트 사용 (Plotly 기반이라 예쁘고 인터랙티브함)
    st.line_chart(trend_df[top5_regions], height=400)

if __name__ == '__main__':
    main()