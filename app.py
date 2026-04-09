import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="2026 부동산 매매지수 대시보드",
    page_icon="🏢",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 2. 한글 폰트 및 시각화 설정
# -----------------------------------------------------------------------------
plt.rcParams['font.family'] = 'Malgun Gothic' # 윈도우 폰트 (맥은 'AppleGothic'으로 변경)
plt.rcParams['axes.unicode_minus'] = False
sns.set_theme(style="whitegrid", font="Malgun Gothic", font_scale=1) # seaborn 스타일 통합 적용

# -----------------------------------------------------------------------------
# 3. 데이터 로드 및 전처리 함수 (캐싱 적용)
# -----------------------------------------------------------------------------
@st.cache_data
@st.cache_data
def load_data():
    """엑셀 파일을 읽고 필요한 기본 전처리를 수행합니다."""
    file_path = 'data/apt_price_20260408.xlsx' 
    
    try:
        # 💡 포인트 1: header=10을 0으로 바꿔보거나, 파일에 맞게 조절해야 할 수 있습니다.
        # 일단 가장 일반적인 header=10으로 두되, 안 맞으면 화면을 보고 고칠 겁니다.
        df = pd.read_excel(file_path, header=10)
    except FileNotFoundError:
        st.error(f"데이터 파일을 찾을 수 없습니다: {file_path}")
        st.stop()
        
    # 💡 포인트 2: 무조건 첫 번째 컬럼(인덱스 0)을 '지역명'으로 강제 변경합니다.
    first_column_name = df.columns[0]
    df.rename(columns={first_column_name: '지역명'}, inplace=True)

    # 🌟 [추가된 코드] 지역명 앞뒤에 숨은 띄어쓰기(공백)를 모두 제거하여 깨끗하게 만듭니다.
    df['지역명'] = df['지역명'].astype(str).str.strip()
    
    return df

@st.cache_data
def process_growth_data(df, target_regions, title_keyword):
    """특정 지역 리스트를 받아 최근 1년간의 상승률을 계산합니다."""
    # 1. 지역 필터링 및 중복 제거
    df_filtered = df[df['지역명'].str.contains('|'.join(target_regions), na=False)].copy()
    
    # "전국, 서울, 경기" 같은 단일 키워드 검색 시, '구'나 '시' 단위가 아니면 정확히 일치하는 것만 찾기
    if len(target_regions) == 1 and not target_regions[0].endswith(('구', '시', '군')):
        df_filtered = df[df['지역명'] == target_regions[0]].copy()
        
    df_filtered = df_filtered.drop_duplicates(subset=['지역명'], keep='first')
    
    # 2. 날짜 컬럼 추출 및 1년 전후 데이터 선택
    date_columns = [col for col in df.columns if col != '지역명']
    latest_col = date_columns[-1]
    past_col = date_columns[-13]

    # 3. 상승률 계산
    latest_p = pd.to_numeric(df_filtered[latest_col], errors='coerce')
    past_p = pd.to_numeric(df_filtered[past_col], errors='coerce')
    df_filtered['상승률'] = ((latest_p - past_p) / past_p) * 100
    
    # 4. 상위 지역 정렬 (결측치 제외)
    df_result = df_filtered.dropna(subset=['상승률']).sort_values(by='상승률', ascending=False)
    
    return df_result, latest_col, past_col

# -----------------------------------------------------------------------------
# 4. 대시보드 UI 및 로직 구현
# -----------------------------------------------------------------------------
def main():
    # --- 타이틀 영역 ---
    st.title("📊 2026 부동산 매매지수 대시보드")
    st.markdown("최근 1년간 아파트 매매가격 상승률을 분석하고 시각화합니다.")
    st.divider()

    # --- 데이터 로드 ---
    df = load_data()

    # 🚨 [디버깅용 화면 출력] 파이썬이 읽어들인 표의 상위 3줄을 대시보드에 그대로 보여줍니다.
    # st.warning("🔍 [데이터 확인용] 첫 번째 컬럼이 정상적으로 '지역명'으로 바뀌었는지, 아래 표를 확인해주세요!")
    # st.dataframe(df.head(3))

    # --- 사이드바 영역 (필터 컨트롤) ---
    with st.sidebar:
        st.header("⚙️ 분석 설정")
        
        # 1. 지역 대분류 선택
        region_type = st.radio(
            "분석할 지역 단위를 선택하세요",
            ("서울 자치구 (TOP 10)", "경기도 자치구 (TOP 10)", "전국 주요 도시 비교")
        )
        
        st.markdown("---")
        st.info("💡 **안내:** 엑셀 데이터의 가장 최근 월을 기준으로 지난 1년간의 상승률을 계산합니다.")

    # --- 메인 영역 (차트 및 데이터 출력) ---
    
    if region_type == "서울 자치구 (TOP 10)":
        st.subheader("🏙️ 서울 25개 자치구 최근 1년 상승률 TOP 10")
        
        # 서울 자치구 리스트
        seoul_gu_list = [
            '종로구', '중구', '용산구', '성동구', '광진구', '동대문구', '중랑구', '성북구', '강북구', '도봉구',
            '노원구', '은평구', '서대문구', '마포구', '양천구', '강서구', '구로구', '금천구', '영등포구', '동작구',
            '관악구', '서초구', '강남구', '송파구', '강동구'
        ]
        
        # 데이터 처리
        result_df, latest_col, past_col = process_growth_data(df, seoul_gu_list, "서울")
        top10_df = result_df.head(10)
        
        st.caption(f"분석 기간: {past_col} ~ {latest_col}")
        
        # 그래프 그리기 (Streamlit 컬럼 레이아웃 활용)
        col1, col2 = st.columns([2, 1]) # 그래프를 2, 데이터를 1 비율로 배치
        
        with col1:
            fig, ax = plt.subplots(figsize=(10, 6))
            sns.barplot(data=top10_df, x='상승률', y='지역명', hue='지역명', palette='vlag_r', legend=False, ax=ax)
            ax.set_xlabel('상승률 (%)')
            ax.set_ylabel('')
            
            # 수치 표시
            for p in ax.patches:
                width = p.get_width()
                ax.text(width + 0.3, p.get_y() + p.get_height()/2, f"{width:.2f}%", ha='left', va='center')
                
            st.pyplot(fig) # Streamlit에 Matplotlib 차트 표시
            
        with col2:
            st.dataframe(top10_df[['지역명', '상승률']].style.format({'상승률': '{:.2f}%'}), use_container_width=True)

    elif region_type == "경기도 자치구 (TOP 10)":
        st.subheader("🏘️ 경기도 최근 1년 상승률 TOP 10")
        
        # 경기도 키워드
        gyeonggi_keywords = ['수원', '성남', '의정부', '안양', '부천', '광명', '평택', '동두천', '안산', '고양', 
                             '과천', '구리', '남양주', '오산', '시흥', '군포', '의왕', '하남', '용인', '파주', 
                             '이천', '안성', '김포', '화성', '광주', '양주', '포천', '여주', '연천', '가평', '양평']
        
        result_df, latest_col, past_col = process_growth_data(df, gyeonggi_keywords, "경기")
        top10_df = result_df.head(10)
        
        st.caption(f"분석 기간: {past_col} ~ {latest_col}")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            fig, ax = plt.subplots(figsize=(10, 6))
            sns.barplot(data=top10_df, x='상승률', y='지역명', hue='지역명', palette='viridis', legend=False, ax=ax)
            ax.set_xlabel('상승률 (%)')
            ax.set_ylabel('')
            
            for p in ax.patches:
                width = p.get_width()
                ax.text(width + 0.3, p.get_y() + p.get_height()/2, f"{width:.2f}%", ha='left', va='center')
                
            st.pyplot(fig)
            
        with col2:
             st.dataframe(top10_df[['지역명', '상승률']].style.format({'상승률': '{:.2f}%'}), use_container_width=True)

    elif region_type == "전국 주요 도시 비교":
        st.subheader("🗺️ 전국 주요 도시 1년 전 대비 변동률")
        
        major_cities = ['전국', '서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종']
        
        # 🌟 [핵심 버그 픽스] '해운대구' 방지! 정확히 이름이 일치하는 도시만 골라옵니다.
        df_filtered = df[df['지역명'].isin(major_cities)].copy()
        df_filtered = df_filtered.drop_duplicates(subset=['지역명'], keep='first')
        
        if not df_filtered.empty:
            # 날짜 컬럼 및 상승률 계산
            date_columns = [col for col in df.columns if col != '지역명']
            latest_col = date_columns[-1]
            past_col = date_columns[-13]
            
            latest_p = pd.to_numeric(df_filtered[latest_col], errors='coerce')
            past_p = pd.to_numeric(df_filtered[past_col], errors='coerce')
            df_filtered['상승률'] = ((latest_p - past_p) / past_p) * 100
            
            # 결과 정렬
            result_df = df_filtered.dropna(subset=['상승률']).sort_values(by='상승률', ascending=False)
            st.caption(f"분석 기간: {past_col} ~ {latest_col}")
            
            # 차트 그리기
            fig, ax = plt.subplots(figsize=(12, 6))
            colors = ['#d62728' if x > 0 else '#1f77b4' for x in result_df['상승률']]
            
            sns.barplot(data=result_df, x='지역명', y='상승률', hue='지역명', palette=colors, legend=False, ax=ax)
            ax.set_ylabel('상승률 (%)')
            ax.set_xlabel('')
            
            # X축 라벨 겹침 방지 (0선 기준선 그리기)
            ax.axhline(0, color='black', linewidth=1.5)
            ax.spines['bottom'].set_position(('axes', 0))
            
            # 수치 표시
            for p in ax.patches:
                height = p.get_height()
                y_pos = height + 0.5 if height > 0 else height - 0.5
                ax.text(p.get_x() + p.get_width()/2., y_pos, f'{height:.1f}%', ha='center', va='bottom' if height > 0 else 'top')

            st.pyplot(fig)
        else:
             st.error("데이터를 불러오는 중 오류가 발생했습니다.")

if __name__ == '__main__':
    main()