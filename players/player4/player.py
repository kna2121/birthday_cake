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
        self.min_area_per_piece: float = self.ideal_area_per_piece - (c.PIECE_SPAN_TOL * 0.5)
        self.max_area_per_piece: float = self.ideal_area_per_piece + (c.PIECE_SPAN_TOL * 0.5)
        self.cake_crust: LineString = cake.exterior_shape.boundary

        print(f"Ideal area per piece: {self.ideal_area_per_piece}")
        print(f"Min area per piece: {self.min_area_per_piece}")
        print(f"Max area per piece: {self.max_area_per_piece}")

    def get_cuts(self) -> list[tuple[Point, Point]]:
        cuts = self.get_mushroom_cuts() 
        # cuts = self._cut_basic_cake(self.cake.exterior_shape, self.children)
        return cuts

    def get_mushroom_cuts(self) -> list[tuple[Point, Point]]:
        cuts: list[tuple[Point, Point]] = []
        assert self.children == 6, "Pre-set mushroom cake can only serve 6 children!"  

        cake_centroid = self.cake.exterior_shape.centroid
        minx, miny, maxx, maxy = self._get_bounds(self.cake)

        # first cut vertically down the middle
        first_v_cut = LineString([(cake_centroid.x, miny), (cake_centroid.x, maxy)])
        v_cut_p1, v_cut_p2 = Point(first_v_cut.coords[0]), Point(first_v_cut.coords[1])
        cuts.append((v_cut_p1, v_cut_p2))

        # Get the two halves
        split_halves = split(self.cake.exterior_shape, first_v_cut)

        # Cut the halves in pieces with good ratio and area
        cuts_per_halve = self.children // 2
        center_upper_p = Point(cake_centroid.x, 0)

        for i, piece in enumerate(split_halves.geoms):
            # Get crust of current half
            current_crust = linemerge(self.cake_crust.intersection(piece.boundary))
            if not center_upper_p.equals(Point(current_crust.coords[0])):
                current_crust = LineString(list(current_crust.coords)[::-1])
          
            crust_len_per_piece = current_crust.length / cuts_per_halve
            current_piece = piece
            for cut in range(1, cuts_per_halve):
                from_p = current_crust.interpolate(crust_len_per_piece * cut)
                from_p = current_crust.interpolate(current_crust.project(from_p))
                to_p = cake_centroid

                def adjust_to_fit_area(piece, from_p, to_p):
                    max_steps = 100
                    step = 0.1
                    for _ in range(max_steps):
                        test_cut = LineString([to_p, from_p])
                        split_pieces = split(piece, test_cut)
                        top_piece, bottom_piece = sorted(split_pieces.geoms, key=lambda p: p.centroid.y)
                        
                        # Check if area of top piece is within bounds and adjust to_p accordingly
                        if self.min_area_per_piece <= top_piece.area <= self.max_area_per_piece:
                            return to_p, top_piece, bottom_piece
                        if top_piece.area > self.max_area_per_piece:
                            to_p = Point(to_p.x, to_p.y - step)
                        else:
                            to_p = Point(to_p.x, to_p.y + step)

                    return to_p, top_piece, bottom_piece

                to_p, _, bottom_piece = adjust_to_fit_area(current_piece, from_p, to_p)
                cuts.append((from_p, to_p))
                if bottom_piece is not None:
                    current_piece = bottom_piece

        return cuts
    
    def _cut_basic_cake(self, current_cake: Polygon, children: int):
        print(f"\ncutting with {children} children remaining.")
        cut_sequence: list[tuple[Point, Point]] = []

        # base case of recursion
        if children == 1:
            return cut_sequence

        cake_centroid = self.cake.exterior_shape.centroid
        minx, miny, maxx, maxy = self._get_bounds(self.cake)
        length = maxx - minx

        minx_curr, _, maxx_curr, _ = self._get_bounds(current_cake)
        current_crust = linemerge(self.cake_crust.intersection(current_cake.boundary))
        print(f"current crust: {current_crust}")

        def _get_next_cut(children, even_split):
            next_cut: LineString = None

            # Do we still have the full crust?
            if self._is_full_crust_left(current_cake):
                print("full crust left, cutting vertically in middle")
                if even_split:
                    next_cut = LineString(
                        [(cake_centroid.x, miny), (cake_centroid.x, maxy)]
                    )
                else:
                    start_distance = self.cake_crust.project(Point(minx, miny))
                    from_p = current_crust.interpolate(
                        start_distance + (floor(children / 2) / children) * length
                    )
                    to_p = (from_p.x, maxy)
                    next_cut = LineString([from_p, to_p])

            else:
                crust_len_per_piece = current_crust.length / children

                # print(f"current cake HERE: {current_cake.boundary}, move for {crust_len_per_piece * floor(children / 2)}")

                # Cut from point on crust
                from_p = current_crust.interpolate(
                    crust_len_per_piece * floor(children / 2)    # Floor in case of odd number of children
                )

                from_p = current_cake.boundary.interpolate(current_cake.boundary.project(from_p))


                to_p = cake_centroid
                # Pick point on interior on opposite side of cake based on area
                # Try to find a to_p that yields approximately equal-area pieces
                target_area = self.ideal_area_per_piece * floor(children / 2)
                print(f"Target area for smaller piece: {target_area}")

                # test cut to find smaller area piece
                test_cut = LineString([from_p, to_p])
                # Initial split to identify which side (top/bottom) is the smaller piece
                split_pieces = split(Polygon(current_cake.exterior.coords), test_cut)
                if len(split_pieces.geoms) < 2:
                    fixed_side = "top"
                    # print(f"cut {test_cut} doesn't split cake!")
                    # print(current_cake.boundary.intersection(test_cut))
                    # print(split_pieces)
                else:
                    bottom_piece, top_piece = sorted(split_pieces.geoms, key=lambda p: p.centroid.y)

                    print(f"bottom piece area: {bottom_piece.area}, top piece area: {top_piece.area}")
                    if bottom_piece.area < top_piece.area:
                        fixed_side = "bottom"
                        
                    else:
                        fixed_side = "top"
                       

                print(f"Fixed side for area adjustment: {fixed_side}")

                # Try to find vertical offset (up/down) from centroid to match target area
                best_to_p = cake_centroid
                best_area_diff = float("inf")

                minx_c, miny_c, maxx_c, maxy_c = current_cake.bounds
                height = maxy_c - miny_c

                def area_diff_for_offset(offset_y: float) -> float | None:
                    test_to_p = Point(cake_centroid.x, cake_centroid.y + offset_y)
                    test_cut = LineString([from_p, test_to_p])
                    # print(f"test_cut: {test_cut}")
                    try:
                        current_cake_copy = Polygon(current_cake.exterior.coords)
                        split_pieces = split(current_cake_copy, test_cut)
                        if len(split_pieces.geoms) < 2:
                            # print(f"{test_cut} not cutting cake {current_cake_copy}")
                            print(current_cake.boundary.intersection(test_cut))
                            return None

                        # Always pick the same side based on centroid.y
                        # print("cutting cake!")
                        bottom_piece, top_piece = sorted(split_pieces.geoms, key=lambda p: p.centroid.y)
                        smaller_piece = bottom_piece if fixed_side == "bottom" else top_piece
                        print(f"Testing {test_to_p}: smaller piece area = {smaller_piece.area}")
                        return smaller_piece.area - target_area
                    except Exception:
                        return None

                dy_test = 0.05 * height
                diff_up = area_diff_for_offset(dy_test)
                diff_down = area_diff_for_offset(-dy_test)
                print(f"Area diffs for small offsets {dy_test}: up={diff_up}, down={diff_down}")
                if diff_up is None and diff_down is None:
                    # fallback to centroid
                    to_p = best_to_p
                else:
                    # Determine direction: if going up increases smaller area, go that way
                    if diff_up is not None and diff_down is not None:
                        direction = 1 if abs(diff_up) < abs(diff_down) else -1
                    elif diff_up is not None:
                        direction = 1
                    else:
                        direction = -1

                    for inc in range(100):
                        offset_y = direction * inc * 0.1
                        diff = area_diff_for_offset(offset_y)
                        if diff is not None and abs(diff) < best_area_diff:
                            best_area_diff = abs(diff)
                            best_to_p = Point(cake_centroid.x, cake_centroid.y + offset_y)
                            print(f"trying out point {best_to_p}")

                        # stop early if area is within acceptable bounds
                        smaller_piece_area = target_area + diff
                        if self.min_area_per_piece * floor(children / 2) <= smaller_piece_area <= self.max_area_per_piece * floor(children / 2):
                            print("found ideal area match")
                            best_to_p = Point(cake_centroid.x, cake_centroid.y + offset_y)
                            break

                    to_p = best_to_p
                    print(f"Chosen to_p: {to_p}")
                    next_cut = LineString([from_p, to_p])


                # Make sure cut goes all the way to opposite side of cake
                # if not to_p.intersects(current_crust):
                #     print("cut doesn't intersect cake, adjusting")
                #     if from_p.x < cake_centroid.x:
                #         to_p = Point(maxx_curr, cake_centroid.y)
                #     else:
                #         to_p = Point(minx_curr, cake_centroid.y)
                #     next_cut = LineString([from_p, to_p])

            return next_cut

        if children % 2 == 0:
            next_cut = _get_next_cut(children, even_split=True)
            children_left = children / 2

            split_pieces = split(current_cake, next_cut)
            subpiece1, subpiece2 = split_pieces.geoms
            cuts1 = self._cut_basic_cake(subpiece1, children_left)
            cuts2 = self._cut_basic_cake(subpiece2, children_left)

        else:
            next_cut = _get_next_cut(children, even_split=False)
            print(f"Next cut: {next_cut}")
            children_left = [floor(children / 2), ceil(children / 2)]
            split_pieces = split(current_cake, next_cut)
            subpiece1, subpiece2 = split_pieces.geoms

            # Make sure subpiece1 is the smaller piece
            if subpiece1.area > subpiece2.area:
                subpiece1, subpiece2 = subpiece2, subpiece1
            cuts1 = self._cut_basic_cake(subpiece1, children_left[0])
            cuts2 = self._cut_basic_cake(subpiece2, children_left[1])

       
        cut_sequence = (
            [(Point(next_cut.coords[0]), Point(next_cut.coords[1]))] + cuts1 + cuts2
        )
        return cut_sequence
    
    def _is_full_crust_left(self, current_cake: Polygon) -> bool:
        current_crust = linemerge(self.cake_crust.intersection(current_cake.boundary))
        current_crust_points = set(Point(co) for co in current_crust.coords)
        cake_crust_points = set(Point(co) for co in self.cake_crust.coords)
        return current_crust_points == cake_crust_points

    def _is_cake_symmetric(
        self,
    ) -> Literal["symmetric_x", "symmetric_y", "symmetric_both", False]:
        cake_centroid = self.cake.exterior_shape.centroid
        cake_boundary_points = {
            Point(co) for co in self.cake.exterior_shape.boundary.coords
        }

        cake_reflected_x = scale(
            self.cake.exterior_shape,
            xfact=1,
            yfact=-1,
            origin=(cake_centroid.x, cake_centroid.y),
        )
        cake_reflected_y = scale(
            self.cake.exterior_shape,
            xfact=-1,
            yfact=1,
            origin=(cake_centroid.x, cake_centroid.y),
        )

        reflected_x_points = {Point(co) for co in cake_reflected_x.boundary.coords}
        reflected_y_points = {Point(co) for co in cake_reflected_y.boundary.coords}

        symmetric_x = reflected_x_points == cake_boundary_points
        symmetric_y = reflected_y_points == cake_boundary_points

        if symmetric_x and symmetric_y:
            return "symmetric_both"
        elif symmetric_x:
            return "symmetric_x"
        elif symmetric_y:
            return "symmetric_y"
        else:
            return False

    def _get_bounds(self, current_cake: Polygon) -> tuple[float, float, float, float]:
        cake_boundary_points = (
            current_cake.get_boundary_points()
            if isinstance(current_cake, Cake)
            else [Point(co) for co in current_cake.boundary.coords]
        )
        min_x = min(point.x for point in cake_boundary_points)
        min_y = min(point.y for point in cake_boundary_points)
        max_x = max(point.x for point in cake_boundary_points)
        max_y = max(point.y for point in cake_boundary_points)
        return min_x, min_y, max_x, max_y
