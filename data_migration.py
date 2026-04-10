import os
import pandas as pd
import oracledb
from dotenv import load_dotenv

# 1. 환경 변수 로드 (.env 파일 활용)
load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_DSN = os.getenv("DB_DSN")

def load_data_to_oracle():
    print("🚀 데이터 마이그레이션 시작...")
    
    file_path = 'data/apt_price_20260408.xlsx'
    
    try:
        df = pd.read_excel(file_path)
    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
        return

    # 날짜 컬럼 이름이 datetime 객체로 인식되는 것을 막기 위해 모두 문자로 변환
    df.columns = df.columns.astype(str)

    # 지역명 컬럼 전처리
    first_col = df.columns[0]
    df.rename(columns={first_col: 'RAW_REGION'}, inplace=True)
    df['RAW_REGION'] = df['RAW_REGION'].astype(str).str.strip()
    
    # 🌟 [로직 1] 전국구 서비스용 계층형 지역명 생성 (동명이인 '중구' 에러 방지)
    sido_list = ['서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종', '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주']
    
    full_region_names = []
    current_sido = ""
    
    for region in df['RAW_REGION']:
        if region in sido_list:
            current_sido = region
            full_region_names.append(region)
        elif region in ['전국', '수도권', '지방', '6개광역시', '5개광역시', '8개도', '9개도', '강북14개구', '강남11개구']:
            current_sido = "" # 통계용 대분류는 소속 없이 그대로 둠
            full_region_names.append(region)
        else:
            # 하위 지역인 경우 앞에 '시/도'를 붙여서 고유한 이름으로 만듦 (예: '서울 중구', '부산 중구')
            if current_sido:
                full_region_names.append(f"{current_sido} {region}")
            else:
                full_region_names.append(region)
    
    # 🌟 추가된 코드: 넓어진 데이터프레임의 메모리 조각(파편화)을 한 번 깔끔하게 모아줍니다.
    df = df.copy()

    # 새로 만든 고유한 지역명을 REGION_NAME 컬럼으로 확정
    df['REGION_NAME'] = full_region_names

    try:
        # DB 연결
        connection = oracledb.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            dsn=DB_DSN
        )
        print("✅ 오라클 클라우드 DB 접속 성공 (보안 적용 완료)!")
        
        cursor = connection.cursor()

        # 🌟 핵심 해결책: 오라클의 병렬 처리(우르르 몰려가기)를 끄고 차분하게 하나씩 넣도록 지시!
        cursor.execute("ALTER SESSION DISABLE PARALLEL DML")
        
        # --- 3. 지역 마스터 (TB_REGION) 데이터 삽입 ---
        unique_regions = df['REGION_NAME'].dropna().unique()
        print(f"🗺️ 총 {len(unique_regions)}개의 고유 지역 마스터 데이터 적재 중...")
        
        for region in unique_regions:
            try:
                # 위치(:1) 대신 이름(:region_name) 기반 바인딩
                cursor.execute("""
                    INSERT INTO TB_REGION (REGION_NAME) 
                    SELECT :region_name FROM DUAL 
                    WHERE NOT EXISTS (SELECT 1 FROM TB_REGION WHERE REGION_NAME = :region_name)
                """, {"region_name": region})
            except Exception as e:
                print(f"지역 삽입 에러 ({region}):", e)
        
        connection.commit()

        # DB에 들어간 지역 ID 맵핑 가져오기
        cursor.execute("SELECT REGION_ID, REGION_NAME FROM TB_REGION")
        region_map = {row[1]: row[0] for row in cursor.fetchall()}

        # --- 4. 매매가격지수 (TB_APT_PRICE_INDEX) 데이터 삽입 ---
        date_cols = [col for col in df.columns if col not in ['RAW_REGION', 'REGION_NAME'] and not col.startswith('Unnamed')]
        df_melted = pd.melt(df, id_vars=['REGION_NAME'], value_vars=date_cols, var_name='BASE_DATE', value_name='INDEX_VALUE')
        
        # 🌟 [로직 2] '-' 등 문자로 된 결측치를 에러 없이 빈칸(NaN)으로 변환 후 삭제
        df_melted['INDEX_VALUE'] = pd.to_numeric(df_melted['INDEX_VALUE'], errors='coerce')
        df_melted = df_melted.dropna(subset=['INDEX_VALUE'])
        
        # 날짜 포맷팅 변환 (YYYY-MM-DD -> YYYYMM)
        df_melted['BASE_YYYYMM'] = df_melted['BASE_DATE'].astype(str).str.replace('-', '').str[:6]
        
        insert_data = []
        for _, row in df_melted.iterrows():
            reg_name = row['REGION_NAME']
            if reg_name in region_map:
                insert_data.append((
                    region_map[reg_name], 
                    row['BASE_YYYYMM'], 
                    float(row['INDEX_VALUE'])
                ))
        
        print(f"📈 총 {len(insert_data)}건의 지수 데이터 정제 완료.")
        
        # 🌟 [로직 3] 멱등성 보장: 기존 찌꺼기 데이터 깔끔하게 삭제 (중복 에러 방지)
        print("🧹 기존 지수 데이터를 안전하게 초기화(삭제)합니다...")
        cursor.execute("DELETE FROM TB_APT_PRICE_INDEX")
        
        print("🚀 DB에 새 데이터 적재 중... 잠시만 기다려주세요.")
        cursor.executemany("""
            INSERT INTO TB_APT_PRICE_INDEX (REGION_ID, BASE_YYYYMM, INDEX_VALUE)
            VALUES (:1, :2, :3)
        """, insert_data)
        
        connection.commit()
        print("🎉 모든 데이터 마이그레이션이 완벽하게 끝났습니다!")

    except Exception as e:
        print("❌ DB 에러 발생:", e)
    finally:
        # 5. 자원 해제
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()

if __name__ == "__main__":
    load_data_to_oracle()