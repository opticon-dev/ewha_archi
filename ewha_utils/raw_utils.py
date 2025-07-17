import Rhino
import Rhino.Geometry as geo  # 모든 geo import를 geo로 통일
from typing import List, Union, Optional, Dict, Any
import random
import os
import json
from System.Drawing import Color
from collections import defaultdict


## 권유진
def get_closest_point(pt: geo.Point3d, crv: geo.Curve) -> Optional[geo.Point3d]:
    """
    권유진 작성
    주어진 점에서 커브까지 가장 가까운 점 반환
    """
    success, param = crv.ClosestPoint(pt)
    return crv.PointAt(param) if success else None


## 권유진
def get_dist_from_pt_crv(pt: geo.Point3d, crv: geo.Curve) -> float:
    """
    권유진 작성
    점과 커브 사이의 최단거리 반환
    """
    closest_pt = get_closest_point(pt, crv)
    return pt.DistanceTo(closest_pt) if closest_pt else float("inf")


## 권유진
def generate_points_in_curve(
    curve: geo.Curve, step: int = 500, offset: int = 200
) -> List[geo.Point3d]:
    """
    권유진 작성
    주어진 커브 내부에 일정 간격으로 점 생성
    - BoundingBox 내에서 grid 점을 만들고,
    - 커브 내부에 포함된 점만 반환
    """
    bbox = curve.GetBoundingBox(True)
    x_count = int((bbox.Max.X - bbox.Min.X) // step)
    y_count = int((bbox.Max.Y - bbox.Min.Y) // step)
    min_point = bbox.Min + geo.Point3d(offset, offset, 0)

    points = []
    for i in range(x_count):
        for j in range(y_count):
            pt = geo.Point3d(
                min_point.X + step * i, min_point.Y + step * j, min_point.Z
            )
            if (
                curve.Contains(pt, geo.Plane.WorldXY, 0.01)
                == geo.PointContainment.Inside
            ):
                points.append(pt)
    return points


## 권유진
def is_pt_inside(pt: geo.Point3d, crv: geo.Curve) -> bool:
    """
    권유진 작성
    점이 커브 내부에 있는지 확인
    """
    return crv.Contains(pt) == geo.PointContainment.Inside


## 김정하
def map_headcount_to_radius(raw: str) -> float:
    """
    김정하 작성
    인원 수 텍스트(예: '수천명', '5000명')를 받아
    시각화용 원 반지름 크기(200~800)로 변환해주는 함수
    """
    try:
        if not raw:
            return 100

        raw = raw.strip().replace(",", "").replace("명", "").replace(" ", "")

        scale_dict = {
            "1": 1,
            "수십": 50,
            "수백": 500,
            "수천": 5000,
            "수만": 50000,
            "수십만": 200000,
        }

        if raw.isdigit():
            num = int(raw)
        elif raw in scale_dict:
            num = scale_dict[raw]
        else:
            print("인원 수 해석 실패 →", raw)
            return 100

        min_val = 1
        max_val = 200000
        normalized = (num - min_val) / float(max_val - min_val)
        radius = 200 + normalized * (800 - 200)
        return round(radius, 2)

    except:
        return 100


## 박시영
def get_points_in_bbox(bbox: geo.BoundingBox, step: float) -> List[geo.Point3d]:
    """
    박시영 작성
    삼중으로 바운딩 박스 생성
    """
    points = []
    x_count = int((bbox.Max.X - bbox.Min.X) // step) + 1  # boundin box내부 x점 개수
    y_count = int((bbox.Max.Y - bbox.Min.Y) // step) + 1  # boundin box내부 y점 개수
    z_count = int((bbox.Max.Z - bbox.Min.Z) // step) + 1  # boundin box내부 z점 개수

    # 삼중으로 돌면서 3차원 점 생성
    for i in range(x_count):
        for j in range(y_count):
            for k in range(z_count):
                x = bbox.Min.X + i * step
                y = bbox.Min.Y + j * step
                z = bbox.Min.Z + k * step
                pt = geo.Point3d(x, y, z)
                points.append(pt)
    return points


## 박시영
def generate_co2_levels(
    count: int, min_value: float = 400, max_value: float = 1000
) -> List[float]:
    """
    박시영 작성
    랜덤으로 CO2농도 부여
    """
    return [random.uniform(min_value, max_value) for _ in range(count)]


## 박시영
def divide_srf(srf: geo.Surface, u_count: int, v_count: int) -> List[geo.Surface]:
    """
    박시영 작성
    서피스 분할
    """
    # 분할된 서브서피스를 저장할 리스트
    sub_surfaces = []

    # 도메인 가져오기
    u_domain = srf.Domain(0)
    v_domain = srf.Domain(1)

    # u, v 파라미터 간격 계산
    u_step = (u_domain.T1 - u_domain.T0) / u_count
    v_step = (v_domain.T1 - v_domain.T0) / v_count

    # 서피스를 분할
    for i in range(u_count):
        for j in range(v_count):
            u0 = u_domain.T0 + i * u_step
            u1 = u_domain.T0 + (i + 1) * u_step
            v0 = v_domain.T0 + j * v_step
            v1 = v_domain.T0 + (j + 1) * v_step

            u_interval = geo.Interval(u0, u1)
            v_interval = geo.Interval(v0, v1)

            # 올바른 Trim 함수 사용
            trimmed = srf.Trim(u_interval, v_interval)
            if trimmed:
                sub_surfaces.append(trimmed)

    return sub_surfaces


## 박시영
def get_dist_srf_to_pt(srf: geo.Surface, pt: geo.Point3d) -> float:
    """
    박시영 작성
    패널그룹과 가장 가까운 포인트 사이의 거리 계산
    """
    success, u, v = srf.ClosestPoint(pt)
    if success:
        # 해당 u,v 위치의 3D 좌표를 구함
        closest_pt_on_surface = srf.PointAt(u, v)

        # 원래의 Point와 가장 가까운 점 사이의 거리 계산
        distance = pt.DistanceTo(closest_pt_on_surface)
        return distance

    else:
        raise Exception("error")


## 서은미
def point_to_key(pt: geo.Point3d, precision: int = 3) -> tuple:
    """
    서은미 작성
    Point3d 객체를 좌표 기준으로 반올림하여 key로 변환
    """
    return (round(pt.X, precision), round(pt.Y, precision), round(pt.Z, precision))


## 서은미
def count_duplicate_points(pts: List[geo.Point3d], precision: int = 3) -> dict:
    """
    서은미 작성
    포인트 리스트에서 중복 위치에 대한 개수를 세는 딕셔너리 반환
    """
    count = defaultdict(int)
    for pt in pts:
        key = point_to_key(pt, precision)
        count[key] += 1
    return count


## 서은미
def get_cctv_color(count: int) -> Color:
    """
    서은미 작성
    중복 개수에 따라 CCTV 색상 반환
    """
    if count >= 2:
        return Color.FromArgb(255, 255, 0, 0)  # 진한 빨강
    else:
        return Color.FromArgb(100, 255, 100, 100)  # 연한 빨강


## 서은미
def is_visible(
    point: geo.Point3d, cctv: geo.Point3d, obstacles: List[geo.Curve]
) -> bool:
    """
    서은미 작성
    CCTV 시야 체크 (장애물에 가리는지 여부 확인)
    """
    line = geo.LineCurve(point, cctv)
    for obs in obstacles:
        if geo.Intersect.Intersection.CurveCurve(line, obs, 0.01, 0.01).Count > 0:
            return False
    return True


## 서은미
def is_on_sidewalk(point: geo.Point3d, sidewalks: List[geo.Curve]) -> bool:
    """
    서은미 작성
    인도 안에 포함되는지 확인
    """
    for crv in sidewalks:
        if isinstance(crv, geo.Curve) and crv.IsClosed:
            if crv.Contains(point, geo.Plane.WorldXY, 0.01) in [
                geo.PointContainment.Inside,
                geo.PointContainment.Coincident,
            ]:
                return True
    return False


## 서은미
def score_by_distance(
    point: geo.Point3d, targets: List[geo.Point3d], max_dist: float, max_score: float
) -> float:
    """
    서은미 작성
    거리 기반 점수 부여 함수 (선형 감쇠 방식)
    어떠한 요소가 일정 반경 이내에 있는지에 따라 판별(예. 편의점, 지구대)
    """
    score = 0
    for target in targets:
        if isinstance(target, geo.Point3d):
            dist = point.DistanceTo(target)
            if dist <= max_dist:
                score += max_score * (1 - dist / max_dist)
    return score


## 서은미
def check_point_safety(
    point: geo.Point3d,
    cctvs: List[geo.Point3d],
    obstacles: List[geo.Curve],
    sidewalks: List[geo.Curve],
    cvs_list: List[geo.Point3d],
    police_list: List[geo.Point3d],
) -> float:
    """
    서은미 작성
    각 포인트에 대한 안전 점수 계산
    """
    score = 0

    # cctv의 반경과 가림 여부
    for cctv in cctvs:
        if isinstance(cctv, geo.Point3d):
            if point.DistanceTo(cctv) <= 20 and is_visible(point, cctv, obstacles):
                score += 40

    # 인도 포함 여부
    if is_on_sidewalk(point, sidewalks):
        score += 60

    # 안전에 영향을 끼칠 요소와의 거리
    score += score_by_distance(point, cvs_list, 30, 50)
    score += score_by_distance(point, police_list, 50, 100)

    return score


## 오정서
def geo_to_xy(lat: float, lon: float, scale: float = 100000) -> geo.Point3d:
    """
    오정서 작성
    위도(lat), 경도(lon)를 Rhino의 XY 평면 좌표로 변환하는 함수
    """
    x = lon * scale
    y = lat * scale
    return geo.Point3d(x, y, 0)


## 오정서
def congestion_to_radius(congestion: float, scale: float = 1.0) -> float:
    """
    오정서 작성
    혼잡도(congestion) 수치를 시각화용 원의 반지름으로 변환하는 함수
    """
    return max(5, scale * (congestion**0.5))


## 이수빈
def get_geoms_from_block_instance(
    rhino_doc, block_instance: Rhino.DocObjects.InstanceObject
) -> dict:
    """
    이수빈 작성
    block instance 내부의 모든 geometry를 가져온다. Block Definition은 원점 인근에 있으므로, 이를 현재 block 위치로 translate한다.
    """
    if block_instance is None or not isinstance(
        block_instance, Rhino.DocObjects.InstanceObject
    ):
        raise ValueError("Selected object is not a block instance.")

    # 블록 정의 가져오기
    block_def = block_instance.InstanceDefinition

    if block_def is None:
        raise ValueError("Block definition not found.")

    # 블록 인스턴스의 변환 행렬 (블록 인스턴스의 위치와 방향)
    instance_xform = block_instance.InstanceXform

    geoms_dict = {}
    # 블록 정의의 구성 요소를 순회하며 커브 찾기
    for i in range(block_def.ObjectCount):
        obj = block_def.Object(i)
        if isinstance(obj, Rhino.DocObjects.InstanceObject):
            for k, v in get_geoms_from_block_instance(rhino_doc, obj).items():
                geoms_transformed = []
                for geom in v:
                    transformed_geom = geom.Duplicate()
                    transformed_geom.Transform(instance_xform)
                    geoms_transformed.append(transformed_geom)
                if k not in geoms_dict:
                    geoms_dict[k] = geoms_transformed
                else:
                    geoms_dict[k] += geoms_transformed

        else:
            layer_name = get_obj_layer(obj, rhino_doc).FullPath
            geometry = obj.Geometry

            # 블록 인스턴스의 변환 행렬을 적용한 커브 복사본 생성
            transformed_geom = geometry.Duplicate()
            transformed_geom.Transform(instance_xform)
            if layer_name not in geoms_dict:
                geoms_dict[layer_name] = [transformed_geom]
            else:
                geoms_dict[layer_name].append(transformed_geom)

    return geoms_dict


## 이수빈
def get_obj_layer(obj, rhino_doc) -> Rhino.DocObjects.Layer:
    """
    이수빈 작성
    객체의 레이어 정보 가져오기
    """
    layer_index = obj.Attributes.LayerIndex
    return rhino_doc.Layers[layer_index]


## 이수빈
def create_block_instance(
    doc: Rhino.RhinoDoc, block_def_id: int, transform
) -> Rhino.DocObjects.InstanceObject:
    """
    이수빈 작성
    block definition 기준으로 instance 삽입
    """
    instance_id = doc.Objects.AddInstanceObject(block_def_id, transform)
    block_instance = Rhino.RhinoDoc.ActiveDoc.Objects.Find(instance_id)
    return block_instance


## 이수빈
def get_geoms_from_block_definition(rhino_doc, block_definition) -> dict:
    """
    이수빈 작성
    block definition 내부 geometry 추출 (instance 없이 직접 가져옴)
    """
    geoms_dict = {}
    for i in range(block_definition.ObjectCount):
        obj = block_definition.Object(i)
        if isinstance(obj, Rhino.DocObjects.InstanceObject):
            for k, v in get_geoms_from_block_instance(rhino_doc, obj).items():
                geoms_transformed = []
                for geom in v:
                    transformed_geom = geom.Duplicate()
                    geoms_transformed.append(transformed_geom)
                if k not in geoms_dict:
                    geoms_dict[k] = geoms_transformed
                else:
                    geoms_dict[k] += geoms_transformed

        else:
            layer_name = get_obj_layer(obj, rhino_doc).FullPath
            geometry = obj.Geometry

            # 블록 인스턴스의 변환 행렬을 적용한 커브 복사본 생성
            transformed_geom = geometry.Duplicate()
            if layer_name not in geoms_dict:
                geoms_dict[layer_name] = [transformed_geom]
            else:
                geoms_dict[layer_name].append(transformed_geom)

    return geoms_dict


## 이수빈
def find_block_definition_from_guid(
    rhino_doc: Rhino.RhinoDoc, block_guid: str
) -> Optional[Rhino.DocObjects.InstanceDefinition]:
    """
    이수빈 작성
    block definition을 GUID로 찾아오는 함수
    """
    for i in range(rhino_doc.InstanceDefinitions.Count):
        idef = rhino_doc.InstanceDefinitions[i]
        if idef.Id == block_guid:
            return idef
    return None


## 이수빈
def geom_dict_to_list(
    geom_dict: Dict[Any, List[geo.GeometryBase]],
) -> List[geo.GeometryBase]:
    """
    이수빈 작성
    Dict 형태 geometry 모음을 단일 리스트로 변환
    """
    result = []
    for geoms in geom_dict.values():
        result.extend(geoms)
    return result


## 이예영
def create_text_entity(
    text: str, position: geo.Point3d, height: float
) -> geo.TextEntity:
    """
    이예영 작성
    텍스트 엔티티 생성 함수
    """
    text_entity = geo.TextEntity()
    text_entity.Text = text
    text_entity.TextHorizontalAlignment = Rhino.DocObjects.TextHorizontalAlignment.Left
    text_entity.Justification = geo.TextJustification.TopLeft
    text_entity.TextHeight = height

    text_entity.Plane = geo.Plane(position, geo.Vector3d.XAxis, geo.Vector3d.YAxis)
    return text_entity


## 이정현
def get_vertices(crv: geo.Curve) -> List[geo.Point3d]:
    """
    이정현 작성
    PolylineCurve 또는 Polyline에서 꼭짓점(Point3d) 리스트 반환
    """
    points = []
    if isinstance(crv, geo.PolylineCurve):
        polyline = crv.ToPolyline()
        points = [pt for pt in polyline]
    elif isinstance(crv, geo.Polyline):
        points = [pt for pt in crv]
    else:
        raise TypeError(
            "지원되지 않는 타입입니다. PolylineCurve 또는 Polyline만 사용하세요."
        )
    return points


## 이정현
def polylinecurve_to_lines(polyline_crv: geo.PolylineCurve) -> List[geo.Line]:
    """
    이정현 작성
    PolylineCurve를 Line의 리스트로 변환
    """
    # 안전장치: PolylineCurve인지 확인한다.
    if not isinstance(polyline_crv, geo.PolylineCurve):
        if isinstance(polyline_crv, geo.LineCurve):
            return [polyline_crv]
        raise TypeError("PolylineCurve 타입만 입력하세요.")
    # PolylineCurve → Polyline으로 변환
    polyline = polyline_crv.ToPolyline()
    # 연속된 점들을 연결해서 Line으로 생성
    lines = []
    for i in range(len(polyline) - 1):
        line = geo.Line(polyline[i], polyline[i + 1])
        lines.append(line)
    return lines


# 이정현
def get_geojson_data(geojson_path):
    """geo json 데이터 불러오기"""
    if not os.path.exists(geojson_path):
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {geojson_path}")

    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


# 이정현
def geojson_to_rhino_geometry(data):
    """Geojson에 있는 정보들을 라이노 데이터로 전환"""
    lines = []

    # GeoJSON features 순회하며 LineString, MultiLineString 처리한다.
    for feature in data["features"]:
        geom_type = feature["geometry"]["type"]
        coords = feature["geometry"]["coordinates"]
        if geom_type == "LineString":
            pts = [geo.Point3d(x, y, 0) for x, y in coords]
            lines.append(geo.PolylineCurve(pts))

        elif geom_type == "MultiLineString":
            for line_coords in coords:
                pts = [geo.Point3d(x, y, 0) for x, y in line_coords]
                lines.append(geo.PolylineCurve(pts))

    return lines


## 정채원
def get_brep_center(brep: geo.Brep) -> geo.Point3d:
    """
    정채원 작성
    Brep의 BoundingBox 중심 좌표 반환
    """
    return brep.GetBoundingBox(True).Center


## 정채원
def get_top_center(brep: geo.Brep) -> geo.Point3d:
    """
    정채원 작성
    Brep의 상단 중앙 지점 반환
    """
    bbox = brep.GetBoundingBox(True)
    return geo.Point3d(
        (bbox.Min.X + bbox.Max.X) / 2, (bbox.Min.Y + bbox.Max.Y) / 2, bbox.Max.Z
    )


## 정채원
def get_bottom_center(brep: geo.Brep) -> geo.Point3d:
    """
    정채원 작성
    Brep의 하단 중앙 지점 반환
    """
    bbox = brep.GetBoundingBox(True)
    return geo.Point3d(
        (bbox.Min.X + bbox.Max.X) / 2, (bbox.Min.Y + bbox.Max.Y) / 2, bbox.Min.Z
    )


## 정채원
def sort_desks_by_y(desks: List[geo.Brep]) -> List[geo.Brep]:
    """
    정채원 작성
    Y값 기준으로 데스크 정렬
    """
    return sorted(desks, key=lambda d: get_brep_center(d).Y)


## 정채원
def sort_by_closest(
    geometries: List[geo.Brep], targets: List[geo.Brep]
) -> List[geo.Brep]:
    """
    정채원 작성
    각 타겟에 대해 가장 가까운 geometry를 찾아 매칭
    """

    def dist(p: geo.Point3d, g: geo.Brep) -> float:
        return p.DistanceTo(get_brep_center(g))

    return [min(geometries, key=lambda g: dist(get_brep_center(t), g)) for t in targets]


# 이예영
def parse_geojson(geom) -> List[geo.PolylineCurve]:
    """
    GeoJSON geometry 데이터를 받아서 Rhino의 PolylineCurve로 변환한다.
    Polygon 또는 MultiPolygon 타입 모두 처리할 수 있다.
    """
    poly_curves = []

    if geom["type"] == "Polygon":
        for ring in geom["coordinates"]:
            points = [geo.Point3d(x, y, 0) for x, y in ring]
            if points[0] != points[-1]:
                points.append(points[0])  # 폐곡선 보장
            polyline = geo.Polyline(points)
            if polyline.IsValid:
                poly_curves.append(geo.PolylineCurve(polyline))

    elif geom["type"] == "MultiPolygon":
        for polygon in geom["coordinates"]:
            for ring in polygon:
                points = [geo.Point3d(x, y, 0) for x, y in ring]
                if points[0] != points[-1]:
                    points.append(points[0])
                polyline = geo.Polyline(points)
                if polyline.IsValid:
                    poly_curves.append(geo.PolylineCurve(polyline))

    return poly_curves


# 이예영
def get_centroid(curve: geo.Curve) -> geo.Point3d:
    """
    주어진 PolylineCurve의 중심점(Point3d)을 계산해서 반환한다.
    텍스트 위치 등에 활용할 수 있다.
    """
    if not curve or not curve.IsValid:
        return None
    bbox = curve.GetBoundingBox(True)
    return bbox.Center


# 이예영
def get_json_path(filename):
    """
    Grasshopper 문서가 저장된 폴더를 기준으로 GeoJSON 파일 경로를 생성한다.
    문서가 저장되지 않은 상태라면 예외를 발생시킨다.
    """
    import scriptcontext as sc

    gh_path = sc.doc.Path
    if gh_path:
        folder = os.path.dirname(gh_path)
        return os.path.join(folder, filename)
    else:
        raise Exception(
            "⚠️ Grasshopper 문서를 먼저 저장하세요. 저장된 경로가 없으면 JSON 파일을 불러올 수 없습니다."
        )


# 이예영
def get_joined_naked_boundary(srf: geo.Surface, tol: float) -> Optional[geo.Curve]:
    """
    주어진 Brep에서 naked edge만 추출하여 하나의 외곽선 Curve로 반환한다.
    실패할 경우 None을 반환한다.
    """
    naked = srf.DuplicateNakedEdgeCurves(True, False)
    if not naked or len(naked) == 0:
        return None

    joined_naked = geo.Curve.JoinCurves(naked, tol)

    if joined_naked and len(joined_naked) > 0:
        return joined_naked[0]
    elif naked and len(naked) > 0:
        return naked[0]
    else:
        return None


# 이예영
def get_srf_center(srf):
    """
    Brep의 면적 중심점을 계산하여 반환한다.
    실패 시 (예: 면적 없음) 원점(0,0,0)을 반환한다.
    """
    amp = geo.AreaMassProperties.Compute(srf)
    return amp.Centroid if amp else geo.Point3d(0, 0, 0)
