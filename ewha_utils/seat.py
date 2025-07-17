import Rhino.Geometry as geo
from .raw_utils import *
import rhinoscriptsyntax as rs
import math
import datetime


def get_geoms_in_layer(layer_name):
    _ids = rs.ObjectsByLayer(layer_name)
    return [Rhino.RhinoDoc.ActiveDoc.Objects.Find(_id).Geometry for _id in _ids]


def get_door_center(door, eye_height=1400):
    """문 중심 좌표 반환 (기본 눈높이 1400mm)"""
    u_domain = door.Domain(0)
    v_domain = door.Domain(1)
    u_mid = (u_domain.T0 + u_domain.T1) / 2
    v_mid = (v_domain.T0 + v_domain.T1) / 2
    pt = door.PointAt(u_mid, v_mid)
    return geo.Point3d(pt.X, pt.Y, eye_height)


def get_door_inside_vector(door, room):
    """문이 바라보는 실내 방향 벡터 계산"""
    vec = door.NormalAt(0.5, 0.5)
    center_pt = get_door_center(door)
    test_pt = center_pt + vec * 100
    if not room.IsPointInside(test_pt, 0.001, True):
        vec.Reverse()
    return vec


def rotate_vector(vec, angle):
    """벡터를 Z축 기준으로 회전"""
    angle_rad = math.radians(angle)
    vec_copy = geo.Vector3d(vec)
    vec_copy.Rotate(angle_rad, geo.Vector3d.ZAxis)
    return vec_copy


def get_rays(origin, base_vector, angle=180, count=40, z_height=None):
    """일정 각도 범위로 퍼지는 시야선(ray) 생성"""
    rays = []
    if z_height is not None:
        origin = geo.Point3d(origin.X, origin.Y, z_height)

    min_angle = -angle
    angle_step = angle * 2 / (count - 1)

    for i in range(count):
        rotate_angle = min_angle + i * angle_step
        rotated_vec = rotate_vector(base_vector, rotate_angle)
        target_pt = origin + rotated_vec * 8000
        seg = geo.LineCurve(origin, target_pt)
        ray = Ray(origin, rotated_vec, seg)
        rays.append(ray)
    return rays


def ensure_surface(obj):
    """Surface 또는 Brep의 Face를 surface로 변환"""
    if isinstance(obj, geo.Surface):
        return obj
    elif isinstance(obj, geo.Brep) and obj.Faces.Count > 0:
        return obj.Faces[0]
    return None


def get_crv_surface_intersection_point(crv, surface):
    """Curve와 Surface 간 첫 번째 교차점 반환"""
    face = surface.Faces[0] if isinstance(surface, geo.Brep) else surface
    tol = 0.001
    events = geo.Intersect.Intersection.CurveSurface(crv, face, tol, tol)
    return events[0].PointA if events and events.Count > 0 else None


# ========== 태양 벡터 계산 함수 ========== #
def get_sun_vector(latitude=37.5, longitude=127.0, dt=None):
    if dt is None:
        dt = datetime.datetime(2025, 5, 29, 15, 0, 0)

    day_of_year = dt.timetuple().tm_yday
    hour = dt.hour + dt.minute / 60.0
    decl = -23.44 * math.cos(math.radians(360 / 365 * (day_of_year + 10)))
    hour_angle = 15 * (hour - 12)

    altitude = math.degrees(
        math.asin(
            math.sin(math.radians(latitude)) * math.sin(math.radians(decl))
            + math.cos(math.radians(latitude))
            * math.cos(math.radians(decl))
            * math.cos(math.radians(hour_angle))
        )
    )
    azimuth = math.degrees(
        math.atan2(
            -math.sin(math.radians(hour_angle)),
            math.tan(math.radians(decl)) * math.cos(math.radians(latitude))
            - math.sin(math.radians(latitude)) * math.cos(math.radians(hour_angle)),
        )
    )

    alt_rad = math.radians(altitude)
    azi_rad = math.radians(azimuth)
    x = math.cos(alt_rad) * math.sin(azi_rad)
    y = math.cos(alt_rad) * math.cos(azi_rad)
    z = math.sin(alt_rad)
    return geo.Vector3d(x, y, z) * -1


# ========== 창문 표면 샘플 포인트 추출 ========== #
def get_window_sample_points(windows, count_u=5, count_v=10):
    points = []
    for win in windows:
        if hasattr(win, "Faces"):
            for face in win.Faces:
                u_domain = face.Domain(0)
                v_domain = face.Domain(1)
                for i in range(count_u):
                    for j in range(count_v):
                        u_ratio = i / float(count_u - 1) if count_u > 1 else 0.5
                        v_ratio = j / float(count_v - 1) if count_v > 1 else 0.5
                        u = u_domain.ParameterAt(u_ratio)
                        v = v_domain.ParameterAt(v_ratio)
                        pt = face.PointAt(u, v)
                        points.append(pt)
    return points


def get_all_rays(window_geos):
    # ========== 시뮬레이션 실행 ========== #
    sun_vec = get_sun_vector()
    ray_origins = get_window_sample_points(window_geos, count_u=3, count_v=5)

    curves = []

    for origin in ray_origins:
        ray = geo.Line(origin, origin + sun_vec * 3000)
        curve = ray.ToNurbsCurve()
        curves.append(curve)
    return curves


class Seat:
    def __init__(self, index, desk, screen, chair):
        self.index = index
        self.desk = desk
        self.screen = screen
        self.chair = chair
        self.position = get_brep_center(desk)
        self.bbox = desk.GetBoundingBox(True).ToBrep()
        self.ventilation_score = 0.0
        self.movement_score = None
        self.movement_weight = 1

        self.sunlight_norm_score = None
        self.sunlight_hit_rays = []
        self.sunlight_hit_points = []
        self.sunlight_score = []

        self.privacy_all_rays = []
        self.privacy_hit_points = []
        self.privacy_hit_rays = []
        self.privacy_score = None
        self.privacy_norm_score = None

        self.screen_face = None
        self.screen_center_z = self.get_screen_center_z()
        self.total_score = None

    def set_screen_face(self, screen_face: geo.BrepFace):
        self.screen_face = screen_face

    # 창문들과의 최소 거리 기반 환기 점수 계산
    def update_ventilation_score(self, windows):
        min_dist = float("inf")
        for win in windows:
            if hasattr(win, "Faces"):
                for face in win.Faces:
                    success, u, v = face.ClosestPoint(self.position)
                    if success:
                        pt = face.PointAt(u, v)
                        dist = self.position.DistanceTo(pt)
                        if dist < min_dist:
                            min_dist = dist
        self.ventilation_score = 10000.0 / (min_dist + 1.0)

    def evaluate_movement(self, commons, weights):
        total_score = 0
        for obj, weight in zip(commons, weights):
            obj_center = get_brep_center(obj)
            dist = self.position.DistanceTo(obj_center)
            if dist == 0:
                continue
            score = weight / dist
            total_score += score
        self.movement_score = total_score

    def get_screen_center_z(self):
        bbox = self.screen.GetBoundingBox(True)
        return (bbox.Min.Z + bbox.Max.Z) / 2

    def evaluate_privacy(self, rays_base_vectors, obstacles, seat_index=None):
        if not self.screen_face:
            raise ValueError("screen face must be set before evalutate")
        distances = []

        for base_origin, base_vector, angle in rays_base_vectors:
            test_z = self.screen_center_z
            rays = get_rays(
                base_origin, base_vector, angle=angle, count=100, z_height=test_z
            )
            self.privacy_all_rays.extend([ray.seg.ToNurbsCurve() for ray in rays])

            for ray in rays:
                intersection_pt = get_crv_surface_intersection_point(
                    ray.seg, self.screen_face
                )
                if not intersection_pt:
                    continue

                success, u, v = self.screen_face.ClosestPoint(intersection_pt)
                if not success:
                    continue

                normal = self.screen_face.NormalAt(u, v)
                if geo.Vector3d.Multiply(ray.vec, normal) < 0:
                    continue

                dist_to_screen = base_origin.DistanceTo(intersection_pt)
                blocked = False

                for obs in obstacles:
                    if obs == self.screen_face:
                        continue
                    obs_pt = get_crv_surface_intersection_point(ray.seg, obs)
                    if obs_pt and base_origin.DistanceTo(obs_pt) < dist_to_screen:
                        blocked = True
                        break

                if blocked:
                    continue

                self.privacy_hit_rays.append(ray.seg.ToNurbsCurve())
                self.privacy_hit_points.append(intersection_pt)
                distances.append(ray.pt.DistanceTo(intersection_pt))

        num_hits = len(distances)
        total_distance = sum(distances)

        self.privacy_score = 10000.0 if num_hits == 0 else (total_distance / num_hits)

    def evaluate_sunlight(self, rays, obstacles):
        def check_ray_hit(curve):
            success, result = geo.Intersect.Intersection.CurveBrep(
                curve, self.bbox, 0.001, 0.001
            )
            if success and result and len(result) > 0:
                for t in result:
                    pt = curve.PointAt(t)
                    self.sunlight_hit_points.append(pt)
                return True
            return False

        for ray in rays:
            if check_ray_hit(ray):
                blocked = False
                for obs in obstacles:
                    _, params = geo.Intersect.Intersection.CurveBrep(ray, obs, 0.1, 0.1)
                    if params and len(params) > 0:
                        blocked = True
                        break
                if not blocked:
                    self.sunlight_hit_rays.append(ray)
        self.sunlight_score = len(self.sunlight_hit_rays)

    def set_sunlight_norm_score(self, sunlight_norm_score):
        self.sunlight_norm_score = sunlight_norm_score

    def set_privacy_norm_score(self, privacy_norm_score):
        self.privacy_norm_score = privacy_norm_score

    def compute_total_score(self, w_privacy, w_sunlight, w_movement, w_ventilation):
        total_score = (
            w_privacy * self.privacy_norm_score
            + w_sunlight * self.sunlight_norm_score
            + self.movement_score * w_movement
            + self.ventilation_score * w_ventilation
        )
        self.total_score = total_score
        return total_score

    def get_bottom_center(self):
        return get_bottom_center(self.desk)

    def get_top_center(self):
        return get_top_center(self.desk)


class Ray:
    def __init__(self, pt, vec, seg):
        self.pt = pt
        self.vec = vec
        self.seg = seg


class Visualizer:
    def __init__(self, mode: str, seats: List[Seat]):
        self.mode = mode
        self.seats = seats

    def visualize(self):
        if self.mode == "Vent":
            return self.visualize_vent()
        elif self.mode == "Movement":
            return self.visualize_movement()
        elif self.mode == "Privacy":
            return self.visualize_privacy()
        elif self.mode == "Sunlight":
            return self.visualize_sunlight()

    def visualize_movement(self):
        # 슬라브
        slab_ids = rs.ObjectsByLayer("Slab")
        slab_list = [
            Rhino.RhinoDoc.ActiveDoc.Objects.Find(id).Geometry for id in slab_ids
        ]
        slab = slab_list[0] if slab_list else None

        # 공용 요소 (6개 레이어)
        commons_layers = [
            "Commons_CritDesk",
            "Commons_TrashBin",
            "Commons_Fridge",
            "Commons_Printer",
            "Commons_Door",
            "Commons_Basin",
        ]

        commons_geos = []
        for layer in commons_layers:
            commons_geos += get_geoms_in_layer(layer)

        # ========== 사용자 설정값 ========== #
        x_count = 20
        y_count = 40
        extrude_height = 510

        # ========== 슬라브 영역에 그리드 포인트 생성 ========== #
        def generate_grid_on_slab(slab, x_count, y_count):
            bbox = slab.GetBoundingBox(True)
            min_pt = bbox.Min
            max_pt = bbox.Max
            x_step = (max_pt.X - min_pt.X) / (x_count - 1)
            y_step = (max_pt.Y - min_pt.Y) / (y_count - 1)

            grid_pts = []
            for i in range(x_count):
                for j in range(y_count):
                    pt = geo.Point3d(
                        min_pt.X + i * x_step, min_pt.Y + j * y_step, min_pt.Z
                    )
                    grid_pts.append(pt)
            return grid_pts, x_step, y_step

        # ========== 중심 좌표 기준 사각형 곡선 생성 ========== #
        def create_rect_from_center_point(center_point, size_x, size_y):
            dx = size_x / 2
            dy = size_y / 2
            pt1 = center_point + geo.Vector3d(-dx, -dy, 0)
            pt2 = center_point + geo.Vector3d(dx, -dy, 0)
            pt3 = center_point + geo.Vector3d(dx, dy, 0)
            pt4 = center_point + geo.Vector3d(-dx, dy, 0)
            return geo.PolylineCurve([pt1, pt2, pt3, pt4, pt1])

        # ========== 가장 가까운 공용 요소까지의 거리 반환 ========== #
        def get_distance_to_nearest_common(pt, commons_centers):
            return (
                min([pt.DistanceTo(center) for center in commons_centers])
                if commons_centers
                else 0
            )

        # ========== 거리값을 색상으로 변환 (가까울수록 빨강) ========== #
        def distance_to_color(dist, min_d, max_d):
            t = (dist - min_d) / (max_d - min_d) if max_d > min_d else 0
            t = max(0, min(t, 1))
            t = 1 - t  # 가까울수록 빨간색

            r = 255
            g = int(255 * (1 - t))
            b = int(100 * (1 - t))
            return Color.FromArgb(r, g, b)

        # ========== 실행 ========== #
        grid_points, step_x, step_y = generate_grid_on_slab(slab, x_count, y_count)
        commons_centers = [get_brep_center(g) for g in commons_geos]

        distances = [
            get_distance_to_nearest_common(pt, commons_centers) for pt in grid_points
        ]
        min_d = min(distances)
        max_d = max(distances)

        extrusions = []
        colors = []

        for pt, dist in zip(grid_points, distances):
            rect = create_rect_from_center_point(pt, step_x, step_y)
            extrude = geo.Extrusion.Create(rect, extrude_height, True)
            color = distance_to_color(dist, min_d, max_d)
            extrusions.append(extrude)
            colors.append(color)

        return extrusions, colors

    def visualize_sunlight(self):
        # ========== 초기화 ========== #
        all_rays = []  # 모든 ray (회색)
        all_colors = []  # 모든 ray의 색상
        valid_pipes = []  # 유효한 hit-ray에 대한 pipe
        valid_colors = []  # pipe 색상 (빨간색)

        r = 10.0  # pipe 반지름

        # ========== 모델 정확도 설정 ========== #
        abs_tol = Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance
        ang_tol = Rhino.RhinoDoc.ActiveDoc.ModelAngleToleranceRadians

        # ========== 출력 처리 ========== #
        # 모든 ray → 회색 NurbsCurve로 시각화
        all_rays = []
        for seat in self.seats:
            all_rays += seat.sunlight_hit_rays
        sun_norm_scores = [seat.sunlight_score for seat in self.seats]
        all_colors = [Color.FromArgb(220, 220, 220) for _ in sun_norm_scores]

        # 유효 ray → pipe로 시각화 (빨간색)
        for crv in all_rays:
            try:
                pipes = geo.Brep.CreatePipe(
                    crv, r, True, geo.PipeCapMode.Round, True, abs_tol, ang_tol
                )
                if pipes:
                    valid_pipes.extend(pipes)
                    valid_colors.extend([Color.FromArgb(255, 50, 50) for _ in pipes])
                else:
                    print("❌ Pipe 생성 실패:", crv)
            except Exception as ex:
                print("⚠️ 예외 발생:", ex)
        return valid_pipes, all_colors

    def visualize_privacy(self):
        score_dots = []
        hit_points = []
        hit_rays = []

        # 점수 TextDot 생성
        for seat in self.seats:
            pt = seat.position
            label = str(round(seat.privacy_score, 2))
            dot = geo.TextDot(
                label, geo.Point3d(pt.X, pt.Y, pt.Z + 700)
            )  # 좌석 위에 띄우기
            score_dots.append(dot)
            hit_points.append(seat.privacy_hit_points)
            hit_rays.append(seat.privacy_hit_rays)

        return score_dots, hit_points, hit_rays

    def visualize_vent(self):
        # ========== 점수 순위 기반 색상 지정 (11단계 색상 팔레트) ========== #
        def assign_ranked_colors(scores):
            palette = [
                Color.FromArgb(8, 29, 88),
                Color.FromArgb(37, 52, 148),
                Color.FromArgb(34, 94, 168),
                Color.FromArgb(29, 145, 192),
                Color.FromArgb(65, 182, 196),
                Color.FromArgb(127, 205, 187),
                Color.FromArgb(199, 233, 180),
                Color.FromArgb(237, 248, 177),
                Color.FromArgb(255, 255, 204),
                Color.FromArgb(255, 237, 160),
                Color.FromArgb(254, 217, 118),
            ][::-1]

            ranked = sorted(enumerate(scores), key=lambda x: x[1])
            colors = [None] * len(scores)
            for i, (idx, _) in enumerate(ranked):
                colors[idx] = palette[i]
            return colors

        # ========== 데스크-의자 영역 바닥 Extrusion 생성 ========== #
        def create_ground_patch(desk, chair, base_height=10):
            desk_box = desk.GetBoundingBox(True)
            chair_box = chair.GetBoundingBox(True)
            union_box = geo.BoundingBox.Union(desk_box, chair_box)

            base_pt = geo.Point3d(union_box.Min.X, union_box.Min.Y, union_box.Min.Z)
            base_plane = geo.Plane(base_pt, geo.Vector3d.ZAxis)

            width = union_box.Max.X - union_box.Min.X
            depth = union_box.Max.Y - union_box.Min.Y

            rect = geo.Rectangle3d(base_plane, width, depth)
            curve = rect.ToNurbsCurve()

            return geo.Extrusion.Create(curve, base_height, True)

        # ========== 실행 및 출력 ========== #

        vent_scores = [seat.ventilation_score for seat in self.seats]
        colors = assign_ranked_colors(vent_scores)

        extrusions = []  # Extrusion 패치
        colors = []  # 색상

        for seat, color in zip(self.seats, colors):
            extrusions.append(create_ground_patch(seat.desk, seat.chair))
            colors.append(color)
        return extrusions, colors
