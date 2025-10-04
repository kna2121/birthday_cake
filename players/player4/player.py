from shapely import Point, Polygon, LineString
from shapely.ops import split, linemerge
from shapely.affinity import scale
from typing import Literal

from players.player import Player
from src.cake import Cake
import src.constants as c
import os
from math import floor, ceil


class Player4(Player):
    def __init__(self, children: int, cake: Cake, cake_path: str | None) -> None:
        super().__init__(children, cake, cake_path)
        self.ideal_area_per_piece: float = cake.get_area() / children
        self.total_cuts: int = children - 1
        self.cake_crust: LineString = cake.exterior_shape.boundary
        self.current_cake_to_cut = cake

        # print(f"Ideal area per piece: {self.ideal_area_per_piece}")
        print(cake.get_boundary_points())
        print(cake.exterior_shape)
        print(self._is_cake_symmetric())

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
    
    def _cut_rectangle(self, current_cake: Polygon, children: int):
        print(f"cutting rectangle with {children} children remaining.")
        cut_sequence: list[tuple[Point, Point]] = []

        # base case of recursion 
        if children == 1:
            return cut_sequence
        
        minx, miny, maxx, maxy = self._get_bounds(self.cake)
        length = maxx - minx

        minx_curr, miny_curr, maxx_curr, maxy_curr = self._get_bounds(current_cake)
        print(f"Current cake bounds: minx {minx_curr}, miny {miny_curr}, maxx {maxx_curr}, maxy {maxy_curr}")

        current_crust = linemerge(self.cake_crust.intersection(current_cake.boundary))
        cake_centroid = self.cake.exterior_shape.centroid
        print(f"current crust: {current_crust}")
        # If two (or generally even number of) children left, then cut into two pieces with both having same area
        # either horizontal cut or angular (if 8 children total)
        if children % 2 == 0:
            # find out how much crust is left
            # get the intersection of current cake and 
            # find perfect cut to split crust
            if current_crust == self.cake_crust:    # make sure points in right order
                # cut vertical in middle
                print("full crust left, cutting vertically in middle")
                next_cut = LineString([(cake_centroid.x, miny), (cake_centroid.x, maxy)])
                
            else:
                # get length of crust
                crust_len_per_piece = current_crust.length / children
                # cut according to size of crust and connect to centroid
                from_p = current_crust.interpolate(crust_len_per_piece)
                # point where line interects a non-crust opposite side
                to_p = cake_centroid
                next_cut = LineString([from_p, to_p])
                print(f"next cut before check: {next_cut}")
                if not to_p.intersects(current_crust):
                    print("cut doesn't intersect cake, adjusting")
                    if from_p.x < cake_centroid.x:
                        to_p = Point(maxx_curr, cake_centroid.y)
                    else:
                        to_p = Point(minx_curr, cake_centroid.y)
                    next_cut = LineString([from_p, to_p])
                    # print(f"Next cut after adjustment: {next_cut}")

            print(f"Next cut here: {next_cut}")
            children_left = children / 2
            split_pieces = split(current_cake, next_cut)
            subpiece1, subpiece2 = split_pieces.geoms
            cuts1 = self._cut_rectangle(subpiece1, children_left)
            cuts2 = self._cut_rectangle(subpiece2, children_left)
        
        # If children left is 3 and piece is not fully surrounded by crust, then do following
        # go from one point in line and move along the curst thirdway and connect this point to center point on other side (not crust)
        # do same from other side

        # else if children odd then divide into two pieces, 1 piece for even number of children, 1 for odd number of children
        else:
            children_left = [floor(children/2), ceil(children/2)]
            # cut cake vertically in two pieces if still full crust
            if current_crust == self.cake_crust:    # make sure points in right order
                # cut vertical in middle
                
                start_distance = self.cake_crust.project(Point(minx, miny))
                # print(f"children left: {children_left}, length: {length}")
                # print(f"Start distance on crust: {start_distance}, go to {start_distance + (children_left[0] / children) * length}")
                from_p = current_crust.interpolate(start_distance + (children_left[0] / children) * length)
                to_p = (from_p.x, maxy)
                next_cut = LineString([from_p, to_p])

            else:
                # get length of crust
                crust_len_per_piece = current_crust.length / children 
                # cut according to size of crust and connect to centroid
                from_p = current_crust.interpolate(crust_len_per_piece * children_left[0])
                to_p = cake_centroid
                next_cut = LineString([from_p, to_p])
                if not to_p.intersects(current_crust):
                    print("cut doesn't intersect cake, adjusting")
                    if from_p.x < cake_centroid.x:
                        to_p = Point(maxx_curr, cake_centroid.y)
                    else:
                        to_p = Point(minx_curr, cake_centroid.y)
                    next_cut = LineString([from_p, to_p])

            print(f"Next cut here: {next_cut}")
            split_pieces = split(current_cake, next_cut)
            subpiece1, subpiece2 = split_pieces.geoms
            if subpiece1.area > subpiece2.area:
                subpiece1, subpiece2 = subpiece2, subpiece1
            cuts1 = self._cut_rectangle(subpiece1, children_left[0])
            cuts2 = self._cut_rectangle(subpiece2, children_left[1])

        print(f"Next cut: {next_cut}")
        cut_sequence = [(Point(next_cut.coords[0]), Point(next_cut.coords[1]))] + cuts1 + cuts2
        return cut_sequence
         

    
    def get_cuts(self) -> list[tuple[Point, Point]]:
        if os.path.basename(self.cake_path) == "rectangle.csv":
            cuts = self._cut_rectangle(self.cake.exterior_shape, self.children)
            print(f"Final cuts: {cuts}")
            return cuts

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


    def _get_bounds(self, current_cake: Polygon) -> tuple[float, float, float, float]:
        cake_boundary_points = current_cake.get_boundary_points() if isinstance(current_cake, Cake) else [Point(c) for c in current_cake.boundary.coords]
        min_x = min(point.x for point in cake_boundary_points)
        min_y = min(point.y for point in cake_boundary_points)
        max_x = max(point.x for point in cake_boundary_points)
        max_y = max(point.y for point in cake_boundary_points)
        return min_x, min_y, max_x, max_y

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