import pandas as pd
import requests
import time

# 내 api 주소 불러오기
KAKAO_API_KEY = ""


def extract_main_keyword(location):
    # 쉼표로 구분해서 첫 번째 키워드만 추출
    if pd.isna(location):
        return ""
    return location.split(",")[0].strip()


# 키워드로 주소의 위도, 경도 찾기
def get_coords_kakao(query):
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params = {"query": query}

    try:
        response = requests.get(url, headers=headers, params=params)
        time.sleep(0.5)
        if response.status_code == 200:
            result = response.json()
            if result["documents"]:
                x = result["documents"][0]["x"]
                y = result["documents"][0]["y"]
                return pd.Series([y, x])
        return pd.Series([None, None])
    except Exception as e:
        print(f"Error for {query}: {e}")
        return pd.Series([None, None])


df = pd.read_csv("classified_protests.csv", encoding="utf-8")
# 정제된 키워드 추출
df["검색용장소"] = df["정제된장소"].apply(extract_main_keyword)
# 위도/경도 검색
df[["위도", "경도"]] = df["검색용장소"].apply(get_coords_kakao)
# 결과 저장
df.to_csv("protest_with_coords.csv", index=False, encoding="utf-8-sig")
print("완료 'protest_with_coords.csv' 파일 생성됨")
