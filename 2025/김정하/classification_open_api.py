import pandas as pd
import openai

# API 키 입력
openai.api_key = ""

# CSV 불러오기
df = pd.read_csv("protest_data.csv", encoding="utf-8-sig")
df.columns = df.columns.str.strip()  # 공백 제거

# open api에게 분류 지시
results = []

for index, row in df.iterrows():
    prompt = f"""
    다음 시위 사례를 보고 시위 방식이 '공격형'인지 '문화형'인지 딱 한 단어로 판단해줘.

    - 시위명: {row['시위명']}
    - 날짜: {row['날짜']}
    - 장소: {row['장소']}
    - 인원: {row['인원']}
    - 요구/구호: {row['요구/구호']}
    - 방식: {row['방식']}

    정의:
    - 공격형: 특정 대상에 분노/압박을 표출하며 직접적인 변화를 요구 (예: 점거, 농성, 규탄발언)
    - 문화형: 공감 유도나 인식 개선을 목표로 퍼포먼스, 캠페인, 전시 등을 중심으로 함
    답변은 '공격형' 또는 '문화형' 중 하나로만 해줘.
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "너는 시위방식을 분석하는 정치사회 데이터 분석가야.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        label = response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        label = f"에러: {e}"

    print(f"{row['시위명']} → {label}")
    results.append(label)

# 결과 저장
df["분류"] = results
df.to_csv("classified_protests.csv", index=False, encoding="utf-8-sig")
print("✅ 파일 저장 완료: classified_protests.csv")
