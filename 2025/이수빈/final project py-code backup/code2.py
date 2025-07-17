import Rhino.Geometry as rg
import random
import Rhino

import sys
import os

# ✅ utils 폴더 경로를 실행 경로 기준으로 추가
base_dir = os.getcwd()  # 현재 gh 파일이 열려 있는 경로 기준
utils_path = os.path.join(base_dir, "utils")

if utils_path not in sys.path:
    sys.path.append(utils_path)

# ✅ geometry_utils 모듈에서 함수 import
from geometry_utils import (
    get_geoms_from_block_instance,
    get_obj_layer,
    create_block_instance,
    get_geoms_from_block_definition,
    flatten_tree_as_groups,
    find_block_definition_from_guid,
    geom_dict_to_lit
)


### -----------------------------------------------------------
### 🔹 2. Block 정의 추출 및 그룹별 Brep 리스트 구성
### -----------------------------------------------------------

# ✅ 각 block instance의 원본 block 정의 ID (GUID)
void_dwelling_id = block_dwelling.ParentIdefId
void1_id = block_void1.ParentIdefId
void2_id = block_void2.ParentIdefId
void_empty_id = block_empty.ParentIdefId
""" Id (GUID)      → 고유 식별자, definition을 찾는 데 사용 """


# ✅ 현재 Rhino 문서 객체
rhino_doc = Rhino.RhinoDoc.ActiveDoc

# ✅ GUID로부터 block definition 찾기
void_dwelling_def = find_block_definition_from_guid(rhino_doc, void_dwelling_id)
void1_def = find_block_definition_from_guid(rhino_doc, void1_id)
void2_def = find_block_definition_from_guid(rhino_doc, void2_id)
void_empty_def = find_block_definition_from_guid(rhino_doc, void_empty_id)


# ✅ 이후 block instance 삽입을 위한 
void_dwelling_index  = void_dwelling_def.Index
void1_index  = void1_def.Index
void2_index  = void2_def.Index
void_empty_index  = void_empty_def.Index
""" Index (int)    → Rhino 문서 내부 리스트의 위치, 삽입 시 사용 """

# ✅ Dict 형태 geometry 모음을 단일 리스트로 변환
def geom_dict_to_list(geom_dict):
    result = []
    for geoms in geom_dict.values():
        result += geoms
    return result

# ✅ 각 block definition으로부터 geometry 리스트 구성
breps_dwelling = geom_dict_to_list(get_geoms_from_block_definition(rhino_doc, void_dwelling_def))
breps_void1    = geom_dict_to_list(get_geoms_from_block_definition(rhino_doc, void1_def))
breps_void2    = geom_dict_to_list(get_geoms_from_block_definition(rhino_doc, void2_def))
breps_empty    = geom_dict_to_list(get_geoms_from_block_definition(rhino_doc, void_empty_def))


### -----------------------------------------------------------
### 🔹 1. 속성별 유닛 색상 정의 및 Unit 클래스 선언
### -----------------------------------------------------------

# ✅속성별 유닛 컬러 코딩
# 속성(label)마다 미리 정의된 RGB 색상값을 설정하고
# r, g, b 리스트에 저장한다.
dwelling_color = (255,255,255) # 흰색
void_1_color = (250,228,167) # 연노랑
void_2_color = (247,205,165) # 연주황
empty_color = (246,195,164) # 주황 

# 최종 출력 리스트
unit_breps = []
r, g, b = [], [], []

### -----------------------------------------------------------
### 🔹 4. 경로 기반 유닛 배치 좌표 생성
### -----------------------------------------------------------

# ✅ 유닛 간 간격 및 경로 길이 기반 자동 계산
unit_spacing = 5200
path_length = path_curve.GetLength()
unit_count = int(path_length // unit_spacing)


# ✅ 일정 간격마다 t값 추출하여 path 위 포인트 생성
t_values = []
d = 0
while d <= min(path_length, unit_spacing * (unit_count - 1)):
    t = path_curve.LengthParameter(d)[1]
    t_values.append(t)
    d += unit_spacing


### -----------------------------------------------------------
### 🔹 5. 층별 unit label 구성 (dwelling / void / empty)
### -----------------------------------------------------------

# 🧩 속성 리스트 생성
    # ✅확장 가능성을 고려하여 최소 void 1개 보장하되,
    # ✅전체 유닛의 절반 이하로 void 허용한다.
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

    floor_labels = (
        ["dwelling"] * N_dwellings +
        ["void_1"] * N_void1 +
        ["void_2"] * N_void2 +
        ["empty"]   * N_empty
    )
    random.shuffle(floor_labels)
    unit_labels.extend(floor_labels)


### -----------------------------------------------------------
### 🔹 유닛 배치 관련 함수 정의
### -----------------------------------------------------------

# ✅ 유닛 배치 평면 생성 함수
def get_unit_plane(t_value, z_level):
    success, base_plane = path_curve.FrameAt(t_value)
    if not success:
        return None

    origin = base_plane.Origin + rg.Vector3d(0, 0, z_level * 4000)
    x_axis = base_plane.XAxis
    z_axis = rg.Vector3d(0, 0, 1)

    y_axis = rg.Vector3d.CrossProduct(z_axis, x_axis)
    z_axis = rg.Vector3d.CrossProduct(x_axis, y_axis)

    x_axis.Unitize()
    y_axis.Unitize()
    z_axis.Unitize()

    return rg.Plane(origin, x_axis, y_axis)

# ✅ 그룹 중심 기준으로 트랜스폼 수행
def get_transformed_geometries(group, source_plane, target_plane):
    all_pts = []
    for geo in group:
        all_pts.extend(geo.GetBoundingBox(True).GetCorners())
    group_center = rg.BoundingBox(all_pts).Center
    source_plane = rg.Plane(group_center, rg.Vector3d.XAxis, rg.Vector3d.YAxis)

    xform = rg.Transform.PlaneToPlane(source_plane, target_plane)
    transformed = []

    for geo in group:
        geo_copy = geo.Duplicate()
        geo_copy.Transform(xform)
        transformed.append(geo_copy)

    return transformed, xform

# ✅ 레이블에 따른 group/색상/블록ID 반환
def get_unit_by_label(label):
    if label == "dwelling":
        return breps_dwelling, dwelling_color, void_dwelling_index
    elif label == "void_1":
        return breps_void1, void_1_color, void1_index
    elif label == "void_2":
        return breps_void2, void_2_color, void2_index
    elif label == "empty":
        return breps_empty, empty_color, void_empty_index
    else:
        return None, None, None

### -----------------------------------------------------------
### 🔹 유닛 복제 및 배치 실행
### -----------------------------------------------------------

for idx, label in enumerate(unit_labels):
    x_idx = idx % unit_count
    z_idx = idx // unit_count

    plane = get_unit_plane(t_values[x_idx], z_idx)
    if plane is None:
        continue

    group, color, block_def_id = get_unit_by_label(label)
    if group is None:
        continue

    transformed_geoms, xform = get_transformed_geometries(group, None, plane)

    if bake:
        create_block_instance(rhino_doc, block_def_id, transform=xform)

    unit_breps.extend(transformed_geoms)
    r.extend([color[0]] * len(transformed_geoms))
    g.extend([color[1]] * len(transformed_geoms))
    b.extend([color[2]] * len(transformed_geoms))



### -----------------------------------------------------------
### 🔹 7. 최종 출력
### -----------------------------------------------------------
a = unit_breps
R = r
G = g
B = b




