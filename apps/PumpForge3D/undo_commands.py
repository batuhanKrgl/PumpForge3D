"""
Undo/Redo command classes for geometry actions.

All geometry-affecting operations should use these commands to enable undo/redo.
Display-only changes (grid toggle, visibility, etc.) do NOT go through undo stack.
"""

from PySide6.QtGui import QUndoCommand
from typing import Tuple, Optional, Any


class MoveControlPointCommand(QUndoCommand):
    """Undoable command for moving a Bezier control point."""
    
    def __init__(
        self,
        design,
        curve_name: str,
        point_index: int,
        old_pos: Tuple[float, float],
        new_pos: Tuple[float, float],
        on_change_callback=None
    ):
        super().__init__(f"Move {curve_name} P{point_index}")
        self.design = design
        self.curve_name = curve_name
        self.point_index = point_index
        self.old_pos = old_pos
        self.new_pos = new_pos
        self.on_change = on_change_callback
    
    def _get_curve(self):
        """Get the curve object by name."""
        if self.curve_name == "hub":
            return self.design.contour.hub_curve
        elif self.curve_name == "tip":
            return self.design.contour.tip_curve
        elif self.curve_name == "leading":
            return self.design.contour.leading_edge.bezier_curve
        elif self.curve_name == "trailing":
            return self.design.contour.trailing_edge.bezier_curve
        return None
    
    def redo(self):
        curve = self._get_curve()
        if curve:
            curve.set_point(self.point_index, self.new_pos[0], self.new_pos[1])
            if self.on_change:
                self.on_change()
    
    def undo(self):
        curve = self._get_curve()
        if curve:
            curve.set_point(self.point_index, self.old_pos[0], self.old_pos[1])
            if self.on_change:
                self.on_change()


class ChangeParameterCommand(QUndoCommand):
    """Undoable command for changing a numeric parameter (e.g., spinbox value)."""
    
    def __init__(
        self,
        target_object: Any,
        attr_name: str,
        old_value: float,
        new_value: float,
        description: str = "Change parameter",
        on_change_callback=None
    ):
        super().__init__(description)
        self.target = target_object
        self.attr_name = attr_name
        self.old_value = old_value
        self.new_value = new_value
        self.on_change = on_change_callback
    
    def redo(self):
        setattr(self.target, self.attr_name, self.new_value)
        if self.on_change:
            self.on_change()
    
    def undo(self):
        setattr(self.target, self.attr_name, self.old_value)
        if self.on_change:
            self.on_change()


class MoveEdgeAnchorCommand(QUndoCommand):
    """Undoable command for moving an edge anchor point on hub/tip curve."""
    
    def __init__(
        self,
        design,
        edge_name: str,  # "leading" or "trailing"
        anchor_type: str,  # "hub" or "tip"
        old_t: float,  # old parameter value
        new_t: float,  # new parameter value
        on_change_callback=None
    ):
        super().__init__(f"Move {edge_name} edge {anchor_type} anchor")
        self.design = design
        self.edge_name = edge_name
        self.anchor_type = anchor_type
        self.old_t = old_t
        self.new_t = new_t
        self.on_change = on_change_callback
    
    def _get_edge(self):
        if self.edge_name == "leading":
            return self.design.contour.leading_edge
        elif self.edge_name == "trailing":
            return self.design.contour.trailing_edge
        return None
    
    def _set_anchor(self, t_value):
        edge = self._get_edge()
        if edge:
            if self.anchor_type == "hub":
                edge.hub_t = t_value
            else:
                edge.tip_t = t_value
            # Recompute edge endpoints
            edge.update_from_meridional(
                self.design.contour.hub_curve,
                self.design.contour.tip_curve
            )
    
    def redo(self):
        self._set_anchor(self.new_t)
        if self.on_change:
            self.on_change()
    
    def undo(self):
        self._set_anchor(self.old_t)
        if self.on_change:
            self.on_change()


class ChangeAngleLockCommand(QUndoCommand):
    """Undoable command for toggling angle lock on a control point."""
    
    def __init__(
        self,
        design,
        curve_name: str,
        point_index: int,
        old_locked: bool,
        new_locked: bool,
        old_angle: Optional[float] = None,
        new_angle: Optional[float] = None,
        on_change_callback=None
    ):
        action = "Lock" if new_locked else "Unlock"
        super().__init__(f"{action} {curve_name} P{point_index} angle")
        self.design = design
        self.curve_name = curve_name
        self.point_index = point_index
        self.old_locked = old_locked
        self.new_locked = new_locked
        self.old_angle = old_angle
        self.new_angle = new_angle
        self.on_change = on_change_callback
    
    def _get_point(self):
        if self.curve_name == "hub":
            return self.design.contour.hub_curve.control_points[self.point_index]
        elif self.curve_name == "tip":
            return self.design.contour.tip_curve.control_points[self.point_index]
        return None
    
    def redo(self):
        pt = self._get_point()
        if pt:
            pt.angle_locked = self.new_locked
            if self.new_angle is not None:
                pt.locked_angle = self.new_angle
            if self.on_change:
                self.on_change()
    
    def undo(self):
        pt = self._get_point()
        if pt:
            pt.angle_locked = self.old_locked
            if self.old_angle is not None:
                pt.locked_angle = self.old_angle
            if self.on_change:
                self.on_change()


class ChangeDimensionsCommand(QUndoCommand):
    """Undoable command for changing main dimensions."""
    
    def __init__(
        self,
        design,
        old_dims_dict: dict,
        new_dims_dict: dict,
        on_change_callback=None
    ):
        super().__init__("Change main dimensions")
        self.design = design
        self.old_dims = old_dims_dict
        self.new_dims = new_dims_dict
        self.on_change = on_change_callback
    
    def _apply_dims(self, dims_dict):
        from pumpforge3d_core.geometry.meridional import MainDimensions
        new_dims = MainDimensions.from_dict(dims_dict)
        self.design.set_main_dimensions(new_dims)
    
    def redo(self):
        self._apply_dims(self.new_dims)
        if self.on_change:
            self.on_change()
    
    def undo(self):
        self._apply_dims(self.old_dims)
        if self.on_change:
            self.on_change()
