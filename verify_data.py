import os
import pandas as pd
import oracledb
from dotenv import load_dotenv
import warnings

# 🌟 2. Pandas의 SQLAlchemy 권장 UserWarning을 화면에 띄우지 않도록 무시 설정
warnings.filterwarnings('ignore', category=UserWarning)

# 환경 변수 로드
load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_DSN = os.getenv("DB_DSN")

def verify_oracle_data():
    try:
        # DB 연결
        connection = oracledb.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            dsn=DB_DSN
        )
        print("✅ DB 접속 성공! 검증을 시작합니다.\n")
        
        # 결과를 예쁘게 출력하기 위한 Pandas 설정
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)

        # ---------------------------------------------------------
        # 1. 데이터 건수 확인 (마스터 vs 팩트)
        # ---------------------------------------------------------
        count_query = """
            SELECT 
                (SELECT COUNT(*) FROM TB_REGION) AS REGION_COUNT,
                (SELECT COUNT(*) FROM TB_APT_PRICE_INDEX) AS INDEX_COUNT
            FROM DUAL
        """
        df_count = pd.read_sql(count_query, con=connection)
        print("📊 [검증 1] 테이블 데이터 총 건수")
        print(f" - 지역 마스터(TB_REGION): {df_count['REGION_COUNT'].iloc[0]:,}건")
        print(f" - 매매지수(TB_APT_PRICE_INDEX): {df_count['INDEX_COUNT'].iloc[0]:,}건\n")

        # ---------------------------------------------------------
        # 2. 동명이인 지역명 분리 검증 ('중구' 검색)
        # ---------------------------------------------------------
        junggu_query = """
            SELECT REGION_ID, REGION_NAME 
            FROM TB_REGION 
            WHERE REGION_NAME LIKE '%중구%'
            ORDER BY REGION_ID
        """
        df_junggu = pd.read_sql(junggu_query, con=connection)
        print("🕵️‍♂️ [검증 2] 골칫거리였던 '중구' 데이터 확인 (계층형 이름 결합 테스트)")
        print(df_junggu.to_string(index=False), "\n")

        # ---------------------------------------------------------
        # 3. 최신 데이터 무결성 및 조인 테스트 (가장 최근 월의 TOP 5)
        # ---------------------------------------------------------
        top5_query = """
            SELECT 
                R.REGION_NAME, 
                I.BASE_YYYYMM, 
                I.INDEX_VALUE
            FROM TB_APT_PRICE_INDEX I
            JOIN TB_REGION R ON I.REGION_ID = R.REGION_ID
            WHERE I.BASE_YYYYMM = (SELECT MAX(BASE_YYYYMM) FROM TB_APT_PRICE_INDEX)
            ORDER BY I.INDEX_VALUE DESC
            FETCH FIRST 5 ROWS ONLY
        """
        df_top5 = pd.read_sql(top5_query, con=connection)
        latest_month = df_top5['BASE_YYYYMM'].iloc[0] if not df_top5.empty else "N/A"
        
        print(f"🏆 [검증 3] {latest_month} 기준, 전국 아파트 매매지수 TOP 5 (JOIN 테스트)")
        print(df_top5.to_string(index=False), "\n")

        print("🎉 모든 검증 쿼리가 성공적으로 실행되었습니다!")

    except Exception as e:
        print("❌ DB 에러 발생:", e)
    finally:
        if 'connection' in locals():
            connection.close()

if __name__ == "__main__":
    verify_oracle_data()