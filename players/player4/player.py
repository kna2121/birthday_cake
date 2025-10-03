from shapely import Point, Polygon, LineString
from shapely.ops import split
from shapely.affinity import scale
from typing import Literal

from players.player import Player
from src.cake import Cake
import src.constants as c
import os


class Player4(Player):
    def __init__(self, children: int, cake: Cake, cake_path: str | None) -> None:
        super().__init__(children, cake, cake_path)
        self.ideal_area_per_piece = cake.get_area() / children
        self.total_cuts = children - 1
        self.cake_boundary = cake.exterior_shape.boundary
        self.current_cake_to_cut = cake

        print(f"Ideal area per piece: {self.ideal_area_per_piece}")
        print(cake.get_boundary_points())
        print(self._is_cake_symmetric())


    # def get_cuts(self) -> list[tuple[Point, Point]]:
    #     cuts_res = []
        
    #     # cut until I have piece with 1/n area and another n-1/n area
    #     # then repeat the same with n-1/n piece
    #     for cut in range(1, self.total_cuts+1):
    #         print(f"Making cut {cut}/{self.total_cuts}")
    #         a, b = self._find_proper_cut(self.children - cut)
    #         cuts_res.append((a, b))
    #         self.cake.cut(a, b)
    #         # print(self.current_cake_to_cut.exterior_pieces[0].boundary, self.current_cake_to_cut.exterior_pieces[1].boundary)
    #         self.current_cake_to_cut = max(self.cake.exterior_pieces, key=lambda p: p.area) 
    #         # Comment: it doesn't have to be the second piece, this is only true bc we cut vertically from left to right
    #         print(f"Current cake border: {self.current_cake_to_cut.boundary}")
    #     return cuts_res

    def _cut_rectangle_even(self):
        # find cut through center of cake first
        cake_centroid = self.cake.exterior_shape.centroid
        minx, miny, maxx, maxy = self.cake.exterior_shape.bounds

        cuts = []

        cut_middle = LineString([(cake_centroid.x, miny), (cake_centroid.x, maxy)])
        cuts.append((Point(cut_middle.coords[0]), Point(cut_middle.coords[1])))
        if self.children == 2:
            return cuts
        
        if self.children == 4:
            # cut vertically first, then horizontally on each side
            left_piece, right_piece = split(self.cake.exterior_shape, cut_middle).geoms
            left_centroid = left_piece.centroid
            right_centroid = right_piece.centroid

            cut_left = LineString([(minx, left_centroid.y), (cake_centroid.x, left_centroid.y)])
            cuts.append((Point(cut_left.coords[0]), Point(cut_left.coords[1])))

            cut_right = LineString([(cake_centroid.x, right_centroid.y), (maxx, right_centroid.y)])
            cuts.append((Point(cut_right.coords[0]), Point(cut_right.coords[1])))

            return cuts

    
    def get_cuts(self) -> list[tuple[Point, Point]]:
        piece: Polygon = self.cake.exterior_shape
        if os.path.basename(self.cake_path) == "rectangle.csv":
            return self._cut_rectangle_even()
        print(f"Player 4: Starting DFS for {self.children} children.")
        return self.DFS(piece, self.children)


    def _is_cake_symmetric(self) -> Literal['symmetric_x', 'symmetric_y', 'symmetric_both', False]:
        cake_centroid = self.cake.exterior_shape.centroid
        cake_boundary_points = {Point(co) for co in self.cake.exterior_shape.boundary.coords}

        cake_reflected_x = scale(self.cake.exterior_shape, xfact=1, yfact=-1, origin=(cake_centroid.x, cake_centroid.y))
        cake_reflected_y = scale(self.cake.exterior_shape, xfact=-1, yfact=1, origin=(cake_centroid.x, cake_centroid.y))

        reflected_x_points = {Point(co) for co in cake_reflected_x.boundary.coords}
        reflected_y_points = {Point(co) for co in cake_reflected_y.boundary.coords}

        symmetric_x = reflected_x_points == cake_boundary_points
        symmetric_y = reflected_y_points == cake_boundary_points

        if symmetric_x and symmetric_y:
            return 'symmetric_both'
        elif symmetric_x:
            return 'symmetric_x'
        elif symmetric_y:
            return 'symmetric_y'
        else:
            return False

    def _check_cake_area_ratio(self, piece_done: Polygon, piece_rest: Polygon, pieces_left: int) -> bool:
        piece_done_area_diff = abs(piece_done.area - self.ideal_area_per_piece)
        piece_rest_area_diff = abs(piece_rest.area - self.ideal_area_per_piece * pieces_left)

        return piece_done_area_diff < c.TOL and piece_rest_area_diff < c.TOL


    def _is_piece_area_difference_okay(self, piece_1: Polygon, piece_2: Polygon) -> bool:
        area_diff = abs(piece_1.area - piece_2.area)
        print(f"Area difference between pieces: {area_diff}")
        return area_diff < c.PIECE_SPAN_TOL

    def _find_proper_cut(self, pieces_left_after_cut: int) -> tuple[Point, Point]:
        try_cuts_num = pieces_left_after_cut #3 if pieces_left_after_cut % 2 == 1 else 2

        min_x, min_y, max_x, max_y = self._get_bounds()
        print(f"Min x: {min_x}, Min y: {min_y}, Max x: {max_x}, Max y: {max_y}")

        length_x = max_x - min_x
        cut_length = length_x / (try_cuts_num + 1)

        cake_boundary = self.current_cake_to_cut.exterior_shape.boundary if isinstance(self.current_cake_to_cut, Cake) else self.current_cake_to_cut.boundary

        for x in range(1, try_cuts_num + 1):
            start_p = Point(min_x + x * cut_length, min_y)
            end_p = Point(min_x + x * cut_length, max_y)
            a = cake_boundary.interpolate(cake_boundary.project(start_p))
            b = cake_boundary.interpolate(cake_boundary.project(end_p))
            print(f"Trying cut from {a} to {b}")
            cake_pieces = self._simulate_cut(a, b)

            if self._check_cake_area_ratio(cake_pieces[0], cake_pieces[1], pieces_left_after_cut):
                print(f"Found suitable cut from {a} to {b}")
                return a, b


    def _simulate_cut(self, start_p: Point, end_p: Point) -> list[Polygon]:
        print(f"Simulating cut from {start_p} to {end_p}")
        cake_cpy = self.cake.copy()
        
        cake_cpy.cut(start_p, end_p)
        return cake_cpy.exterior_pieces


    def _get_bounds(self):
        cake_boundary_points = self.current_cake_to_cut.get_boundary_points() if isinstance(self.current_cake_to_cut, Cake) else [Point(c) for c in self.current_cake_to_cut.boundary.coords]
        min_x = min(point.x for point in cake_boundary_points)
        min_y = min(point.y for point in cake_boundary_points)
        max_x = max(point.x for point in cake_boundary_points)
        max_y = max(point.y for point in cake_boundary_points)
        return min_x, min_y, max_x, max_y
