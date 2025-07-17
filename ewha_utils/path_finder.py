import Rhino.Geometry as geo
import heapq
import ewha_utils.raw_utils as raw_utils


class PathFinder:
    """
    이정현 작성
    도로 중심선 데이터(PolylineCurve)를 입력받아
    각 라인을 노드-엣지 그래프로 변환하고,
    설정한 시작점과 끝점 간의 최단 경로를 Dijkstra 알고리즘으로 탐색하는 클래스.
    """

    def __init__(self, road_crvs):
        """
        이정현 작성
        클래스 초기화 함수
        """
        all_lines = []
        for crv in road_crvs:
            all_lines += raw_utils.polylinecurve_to_lines(crv)
        all_points = []
        for crv in road_crvs:
            all_points += raw_utils.get_vertices(crv)
        self.unique_points, self.adjacency = self.analyze_road_data(
            all_points, all_lines
        )

    def process(self, start_pt, end_pt):
        """
        이정현 작성
        data는 ngii.co.kr(국토정보부)에서 다운받은 shp의 geojson의 도로 중심선 데이터
        혹은 임의로 작성된 도로 데이터
        최단거리를 찾는 코드
        road_points [geo.Point3d] : 중심선 데이터의 절점들(Node)
        road_lines [geo.Line] : 중심선 데이터의 연결선들(Edge)
        start_pt : 시작점 : 꼭 road_points 일 필요는 없음
        end_pt : 끝점 : 꼭 road_points 일 필요는 없음
        """

        def closest_point_index(pt):
            """
            이정현 작성
            pt에서 unique_points 리스트 내 가장 가까운 점의 인덱스를 반환
            """
            dists = [pt.DistanceTo(up) for up in self.unique_points]
            return dists.index(min(dists))

        # 시작점과 도착점에 대한 가장 가까운 도로 상의 점을 분석
        start_idx = closest_point_index(start_pt)
        end_idx = closest_point_index(end_pt)
        # 시작 인덱스와 끝 인덱스를 기반으로 최단 경로를 계산
        return self.get_path(start_idx, end_idx)

    def analyze_road_data(self, road_points, road_lines):
        """
        이정현 작성
        도로데이터 그래프로 생성
        """

        def rounded_key(pt, precision=4):
            """
            이정현 작성
            중복 점 제거를 위한 허용오차 설정
            """
            return (
                round(pt.X, precision),
                round(pt.Y, precision),
                round(pt.Z, precision),
            )

        unique_points = []  # 중복 제거된 좌표 리스트 형성
        point_idx_map = {}  # 좌표 키 → 인덱스 매핑
        # 1. 중복 점 제거
        for pt in road_points:
            key = rounded_key(pt)
            if key not in point_idx_map:
                point_idx_map[key] = len(unique_points)
                unique_points.append(pt)
        # 2. 인접 리스트 초기화
        adjacency = {i: [] for i in range(len(unique_points))}
        # 3. 도로(Line)를 기반으로 노드 간 연결 정보 생성
        for line in road_lines:
            key_from = rounded_key(line.From)
            key_to = rounded_key(line.To)
            i1 = point_idx_map.get(key_from, -1)
            i2 = point_idx_map.get(key_to, -1)
            if i1 != -1 and i2 != -1:
                length = line.Length
                adjacency[i1].append((i2, length))  # 점끼리 양방향으로 연결
                adjacency[i2].append((i1, length))
        return unique_points, adjacency

    def get_path(self, start_idx, end_idx):
        """
        이정현 작성
        start_idx에서 end_idx까지의 최단 경로 기반 PolylineCurve 반환
        """
        dist = {
            i: float("inf") for i in self.adjacency
        }  # 모든 노드까지의 거리 초기화 (무한대)
        prev = {i: None for i in self.adjacency}  # 경로 추적을 위한 이전 노드 저장
        dist[start_idx] = 0
        queue = [(0, start_idx)]  # 시작 노드 지정 (우선순위 큐)
        while queue:
            current_dist, u = heapq.heappop(queue)
            if current_dist > dist[u]:
                continue  # 더 짧은 거리로 이미 방문한 경우 생략
            if u == end_idx:
                break  # 도착점에 도달
            for v, weight in self.adjacency[u]:  # 인접 노드 탐색
                alt = dist[u] + weight
                if alt < dist[v]:  # 더 짧은 경로 발견 시 업데이트
                    dist[v] = alt
                    prev[v] = u
                    heapq.heappush(queue, (alt, v))
        path_indices = []
        u = end_idx
        if prev[u] is not None or u == start_idx:
            while u is not None:
                path_indices.insert(0, u)
                u = prev[u]
        else:
            return None, None  # 경로 없음
        path_points = [self.unique_points[i] for i in path_indices]
        polyline = geo.Polyline(path_points)
        return geo.PolylineCurve(polyline)
