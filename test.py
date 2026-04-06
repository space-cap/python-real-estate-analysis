import pandas as pd
import matplotlib.pyplot as plt

# 1. 간단한 데이터 만들기 (지역별 가상 매매지수)
data = {'Region': ['Gangnam', 'Seocho', 'Songpa', 'Yongsan'],
        'Index': [105.2, 103.8, 101.5, 102.1]}
df = pd.DataFrame(data)

# 2. 터미널에 출력
print("--- 데이터프레임 확인 ---")
print(df)

# 3. 간단한 그래프 그리기
df.plot(kind='bar', x='Region', y='Index', color='skyblue', legend=False)
plt.title('Real Estate Index Test')
plt.show()