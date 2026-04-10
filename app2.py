import streamlit as st
import pandas as pd
import altair as alt

# 페이지 설정
st.set_page_config(page_title="부동산 매매지수 종합 대시보드", page_icon="🏢", layout="wide", initial_sidebar_state="expanded")

# 데이터 로드 및 전처리 (캐싱)
@st.cache_data
def load_and_preprocess_data():
    file_path = 'data/apt_price_20260408.xlsx'
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path, header=0)
    except Exception as e:
        st.error(f"⚠️ 데이터 파일 로드 실패: {e}")
        st.stop()
        
    first_col = df.columns[0]
    df.rename(columns={first_col: '지역명'}, inplace=True)
    df['지역명'] = df['지역명'].astype(str).str.strip()
    
    # 노트북 방식 적용: 가로형(Wide)을 세로형(Long Format)으로 변환
    date_cols = [col for col in df.columns if col != '지역명' and not str(col).startswith('Unnamed')]
    
    df_long = pd.melt(
        df, 
        id_vars=['지역명'], 
        var_name='날짜', 
        value_name='매매가격지수',
        value_vars=date_cols
    )
    
    # 날짜 타입 변환
    df_long['날짜_dt'] = pd.to_datetime(df_long['날짜'], errors='coerce')
    df_long['매매가격지수'] = pd.to_numeric(df_long['매매가격지수'], errors='coerce')
    
    # 결측치 제거
    df_long = df_long.dropna(subset=['날짜_dt', '매매가격지수'])
    # 날짜 포맷팅
    df_long['연월'] = df_long['날짜_dt'].dt.strftime('%Y-%m')
    
    return df, df_long, date_cols

# 데이터 불러오기
df_original, df_long, date_cols = load_and_preprocess_data()
unique_regions = sorted(df_original['지역명'].unique().tolist())
formatted_dates = sorted(df_long['연월'].unique().tolist())

# --- 1. 종합 시장 사이드바 메뉴 ---
st.sidebar.title("🏢 대시보드 메뉴")
st.sidebar.markdown("""
> **모바일 사용자 팁📱**
> 화면 좌측 상단의 햄버거 메뉴(`>`)를 터치하여 언제든 이 사이드바 메뉴를 열고 닫을 수 있습니다. 해당 방식이 모바일 환경에서 가장 최적화되고 추천되는 방식입니다.
""")

menu_options = [
    "🌐 종합 시장 동향 분석", 
    "🔍 맞춤형 관심 지역 분석", 
    "🏅 기간별 변동률 랭킹 분석", 
    "📊 원본 데이터 탐색"
]
selected_menu = st.sidebar.radio("원하시는 분석 메뉴를 선택하세요", menu_options)

st.sidebar.divider()
st.sidebar.info("💡 **제공 데이터**: 기준일 2026.04.08 아파트 매매가격지수 (한국부동산원)")


# --- Helper Function for KPI ---
def calculate_growth(df_subset, start_ym, end_ym):
    start_val = df_subset[df_subset['연월'] == start_ym]['매매가격지수'].values
    end_val = df_subset[df_subset['연월'] == end_ym]['매매가격지수'].values
    
    if len(start_val) == 0 or len(end_val) == 0:
        return None, None, None
    
    sv, ev = start_val[0], end_val[-1]
    growth_rate = ((ev - sv) / sv) * 100
    return sv, ev, growth_rate

# --- 페이지 라우팅 로직 ---

if selected_menu == "🌐 종합 시장 동향 분석":
    st.title("🌐 종합 시장 동향 분석")
    st.markdown("거시적인 관점에서 대한민국을 대표하는 핵심 권역의 시장 흐름을 파악해보세요. 차트를 드래그하여 확대할 수 있습니다.")
    st.divider()
    
    macro_targets = ['전국', '서울', '강북14개구', '강남11개구']
    available_targets = [r for r in macro_targets if r in unique_regions]
    
    if not available_targets:
        available_targets = unique_regions[:4]
        
    macro_df = df_long[df_long['지역명'].isin(available_targets)]
    
    # 차트
    st.markdown("### 📈 핵심 권역 매매가격지수 장기 추이")
    
    macro_chart = alt.Chart(macro_df).mark_line(size=3).encode(
        x=alt.X('연월:T', title='연-월', axis=alt.Axis(format='%Y-%m', grid=False, tickCount='year')),
        y=alt.Y('매매가격지수:Q', scale=alt.Scale(zero=False), title='매매가격지수'),
        color=alt.Color('지역명:N', legend=alt.Legend(title="지역구분", orient="top")),
        tooltip=['연월:T', '지역명:N', alt.Tooltip('매매가격지수:Q', format='.2f')]
    ).properties(height=450)
    
    st.altair_chart(macro_chart, use_container_width=True)
    
    # KPI 요약 지표 섹션 (최근 1년 기준)
    recent_date = formatted_dates[-1]
    year_ago_idx = len(formatted_dates) - 13
    past_date = formatted_dates[year_ago_idx] if year_ago_idx >= 0 else formatted_dates[0]
    
    st.markdown(f"### 💡 최근 1년 동향 요약 (기준: {past_date} ~ {recent_date})")
    cols = st.columns(len(available_targets))
    
    for i, region in enumerate(available_targets):
        reg_df = macro_df[macro_df['지역명'] == region]
        sv, ev, rate = calculate_growth(reg_df, past_date, recent_date)
        if rate is not None:
            with cols[i]:
                st.metric(
                    label=f"🏢 {region}", 
                    value=f"{ev:.1f}p", 
                    delta=f"{rate:+.2f}% (최근 1년)", 
                    delta_color="normal" if rate > 0 else "inverse"
                )

elif selected_menu == "🔍 맞춤형 관심 지역 분석":
    st.title("🔍 맞춤형 관심 지역 심층 다중 비교")
    st.markdown("자신이 특별히 주목하는 지역(시군구 등)들을 여러 개 복수 선택해서 직접 비교해보세요.")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        selected_regions = st.multiselect(
            "📍 탐색할 지역들을 선택해주세요 (다중 선택 가능)", 
            unique_regions, 
            default=['종로구', '중구'] if '종로구' in unique_regions else unique_regions[:2]
        )
    with col2:
        if len(formatted_dates) > 1:
            start_m, end_m = st.select_slider(
                "📅 비교할 세부 기간 범위를 드래그 하세요", 
                options=formatted_dates, 
                value=(formatted_dates[-36] if len(formatted_dates) >= 36 else formatted_dates[0], formatted_dates[-1])
            )
        else:
            start_m, end_m = formatted_dates[0], formatted_dates[0]
            
    if not selected_regions:
        st.warning("👆 위에서 분석하실 관심 지역을 1개 이상 선택해주세요.")
    else:
        if start_m > end_m:
            start_m, end_m = end_m, start_m
            
        filtered_df = df_long[
            (df_long['지역명'].isin(selected_regions)) & 
            (df_long['연월'] >= start_m) & 
            (df_long['연월'] <= end_m)
        ]
        
        # 중복 데이터(예: 서울 '중구', 부산 '중구' 등 이름이 같은 지역)를 평균값으로 병합하여 지그재그 차트 방지
        plot_df = filtered_df.groupby(['연월', '지역명'])['매매가격지수'].mean().reset_index()
        
        st.divider()
        st.markdown(f"### 📈 선택 지역 비교 : {start_m} ~ {end_m}")
        
        custom_chart = alt.Chart(plot_df).mark_line(size=2.5, point=True).encode(
            x=alt.X('연월:T', title=''),
            y=alt.Y('매매가격지수:Q', scale=alt.Scale(zero=False)),
            color=alt.Color('지역명:N'),
            tooltip=['연월:T', '지역명:N', alt.Tooltip('매매가격지수:Q', format='.2f')]
        ).properties(height=450)
        
        st.altair_chart(custom_chart, use_container_width=True)

        with st.expander("📝 선택한 지역 시계열 데이터 표 확인 (클릭하여 열기)"):
            pivot_df = filtered_df.pivot_table(index='연월', columns='지역명', values='매매가격지수', aggfunc='mean')
            st.dataframe(
                pivot_df.style.highlight_max(axis=0, color='rgba(239, 68, 68, 0.4)')
                              .highlight_min(axis=0, color='rgba(59, 130, 246, 0.4)'), 
                use_container_width=True,
                height=400
            )

elif selected_menu == "🏅 기간별 변동률 랭킹 분석":
    st.title("🏅 주도 지역(급등) 및 침체 지역(급락) 랭킹")
    st.markdown("특정 기간 동안 지수가 **어디가 가장 많이 오르고 내렸는지 파악**하며 시장의 흐름을 주도하는 대장 지역을 발굴합니다.")
    
    st.info("기간 슬라이더를 잡고 과거로 이동해보세요. 랭킹이 즉시 재계산됩니다.")
    start_r, end_r = st.select_slider(
        "📅 랭킹을 산출할 두 시점(시작 월 ~ 종료 월)을 선택하세요", 
        options=formatted_dates, 
        value=(formatted_dates[-13] if len(formatted_dates) >= 13 else formatted_dates[0], formatted_dates[-1])
    )
    
    if start_r == end_r:
        st.warning("⚠️ 시작/종료 시점이 동일합니다. 변화율 계산을 위해서 서로 다른 월을 선택해주세요.")
    else:
        if start_r > end_r:
            start_r, end_r = end_r, start_r
            
        with st.spinner("🚀 대한민국 전체 지역 랭킹 실시간 계산 중..."):
            start_col, end_col = None, None
            for c in date_cols:
                if start_r in str(c): start_col = c
                if end_r in str(c): end_col = c
                
            if start_col is None or end_col is None:
                st.error("해당 날짜 포맷의 컬럼을 파일에서 찾을 수 없습니다.")
            else:
                calc_df = df_original[['지역명', start_col, end_col]].copy()
                calc_df[start_col] = pd.to_numeric(calc_df[start_col], errors='coerce')
                calc_df[end_col] = pd.to_numeric(calc_df[end_col], errors='coerce')
                calc_df = calc_df.dropna()
                
                calc_df['변동률(%)'] = ((calc_df[end_col] - calc_df[start_col]) / calc_df[start_col]) * 100
                calc_df = calc_df.sort_values('변동률(%)', ascending=False).reset_index(drop=True)
                
                st.divider()
                col_top, col_bot = st.columns(2)
                
                top10 = calc_df.head(10).copy()
                bot10 = calc_df.tail(10).sort_values('변동률(%)', ascending=True).copy() 
                
                with col_top:
                    st.markdown(f"#### 🚀 상승/주도 지역 TOP 10 ({start_r} ~ {end_r})")
                    top_chart = alt.Chart(top10).mark_bar(color='#ef4444', cornerRadiusEnd=4).encode(
                        x=alt.X('변동률(%):Q', title='상승률 (%)', axis=alt.Axis(grid=False)),
                        y=alt.Y('지역명:N', sort='-x', title=''),
                        tooltip=['지역명:N', alt.Tooltip('변동률(%):Q', format='.2f')]
                    ).properties(height=350)
                    text = top_chart.mark_text(align='left', dx=3, fontWeight='bold').encode(text=alt.Text('변동률(%):Q', format='.2f'))
                    st.altair_chart(top_chart + text, use_container_width=True)
                    
                with col_bot:
                    st.markdown(f"#### 📉 하락/침체 지역 BOTTOM 10 ({start_r} ~ {end_r})")
                    bot_chart = alt.Chart(bot10).mark_bar(color='#3b82f6', cornerRadiusEnd=4).encode(
                        x=alt.X('변동률(%):Q', title='하락률 (%)', axis=alt.Axis(grid=False)),
                        y=alt.Y('지역명:N', sort='x', title=''),
                        tooltip=['지역명:N', alt.Tooltip('변동률(%):Q', format='.2f')]
                    ).properties(height=350)
                    text2 = bot_chart.mark_text(align='left', dx=3, fontWeight='bold').encode(text=alt.Text('변동률(%):Q', format='.2f'))
                    st.altair_chart(bot_chart + text2, use_container_width=True)

                st.divider()
                st.markdown("#### 📋 변동률 히트맵 분석 테이블")
                
                styled_df = calc_df.rename(columns={start_col: f'{start_r} 지수', end_col: f'{end_r} 지수'}).copy()
                st.dataframe(
                    styled_df.style.format({f'{start_r} 지수':'{:.1f}', f'{end_r} 지수':'{:.1f}', '변동률(%)': '{:+.2f}%'})
                    .background_gradient(subset=['변동률(%)'], cmap='vlag'),
                    use_container_width=True, height=500
                )
                
                csv = styled_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 정렬된 데이터 CSV 다운로드", data=csv, file_name=f'ranking_{start_r}_to_{end_r}.csv', mime='text/csv')

elif selected_menu == "📊 원본 데이터 탐색":
    st.title("📊 원본 데이터 뷰어")
    st.markdown("활용된 한국부동산원 원본 엑셀 파일을 탐색하고 다운로드 하십시오.")
    
    st.dataframe(df_original, use_container_width=True, height=650)
    csv_raw = df_original.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 원본 로우데이터 CSV 다운로드", data=csv_raw, file_name='raw_data.csv', mime='text/csv')

st.sidebar.divider()
st.sidebar.caption("🚀 Designed with Altair & Streamlit")
