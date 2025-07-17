import Rhino.Geometry as rg
import random



### -----------------------------------------------------------
### 🔹 1. 유닛 속성별 색상 정의 및 Unit 클래스 선언
### -----------------------------------------------------------

# ✅속성별 유닛 컬러 코딩
# 속성(label)마다 미리 정의된 RGB 색상값을 설정하고
# r, g, b 리스트에 저장한다.
dwelling_color = (255,255,255) # 흰색
void_1_color   = (250,228,167) # 연노랑
void_2_color   = (247,205,165) # 연주황
empty_color    = (246,195,164) # 주황 

# ✅ Unit 클래스 정의
class Unit:
    def __init__(self, brep, label):
        self.brep = brep
        self.label = label
        self.color = self.get_color(label)

    def get_color(self, label):
        if label == "dwelling":
            return dwelling_color
        elif label == "void_1":
            return void_1_color
        elif label == "void_2":
            return void_2_color
        elif label == "empty":
            return empty_color
        else:
            raise Exception('no color')




### -----------------------------------------------------------
### 🔹 2. base_brep를 기반으로 전체 유닛 위치 생성
### -----------------------------------------------------------

# ✅ base_brep를 층수(num_floors), 가로 유닛 수(unit_count) 기준으로 복제하여 배치
all_breps = []
for floor in range(int(num_floors)):
    for i in range(int(unit_count)):
        move_vec = rg.Vector3d(i * 5200, 0, floor * 4000)
        brep_copy = base_brep.Duplicate()
        brep_copy.Transform(rg.Transform.Translation(move_vec))
        all_breps.append(brep_copy)




### -----------------------------------------------------------
### 🔹 3. 층별 유닛 속성 레이블 무작위 배정
### -----------------------------------------------------------
# 🧩 속성 리스트 생성

unit_labels = []
for floor in range(int(num_floors)):
    min_voids = 1
    max_voids = unit_count // 2
    N_voids_floor = random.randint(min_voids, max_voids)
    """     
    # ✅확장 가능성을 고려하여 최소 void 1개 보장하되,
    # ✅전체 유닛의 절반 이하로 void 허용한다. 
    """
    N_void1 = random.randint(0, N_voids_floor)
    N_void2 = random.randint(0, N_voids_floor - N_void1)
    N_empty = N_voids_floor - N_void1 - N_void2
    N_dwellings = unit_count - N_voids_floor

    if N_dwellings < 0:
        raise ValueError("층 단위 유닛 수보다 void 수가 많습니다.")

    floor_labels = (
        ["dwelling"] * N_dwellings +
        ["void_1"] * N_void1 +
        ["void_2"] * N_void2 +
        ["empty"]   * N_empty
    )
    random.shuffle(floor_labels)
    unit_labels.extend(floor_labels)




### -----------------------------------------------------------
### 🔹 4. Unit 객체 생성 및 출력 정보 구성
### -----------------------------------------------------------

# ✅ Unit 인스턴스 생성 및 시각화용 리스트 정리
unit_breps, r, g, b, units = [], [], [], [], []

for brep, label in zip(all_breps, unit_labels):
    unit = Unit(brep, label)
    units.append(unit)
    unit_breps.append(unit.brep)
    r.append(unit.color[0])
    g.append(unit.color[1])
    b.append(unit.color[2])




### -----------------------------------------------------------
### 🔹 5. 결과 요약 정보 출력
### -----------------------------------------------------------

# ✅ 비율 계산 및 예시 출력
N_units = len(all_breps)
N_voids = unit_labels.count("void_1") + unit_labels.count("void_2") + unit_labels.count("empty")
N_dwellings = unit_labels.count("dwelling")

dwelling_ratio = round(N_dwellings / float(N_units), 2)
void_ratio     = round(N_voids / float(N_units), 2)
ratio_str = "dwelling:void = {} : {}  ({} / {})".format(
    dwelling_ratio, void_ratio, N_dwellings, N_voids
)

x = units[0].brep
y = units[0].label

print("생성된 Brep 개수:", len(unit_breps))
print("r/g/b 개수:", len(r), len(g), len(b))
print("라벨 예시:", [unit.label for unit in units[:5]])
