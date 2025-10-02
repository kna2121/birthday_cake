from shapely import LineString, Point, Polygon
from shapely.ops import split

from players.player import Player
from src.cake import Cake


class Player4(Player):
    def __init__(self, children: int, cake: Cake, cake_path: str | None) -> None:
        super().__init__(children, cake, cake_path)
        self.final_piece_min_area = (cake.exterior_shape.area / float(children)) - 0.5

    def get_cuts(self) -> list[tuple[Point, Point]]:
        piece: Polygon = self.cake.exterior_shape
        print(f"Player 4: Starting DFS for {self.children} children.")
        return self.DFS(piece, self.children)

    def DFS(self, piece: Polygon, children: int) -> list[tuple[Point, Point]]:
        print(f"DFS called with {children} children remaining.")
        cut_sequence: list[tuple[Point, Point]] = []
        if children == 1:
            return cut_sequence
        
        possible_cuts: list[tuple[Point, Point]] = self.get_all_possible_cuts(piece)
        valid_cuts: list[tuple[Point, Point]] = self.filter_cuts(piece, children, possible_cuts)
        if not valid_cuts:
            return None
        
        for from_p, to_p in valid_cuts:
            line = LineString([from_p, to_p])
            split_pieces = split(piece, line)
            if len(split_pieces.geoms) != 2:
                continue
            subpiece1, subpiece2 = split_pieces.geoms

            # Central DFS idea: assign each subpiece to have (k, children - k) final pieces and try
            for k in range(1, children):
                subpiece1_children = k
                subpiece2_children = children - k
                subpiece1_min_area = self.final_piece_min_area * subpiece1_children
                subpiece2_min_area = self.final_piece_min_area * subpiece2_children

                # Is each subpiece big enough to share with its assigned children?
                if subpiece1.area < subpiece1_min_area or subpiece2.area < subpiece2_min_area:
                    continue
                
                # DFS on each subpiece
                cuts1 = self.DFS(subpiece1, subpiece1_children)
                if cuts1 is None:
                    continue
                cuts2 = self.DFS(subpiece2, subpiece2_children)
                if cuts2 is None:
                    continue
                
                # Success! Found k where both subpieces can be cut properly
                cut_sequence = [(from_p, to_p)] + cuts1 + cuts2
                return cut_sequence
        return None

    def get_all_possible_cuts(self, piece: Polygon) -> list[tuple[Point, Point]]:
        """
        This method generates a list of all possible valid cuts for a given polygon piece. A possible valid cut is a pair of two points on the piece's perimeter, where the line segment connecting these points lies entirely within the piece.
        """
        # Get the bounding box of the piece
        minx, miny, maxx, maxy = piece.bounds
        
        # Number of sweeps
        num_sweeps: int = 100
        # Calculate step size for sweeping across the width
        step: float = (maxx - minx) / (num_sweeps - 1)
        
        candidate_cuts: list[tuple[Point, Point]] = []
        # Sweep vertically across the piece
        for i in range(num_sweeps):
            x = minx + i * step
            # Extend it beyond the piece's y bounds to ensure intersection
            vertical_line = LineString([(x, miny - 100), (x, maxy + 100)])
            intersection = vertical_line.intersection(piece.boundary)
            if intersection.is_empty:
                continue
            
            # Extract points from the intersection
            points: list[Point] = []
            if intersection.geom_type == 'Point':
                points = [intersection]
            elif intersection.geom_type == 'MultiPoint':
                points = list(intersection.geoms)
            elif intersection.geom_type == 'GeometryCollection':
                # Extract only Point geometries from the collection
                points = [geom for geom in intersection.geoms if geom.geom_type == 'Point']
            
            # We need at least 2 points to make a cut
            if len(points) >= 2:
                # Check all pairs of intersection points
                for j in range(len(points)):
                    for k in range(j + 1, len(points)):
                        from_p: Point = points[j]
                        to_p: Point = points[k]

                        # Check if this cut is valid using the cake's validation method
                        is_valid, _ = self.cake.cut_is_valid(from_p, to_p)
                        if is_valid:
                            candidate_cuts.append((from_p, to_p))
                            
        # Sweep horizontally down the piece
        step: float = (maxy - miny) / (num_sweeps - 1)
        for i in range(num_sweeps):
            y = miny + i * step
            # Extend it beyond the piece's x bounds to ensure intersection
            horizontal_line = LineString([(minx - 100, y), (maxx + 100, y)])
            intersection = horizontal_line.intersection(piece.boundary)
            if intersection.is_empty:
                continue
            
            # Extract points from the intersection
            points: list[Point] = []
            if intersection.geom_type == 'Point':
                points = [intersection]
            elif intersection.geom_type == 'MultiPoint':
                points = list(intersection.geoms)
            elif intersection.geom_type == 'GeometryCollection':
                # Extract only Point geometries from the collection
                points = [geom for geom in intersection.geoms if geom.geom_type == 'Point']
            
            # We need at least 2 points to make a cut
            if len(points) >= 2:
                # Check all pairs of intersection points
                for j in range(len(points)):
                    for k in range(j + 1, len(points)):
                        from_p: Point = points[j]
                        to_p: Point = points[k]

                        # Check if this cut is valid using the cake's validation method
                        is_valid, _ = self.cake.cut_is_valid(from_p, to_p)
                        if is_valid:
                            candidate_cuts.append((from_p, to_p))
        return candidate_cuts

    def filter_cuts(self, piece: Polygon, children: int, cuts: list[tuple[Point, Point]]) -> list[tuple[Point, Point]]:
        """
        This method filters a list of cuts and returns a subset (or none) of them that are valid for the given piece and number of children.
        """
        valid_cuts: list[tuple[Point, Point]] = []
        
        # Keep only cuts where both subpieces are bigger than one final piece in area
        # Each final piece can have a 0.5 unit^2 area tolerance
        children_per_subpiece = children - 1
        for from_p, to_p in cuts:
            line = LineString([from_p, to_p])
            split_pieces = split(piece, line)
            if len(split_pieces.geoms) != 2:
                continue
            piece1, piece2 = split_pieces.geoms
            if piece1.area < self.final_piece_min_area or piece2.area < self.final_piece_min_area:
                # print(f"Cut from {from_p} to {to_p} rejected due to insufficient area: {piece1.area}, {piece2.area}")
                continue
            else:
                valid_cuts.append((from_p, to_p))
        return valid_cuts