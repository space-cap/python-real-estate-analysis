import os
import oracledb
from dotenv import load_dotenv

# 1. .env 파일 로드 (이 코드가 실행되면 .env 안의 값들이 환경 변수로 등록됩니다)
load_dotenv()

# 2. 환경 변수에서 값 가져오기
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_dsn = os.getenv("DB_DSN")

try:
    # 3. 변수를 사용하여 안전하게 접속
    connection = oracledb.connect(
        user=db_user,
        password=db_password,
        dsn=db_dsn
    )
    print("DB 연결 성공 (보안 적용 완료)!")
    
    cursor = connection.cursor()

    # 3. 데이터 삽입 쿼리 준비 (오라클은 바인드 변수로 :1, :2 등을 사용합니다)
    sql = "INSERT INTO real_estate_item (title, price) VALUES (:1, :2)"

    # 넣을 데이터 리스트 (보통 크롤링이나 CSV에서 읽어온 데이터가 들어갑니다)
    data = [
        ('강남구 래미안 아파트', 250000),
        ('서초구 자이 아파트', 220000),
        ('송파구 시그니엘', 450000)
    ]

    # 4. executemany로 여러 줄을 한 방에 고속으로 밀어 넣기
    cursor.executemany(sql, data)
    
    # 5. 오라클은 커밋(Commit)을 해야 실제 DB에 반영됩니다.
    connection.commit()
    
    print(f"{cursor.rowcount}건의 부동산 데이터가 성공적으로 저장되었습니다!")

except Exception as e:
    print("DB 오류 발생:", e)
finally:
    # 6. 작업이 끝나면 문을 닫아줍니다.
    if 'cursor' in locals():
        cursor.close()
    if 'connection' in locals():
        connection.close()