import pandas as pd
from pyproj import CRS, Transformer

# 좌표 변환기 정의 (WGS84 → KGD2002_Central_Belt_2010)
crs_wgs84 = CRS.from_epsg(4326)
crs_kgd2002_tm = CRS.from_proj4(
    "+proj=tmerc +lat_0=38 +lon_0=127 +k=1 +x_0=200000 +y_0=600000 "
    "+ellps=GRS80 +units=m +no_defs"
)
transformer = Transformer.from_crs(crs_wgs84, crs_kgd2002_tm, always_xy=True)

# CSV 파일 불러오기
df = pd.read_csv("protest_with_coords.csv", encoding="utf-8")


# 위도/경도 → X, Y, Z 변환 함수 정의
def convert_coords(row):
    lon, lat = row["경도"], row["위도"]
    if pd.notnull(lon) and pd.notnull(lat):
        x, y = transformer.transform(lon, lat)
        return pd.Series([x, y, 0])  # Z는 항상 0
    else:
        return pd.Series([None, None, None])


# 변환 실행
df[["X", "Y", "Z"]] = df.apply(convert_coords, axis=1)

# 변환된 좌표 확인
print(df[["정제된장소", "X", "Y", "Z"]])

# CSV 저장
df.to_csv("protest_final.csv", index=False, encoding="utf-8-sig")
