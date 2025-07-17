import Rhino
import Rhino.Geometry as geo
from typing import List, Optional, Tuple
from System.Drawing import Color

import ewha_utils

# pfs = path friendliness score (동선 편리성 점수)

# ---------- 복도폭 계산 함수 ----------


def get_corridor_width_at_point(
    pt: geo.Point3d, boundary_crvs: List[geo.Curve], search_length: float = 100000
) -> Optional[float]:
    """
    권유진 작성
    주어진 점에서 복도폭 계산
    기준점에서 수평, 수직 방향으로 선을 쏘아 양쪽 경계와의 거리를 계산.
    짧은 쪽 폭을 복도 폭으로 사용.
    """
    corridor_boundary_of_pt = None
    for crv in boundary_crvs:
        if ewha_utils.is_pt_inside(pt, crv):
            corridor_boundary_of_pt = crv
            break

    if corridor_boundary_of_pt is None:
        print(f"[!] 점이 어떤 복도에도 속하지 않음: {pt}")
        return None

    def get_width_by_directions(vec: geo.Vector3d) -> Optional[float]:
        """주어진 방향 벡터 기준 양방향으로 거리 측정"""
        vec.Unitize()
        ray1 = geo.LineCurve(pt, pt + vec * search_length)
        ray2 = geo.LineCurve(pt, pt - vec * search_length)
        intersections = []
        for ray in [ray1, ray2]:
            result = geo.Intersect.Intersection.CurveCurve(
                corridor_boundary_of_pt, ray, 0.1, 0.1
            )
            if result:
                closest = min(result, key=lambda r: pt.DistanceTo(r.PointA))
                intersections.append(closest.PointA)
        return (
            pt.DistanceTo(intersections[0]) + pt.DistanceTo(intersections[1])
            if len(intersections) == 2
            else None
        )

    x_width = get_width_by_directions(geo.Vector3d(1, 0, 0))
    y_width = get_width_by_directions(geo.Vector3d(0, 1, 0))
    widths = [w for w in [x_width, y_width] if w is not None]
    if not widths:
        print(f"[!] 복도폭 측정 실패 @ {pt}")
        return None
    return min(widths)


# ---------- 동선 편리성 항목별 점수 계산 함수들 ----------


def get_corridor_score(
    width: Optional[float],
    min_w: float = 1000,
    max_w: float = 4000,
    perfect: float = 2500,
) -> float:
    """
    권유진 작성
    1. 복도폭 점수 계산 (1000~4000mm 기준, 2500mm 최적)
    - 최소폭 이하 또는 최대폭 이상은 0점
    - 적정폭일 때 100점
    - 그 사이일 경우 비례 점수
    """
    if width is None:
        return 0
    if width < min_w or width > max_w:
        return 0
    elif width <= perfect:
        return round((width - min_w) / (perfect - min_w) * 100)
    else:
        return round((max_w - width) / (max_w - perfect) * 100)


def calculate_shelter_score(
    pt: geo.Point3d,
    shelter_pts: List[geo.Point3d],
    max_shelters: int = 15,
    search_radius: float = 10000,
) -> Tuple[float, float, float]:
    """
    권유진 작성
    2. 쉼터 점수 계산: 거리 + 빈도
    - 거리: 가장 가까운 쉼터까지의 거리 기반 점수
    - 빈도: 반경 내 쉼터 개수 비율 점수
    - 거리*0.6, 빈도*0.4로 가중 평균
    """
    if not shelter_pts:
        return 0, 0, 0

    dist_pts = min([pt.DistanceTo(sp) for sp in shelter_pts], default=float("inf"))
    dist_score = (
        max(0, (15000 - dist_pts) / 15000 * 100) if dist_pts != float("inf") else 0
    )
    count_shelter_pts = sum(
        1 for sp in shelter_pts if pt.DistanceTo(sp) <= search_radius
    )
    freq_score = count_shelter_pts / max_shelters * 100
    return dist_score * 0.6 + freq_score * 0.4, dist_score, freq_score


def calculate_obstacle_score(
    pt: geo.Point3d, obstacle_pts: List[geo.Point3d], safe_radius: float = 2000
) -> float:
    """
    권유진 작성
    3. 장애물 점수 계산: 반경 내 개수
    - 기준 반경 내 장애물 개수에 따라 점수 부여 (최대 3개)
    - 장애물이 적을수록 높은 점수
    """
    if not obstacle_pts:
        return 100
    count_obst = sum(1 for op in obstacle_pts if pt.DistanceTo(op) < safe_radius)
    return max(0, (3 - count_obst) / 3 * 100)


def calculate_light_score(
    pt: geo.Point3d, window_crvs: List[geo.Curve], light_radius: float = 10000
) -> Tuple[float, float, float, float, float]:
    """
    권유진 작성
    4. 자연광 점수 계산: 길이, 거리
    - 길이: 10m 반경 내 창문 길이 총합 기반 점수
    - 거리: 가장 가까운 창문까지의 거리 기반 점수
    - 길이*0.6, 거리*0.4로 가중 평균
    """
    if not window_crvs:
        return 0, 0, 0, 0, 0, float("inf"), 0
    relevant_windows = [
        crv
        for crv in window_crvs
        if ewha_utils.get_dist_from_pt_crv(pt, crv) <= light_radius
    ]
    total_length = sum(crv.GetLength() for crv in relevant_windows)
    length_score = min(total_length / 10000.0, 1.0) * 100
    dist_light = min(
        [ewha_utils.get_dist_from_pt_crv(pt, crv) for crv in window_crvs],
        default=float("inf"),
    )
    dist_score_light = (
        max(0, (8000 - dist_light) / 8000 * 100) if dist_light != float("inf") else 0
    )
    return (
        length_score * 0.6 + dist_score_light * 0.4,
        total_length,
        length_score,
        dist_light,
        dist_score_light,
    )


# ---------- 복도 클래스 ----------


class Corridor:
    def __init__(self, curve, boundary_crvs):
        self.curve = curve
        self.boundary_crvs = boundary_crvs
        self.points = ewha_utils.raw_utils.generate_points_in_curve(curve)
        self.scores = []
        self.spheres = []
        self.colors = []

    # 복도폭 구하기
    def get_corridor_width(self, pt):
        return ewha_utils.pfs.get_corridor_width_at_point(pt, self.boundary_crvs)

    # 항목별 점수 산정 후 최종 점수 계산
    def calculate_scores(self, shelter_pts, obstacle_pts, window_crvs):
        for pt in self.points:
            width = self.get_corridor_width(pt)
            s_corridor = ewha_utils.pfs.get_corridor_score(width)
            s_rest, dist_score, freq_score = ewha_utils.pfs.calculate_shelter_score(
                pt, shelter_pts
            )
            s_obst = ewha_utils.pfs.calculate_obstacle_score(pt, obstacle_pts)
            s_light, total_length, length_score, dist_light, dist_score_light = (
                ewha_utils.pfs.calculate_light_score(pt, window_crvs)
            )

            total_score = round(
                s_corridor * 0.2 + s_rest * 0.4 + s_obst * 0.1 + s_light * 0.3
            )
            self.scores.append(total_score)

            # 상세 점수 출력
            print(f"[{pt}]")
            print(f"  - 복도폭: {width:.1f} mm")
            print(f"  - 복도폭 점수: {s_corridor:.1f}")
            print(
                f"  - 쉼터 점수: 거리 {dist_score:.1f}, 빈도 {freq_score:.1f}, 총점 {s_rest:.1f}"
            )
            print(f"  - 장애물 점수: {s_obst:.1f}")
            print(f"  - 자연광 점수:")
            print(f"     - 창문 길이: {total_length:.1f} mm, 점수: {length_score:.1f}")
            print(f"     - 거리: {dist_light:.1f} mm, 점수: {dist_score_light:.1f}")
            print(f"     - 총점: {s_light:.1f}")
            print(f"  => 최종 점수: {total_score:.1f}")
            print("-" * 60)

    # 도형으로 시각화
    def visualize(self, radius=350):
        for pt, score in zip(self.points, self.scores):
            self.spheres.append(geo.Sphere(pt, radius).ToBrep())
            self.colors.append(self.score_to_color(score))

    # 점수에 따라 색깔 부여(초록색=편리한 동선, 빨간색=불편한 동선)
    def score_to_color(self, score):
        r = int(min(255, max(0, 255 * (100 - score) / 50)))
        g = int(min(255, max(0, 255 * score / 50)))
        return Color.FromArgb(r, g, 0)
