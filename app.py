import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정
# -----------------------------------------------------------------------------
st.set_page_config(page_title="2026 부동산 매매지수 대시보드", page_icon="🏢", layout="wide")

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False
sns.set_theme(style="whitegrid", font="Malgun Gothic", font_scale=1)

# -----------------------------------------------------------------------------
# 2. 데이터 로드
# -----------------------------------------------------------------------------
@st.cache_data
def load_data():
    """엑셀(또는 CSV) 파일을 읽고 무조건 첫 컬럼을 '지역명'으로 맞춥니다."""
    file_path = 'data/apt_price_20260408.xlsx' 
    
    try:
        # 파일 형식에 따라 유연하게 대처 (csv로 저장하셨다면 read_csv로 읽습니다)
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path, header=0) # 엑셀 구조에 맞게 header=0 또는 10으로 조절
    except FileNotFoundError:
        st.error(f"데이터 파일을 찾을 수 없습니다: {file_path}")
        st.stop()
        
    first_col = df.columns[0]
    df.rename(columns={first_col: '지역명'}, inplace=True)
    return df

# -----------------------------------------------------------------------------
# 3. [핵심] 철통 방어 데이터 전처리 함수
# -----------------------------------------------------------------------------
@st.cache_data
def process_growth_data(df, target_regions, is_exact_match=False):
    """쓰레기 값, 병합 셀, 띄어쓰기를 완벽하게 걸러내고 상승률을 계산합니다."""
    
    # 1. 지역명에 숨어있는 모든 띄어쓰기 완전 제거 (안전성 100%)
    df['clean_region'] = df['지역명'].astype(str).str.replace(r'\s+', '', regex=True)
    clean_targets = [str(x).replace(' ', '') for x in target_regions]
    
    # 2. 필터링 (정확히 일치 vs 포함)
    if is_exact_match:
        df_filtered = df[df['clean_region'].isin(clean_targets)].copy()
    else:
        pattern = '|'.join(clean_targets)
        df_filtered = df[df['clean_region'].str.contains(pattern, na=False)].copy()
        
    # 3. 날짜 컬럼만 정확히 추출 ('Unnamed' 같은 유령 열 차단!)
    date_columns = [col for col in df.columns if col not in ['지역명', 'clean_region'] and not str(col).startswith('Unnamed')]
    latest_col = date_columns[-1]
    past_col = date_columns[-13]

    # 4. 숫자 변환
    df_filtered['latest_val'] = pd.to_numeric(df_filtered[latest_col], errors='coerce')
    df_filtered['past_val'] = pd.to_numeric(df_filtered[past_col], errors='coerce')
    
    # 5. [버그 해결] 데이터가 NaN인 텅 빈 줄(엑셀 병합셀 흔적) 먼저 삭제!
    df_filtered = df_filtered.dropna(subset=['latest_val', 'past_val'])
    
    # 6. 그 다음에 중복 제거 (진짜 데이터가 있는 유효한 첫 줄만 남음)
    df_filtered = df_filtered.drop_duplicates(subset=['clean_region'], keep='first')
    
    # 7. 상승률 계산 및 정렬
    df_filtered['상승률'] = ((df_filtered['latest_val'] - df_filtered['past_val']) / df_filtered['past_val']) * 100
    df_result = df_filtered.dropna(subset=['상승률']).sort_values(by='상승률', ascending=False)
    
    # 화면 출력을 위해 깔끔한 이름 덮어쓰기
    df_result['지역명'] = df_result['clean_region']
    
    return df_result, latest_col, past_col

# -----------------------------------------------------------------------------
# 4. 대시보드 UI
# -----------------------------------------------------------------------------
def main():
    st.title("📊 2026 부동산 매매지수 대시보드")
    st.markdown("최근 1년간 아파트 매매가격 상승률을 분석하고 시각화합니다.")
    st.divider()

    df = load_data()

    with st.sidebar:
        st.header("⚙️ 분석 설정")
        # '경기도 자치구' -> '경기도 시·군'으로 이름 변경
        region_type = st.radio("분석할 지역 단위를 선택하세요", ("서울 자치구 (TOP 10)", "경기도 시·군 (TOP 10)", "전국 주요 도시 비교"))
        st.markdown("---")
        st.info("💡 **안내:** 엑셀 데이터의 가장 최근 월을 기준으로 지난 1년간의 상승률을 계산합니다.")

    if region_type == "서울 자치구 (TOP 10)":
        st.subheader("🏙️ 서울 25개 자치구 최근 1년 상승률 TOP 10")
        seoul_gu_list = ['종로구', '중구', '용산구', '성동구', '광진구', '동대문구', '중랑구', '성북구', '강북구', '도봉구', '노원구', '은평구', '서대문구', '마포구', '양천구', '강서구', '구로구', '금천구', '영등포구', '동작구', '관악구', '서초구', '강남구', '송파구', '강동구']
        
        result_df, latest_col, past_col = process_growth_data(df, seoul_gu_list, is_exact_match=False)
        top10_df = result_df.head(10)
        
        st.caption(f"분석 기간: {past_col} ~ {latest_col}")
        col1, col2 = st.columns([2, 1])
        with col1:
            fig, ax = plt.subplots(figsize=(10, 6))
            sns.barplot(data=top10_df, x='상승률', y='지역명', hue='지역명', palette='vlag_r', legend=False, ax=ax)
            ax.set_xlabel('상승률 (%)')
            ax.set_ylabel('')
            for p in ax.patches:
                width = p.get_width()
                ax.text(width + 0.3, p.get_y() + p.get_height()/2, f"{width:.2f}%", ha='left', va='center')
            st.pyplot(fig)
        with col2:
            st.dataframe(top10_df[['지역명', '상승률']].style.format({'상승률': '{:.2f}%'}), use_container_width=True)

    elif region_type == "경기도 시·군 (TOP 10)":
        st.subheader("🏘️ 경기도 최근 1년 상승률 TOP 10 (시·군 단위)")
        
        # 🌟 핵심 버그 픽스: '구' 단위를 원천 차단하고 31개 시/군만 정확하게 리스트업!
        gyeonggi_cities = [
            '수원시', '성남시', '의정부시', '안양시', '부천시', '광명시', '평택시', '동두천시', '안산시', '고양시', 
            '과천시', '구리시', '남양주시', '오산시', '시흥시', '군포시', '의왕시', '하남시', '용인시', '파주시', 
            '이천시', '안성시', '김포시', '화성시', '광주시', '양주시', '포천시', '여주시', '연천군', '가평군', '양평군'
        ]
        
        # is_exact_match=True 로 설정! 
        # 이제 '성남시'만 가져오고 '성남시 분당구'는 이름이 다르므로 무시합니다.
        result_df, latest_col, past_col = process_growth_data(df, gyeonggi_cities, is_exact_match=True)
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
            
            fig.tight_layout()
            st.pyplot(fig)
        with col2:
             st.dataframe(top10_df[['지역명', '상승률']].style.format({'상승률': '{:.2f}%'}), use_container_width=True)

    elif region_type == "전국 주요 도시 비교":
        st.subheader("🗺️ 전국 주요 도시 1년 전 대비 변동률")
        major_cities = ['전국', '서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종']
        
        # 🌟 루프 삭제! 한 번의 호출로 깔끔하고 정확하게 가져옵니다.
        result_df, latest_col, past_col = process_growth_data(df, major_cities, is_exact_match=True)
        
        if not result_df.empty:
            st.caption(f"분석 기간: {past_col} ~ {latest_col}")
            fig, ax = plt.subplots(figsize=(12, 6))
            
            colors = ['#d62728' if x > 0 else '#1f77b4' for x in result_df['상승률']]
            sns.barplot(data=result_df, x='지역명', y='상승률', hue='지역명', palette=colors, legend=False, ax=ax)
            
            ax.set_ylabel('상승률 (%)')
            ax.set_xlabel('')
            
            # X축 라벨 겹침 방지 설정
            ax.axhline(0, color='black', linewidth=1.5)
            ax.spines['bottom'].set_position(('axes', 0))
            
            for p in ax.patches:
                height = p.get_height()
                y_pos = height + 0.5 if height > 0 else height - 0.5
                ax.text(p.get_x() + p.get_width()/2., y_pos, f'{height:.1f}%', ha='center', va='bottom' if height > 0 else 'top')

            st.pyplot(fig)
        else:
             st.error("해당 조건에 맞는 데이터가 없습니다.")

if __name__ == '__main__':
    main()