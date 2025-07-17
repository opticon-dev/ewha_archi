import Rhino.Geometry as geo
import math
import random
from typing import List, Optional


class TouristAgent:
    """
    맹진하 작성
    방문자 에이전트: 관광객 경로를 따라 이동 (장애물, 제관 근처 회피)
    """

    def __init__(
        self,
        tourist_start_point: geo.Point3d,
        velocity: float,
        walls: List[geo.Curve],
        touristing_points: List[geo.Point3d],
        ritual_paths: Optional[List[geo.Curve]] = None,
    ):
        self.path = get_tourist_path(
            tourist_start_point, walls, touristing_points, ritual_paths
        )
        self.velocity = velocity
        self.dt = 0.1
        self.distance_moved = 0.0
        self.finished = False
        self.current_position = tourist_start_point if self.path else None

    def update(self, ritual_positions: Optional[List[geo.Point3d]] = None) -> None:
        """
        경로 따라 한 스텝 이동 (제관 근처 회피 포함)
        """
        if not self.path or self.finished:
            return
        curve_length = self.path.GetLength()
        step_distance = self.velocity * self.dt
        self.distance_moved += step_distance
        if self.distance_moved >= curve_length:
            self.distance_moved = curve_length
            self.finished = True
        next_pos = self.path.PointAtLength(self.distance_moved)

        # 제관 회피 (2m 이내 접근 시)
        if ritual_positions:
            for rp in ritual_positions:
                if rp is None:
                    continue
                vec = geo.Vector3d(next_pos - rp)
                dist = vec.Length
                if dist < 2000.0:
                    vec.Unitize()
                    repel = vec * 800.0 * math.exp(-dist / 400.0)
                    next_pos += repel

        self.current_position = next_pos


class RitualAgent:
    """
    맹진하 작성
    제관 에이전트: 고정된 목표 지점을 순서대로 이동
    """

    def __init__(
        self, start: geo.Point3d, goals: List[geo.Point3d], speed: float = 2000.0
    ):
        self.position = start
        self.goals = goals
        self.goal_index = 0
        self.speed = speed
        self.velocity = geo.Vector3d(0, 0, 0)
        self.path = [start]
        self.finished = False
        self.current_position = start

    def current_goal(self) -> Optional[geo.Point3d]:
        return (
            self.goals[self.goal_index] if self.goal_index < len(self.goals) else None
        )

    def update(self) -> None:
        """
        현재 목표 지점으로 한 스텝 이동
        """
        if self.finished:
            return
        goal = self.current_goal()
        if not goal:
            self.finished = True
            return
        direction = geo.Vector3d(goal - self.position)
        distance = direction.Length
        if distance < self.speed * 0.1:
            self.position = goal
            self.path.append(goal)
            self.goal_index += 1
            self.velocity = geo.Vector3d(0, 0, 0)
            self.current_position = goal
            return

        direction.Unitize()
        desired_velocity = direction * self.speed
        force = (desired_velocity - self.velocity) * 0.5
        dt = 0.1
        self.velocity += force * dt
        if self.velocity.Length > self.speed:
            self.velocity.Unitize()
            self.velocity *= self.speed
        move = self.velocity * dt
        self.position += move
        self.path.append(self.position)
        self.current_position = self.position


def get_tourist_path(
    tourist_start_point: geo.Point3d,
    walls: List[geo.Curve],
    touristing_points: List[geo.Point3d],
    ritual_paths: Optional[List[geo.Curve]] = None,
) -> Optional[geo.NurbsCurve]:
    """
    맹진하 작성
    시작점에서 관광 포인트들을 무작위로 방문하며, 벽과 제관 경로를 장애물로 회피하는 경로를 생성
    """
    if ritual_paths is None:
        ritual_paths = []
    all_walls = [crv.ToNurbsCurve() for crv in walls if crv and crv.IsValid]
    for ritual_path in ritual_paths:
        if ritual_path and ritual_path.IsValid:
            all_walls.append(ritual_path)

    waypoints = random.sample(touristing_points, len(touristing_points))
    path = [tourist_start_point]
    position = tourist_start_point

    def is_visible(p1: geo.Point3d, p2: geo.Point3d) -> bool:
        # 두 점 사이 장애물 여부 확인
        line = geo.Line(p1, p2).ToNurbsCurve()
        for wall in all_walls:
            result = geo.Intersect.Intersection.CurveCurve(wall, line, 1.0, 1.0)
            if result and result.Count > 0:
                return False
        return True

    def get_random_point(
        wp: geo.Point3d, position: geo.Point3d
    ) -> Optional[geo.Point3d]:
        # 장애물 회피용 임시 포인트 선택
        direction = geo.Vector3d(wp - position)
        if direction.IsZero:
            return None
        direction.Unitize()
        bounds = geo.BoundingBox([position] + touristing_points)
        candidates = [
            geo.Point3d(
                random.uniform(bounds.Min.X, bounds.Max.X),
                random.uniform(bounds.Min.Y, bounds.Max.Y),
                0,
            )
            for _ in range(100)
        ]
        filtered = [
            pt
            for pt in candidates
            if geo.Vector3d.VectorAngle(direction, geo.Vector3d(pt - position))
            < math.radians(120)
            and is_visible(position, pt)
        ]
        if filtered:
            return min(
                filtered,
                key=lambda pt: pt.DistanceTo(wp) + 0.5 * pt.DistanceTo(position),
            )
        return None

    for wp in waypoints:
        if is_visible(position, wp):
            path.append(wp)
            position = wp
        else:
            for _ in range(3):
                pt = get_random_point(wp, position)
                if pt:
                    path.append(pt)
                    position = pt
                    if is_visible(position, wp):
                        path.append(wp)
                        position = wp
                        break

    return geo.Polyline(path).ToNurbsCurve() if len(path) > 1 else None


def create_ritual_path(ritual_goals: List[geo.Point3d]) -> Optional[geo.NurbsCurve]:
    """
    맹진하 작성
    제관 목표 포인트들을 Polyline → Curve로 변환
    """
    return geo.Polyline(ritual_goals).ToNurbsCurve() if ritual_goals else None


def make_circle(
    position: Optional[geo.Point3d], radius: float = 500.0
) -> Optional[geo.NurbsCurve]:
    """
    맹진하 작성
    주어진 위치에 반지름 r 원 생성 (에이전트 시각화용)
    """
    if position is None:
        return None
    plane = geo.Plane(position, geo.Vector3d.ZAxis)
    circle = geo.Circle(plane, radius)
    return circle.ToNurbsCurve()
