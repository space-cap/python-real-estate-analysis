import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import oracledb
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_DSN = os.getenv("DB_DSN")

# 전역 커넥션 풀 변수
db_pool = None

# --- 1. 서버 라이프사이클 관리 (시작할 때 풀 생성, 꺼질 때 풀 반환) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool
    try:
        # 최소 2개, 최대 10개의 커넥션을 유지하는 풀 생성
        db_pool = oracledb.create_pool(
            user=DB_USER,
            password=DB_PASSWORD,
            dsn=DB_DSN,
            min=2,
            max=10,
            increment=1
        )
        print("✅ 오라클 DB 커넥션 풀 생성 완료!")
        yield
    finally:
        if db_pool:
            db_pool.close()
            print("🛑 오라클 DB 커넥션 풀 종료")

# --- 2. FastAPI 앱 초기화 ---
app = FastAPI(title="부동산 매매지수 API", lifespan=lifespan)

# 프론트엔드(Next.js 등)에서 호출할 수 있도록 CORS 허용 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 실무에서는 실제 도메인으로 제한해야 합니다
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 3. API 엔드포인트 ---

@app.get("/")
def read_root():
    return {"message": "부동산 매매지수 API 서버가 정상 작동 중입니다. 🚀"}

@app.get("/api/regions")
def get_regions():
    """전체 지역 마스터 목록을 반환합니다."""
    try:
        with db_pool.acquire() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT REGION_ID, REGION_NAME FROM TB_REGION ORDER BY REGION_ID")
                # 컬럼명을 키로 하는 딕셔너리 리스트로 변환
                columns = [col[0] for col in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ranking")
def get_ranking(
    target_month: str = Query(..., description="조회할 연월 (예: 202603)"),
    limit: int = Query(10, description="가져올 순위 개수")
):
    """특정 월을 기준으로 상승 지수가 가장 높은 지역 TOP N을 반환합니다."""
    try:
        with db_pool.acquire() as connection:
            with connection.cursor() as cursor:
                # 보안을 위한 바인드 변수(:month, :limit) 사용
                query = """
                    SELECT 
                        R.REGION_NAME, 
                        I.INDEX_VALUE
                    FROM TB_APT_PRICE_INDEX I
                    JOIN TB_REGION R ON I.REGION_ID = R.REGION_ID
                    WHERE I.BASE_YYYYMM = :month
                    ORDER BY I.INDEX_VALUE DESC
                    FETCH FIRST :limit ROWS ONLY
                """
                cursor.execute(query, month=target_month, limit=limit)
                
                columns = [col[0] for col in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return {"status": "success", "target_month": target_month, "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trend/{region_id}")
def get_trend(region_id: int):
    """특정 지역의 전체 시계열 매매지수 변화를 반환합니다 (선 그래프용)."""
    try:
        with db_pool.acquire() as connection:
            with connection.cursor() as cursor:
                query = """
                    SELECT BASE_YYYYMM, INDEX_VALUE 
                    FROM TB_APT_PRICE_INDEX 
                    WHERE REGION_ID = :reg_id
                    ORDER BY BASE_YYYYMM ASC
                """
                cursor.execute(query, reg_id=region_id)
                
                columns = [col[0] for col in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return {"status": "success", "region_id": region_id, "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))