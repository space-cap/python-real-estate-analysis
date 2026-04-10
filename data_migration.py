import os
import pandas as pd
import oracledb
from dotenv import load_dotenv

# 1. 환경 변수 로드
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
    df.rename(columns={first_col: 'REGION_NAME'}, inplace=True)
    df['REGION_NAME'] = df['REGION_NAME'].astype(str).str.strip()
    
    try:
        connection = oracledb.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            dsn=DB_DSN
        )
        print("✅ 오라클 클라우드 DB 접속 성공 (보안 적용 완료)!")
        
        cursor = connection.cursor()
        
        # --- 3. 지역 마스터 (TB_REGION) 데이터 삽입 ---
        unique_regions = df['REGION_NAME'].dropna().unique()
        print(f"🗺️ 총 {len(unique_regions)}개의 지역 데이터 적재 중...")
        
        for region in unique_regions:
            try:
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
        date_cols = [col for col in df.columns if col != 'REGION_NAME' and not col.startswith('Unnamed')]
        df_melted = pd.melt(df, id_vars=['REGION_NAME'], value_vars=date_cols, var_name='BASE_DATE', value_name='INDEX_VALUE')
        
        # 🌟 핵심 버그 픽스: 고창군 등에 있는 '-' 같은 문자를 만나면 에러 대신 빈칸(NaN)으로 변환!
        df_melted['INDEX_VALUE'] = pd.to_numeric(df_melted['INDEX_VALUE'], errors='coerce')
        
        # 그 다음, 숫자가 아닌 값이 들어있어 빈칸(NaN)이 된 행을 안전하게 삭제합니다.
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
        
        print(f"📈 총 {len(insert_data)}건의 지수 데이터 정제 완료. DB에 적재 중... 잠시만 기다려주세요.")
        
        cursor.executemany("""
            INSERT INTO TB_APT_PRICE_INDEX (REGION_ID, BASE_YYYYMM, INDEX_VALUE)
            VALUES (:1, :2, :3)
        """, insert_data)
        
        connection.commit()
        print("🎉 모든 데이터 마이그레이션이 완벽하게 끝났습니다!")

    except Exception as e:
        print("❌ DB 에러 발생:", e)
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()

if __name__ == "__main__":
    load_data_to_oracle()