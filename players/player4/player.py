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
        self.cake_crust: LineString = cake.exterior_shape.boundary

    def get_cuts(self) -> list[tuple[Point, Point]]:
        if (
            os.path.basename(self.cake_path) == "rectangle.csv"
            or os.path.basename(self.cake_path) == "square.csv"
        ):
            cuts = self._cut_rectangular_cake(self.cake.exterior_shape, self.children)
            return cuts

    def _cut_rectangular_cake(self, current_cake: Polygon, children: int):
        print(f"\ncutting rectangle with {children} children remaining.")
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
            if current_crust == self.cake_crust:
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
                if even_split:
                    from_p = current_crust.interpolate(
                        crust_len_per_piece * (children / 2)
                    )
                else:
                    from_p = current_crust.interpolate(
                        crust_len_per_piece * floor(children / 2)
                    )
                to_p = cake_centroid
                next_cut = LineString([from_p, to_p])

                # Make sure cut goes all the way to opposite side of cake
                if not to_p.intersects(current_crust):
                    print("cut doesn't intersect cake, adjusting")
                    if from_p.x < cake_centroid.x:
                        to_p = Point(maxx_curr, cake_centroid.y)
                    else:
                        to_p = Point(minx_curr, cake_centroid.y)
                    next_cut = LineString([from_p, to_p])

            return next_cut

        if children % 2 == 0:
            next_cut = _get_next_cut(children, even_split=True)
            children_left = children / 2

            split_pieces = split(current_cake, next_cut)
            subpiece1, subpiece2 = split_pieces.geoms
            cuts1 = self._cut_rectangular_cake(subpiece1, children_left)
            cuts2 = self._cut_rectangular_cake(subpiece2, children_left)

        else:
            next_cut = _get_next_cut(children, even_split=False)
            children_left = [floor(children / 2), ceil(children / 2)]
            split_pieces = split(current_cake, next_cut)
            subpiece1, subpiece2 = split_pieces.geoms

            # Make sure subpiece1 is the smaller piece
            if subpiece1.area > subpiece2.area:
                subpiece1, subpiece2 = subpiece2, subpiece1
            cuts1 = self._cut_rectangular_cake(subpiece1, children_left[0])
            cuts2 = self._cut_rectangular_cake(subpiece2, children_left[1])

        print(f"Next cut: {next_cut}")
        cut_sequence = (
            [(Point(next_cut.coords[0]), Point(next_cut.coords[1]))] + cuts1 + cuts2
        )
        return cut_sequence

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
