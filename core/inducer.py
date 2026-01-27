"""GUI-independent inducer information model."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Dict, Iterable, Optional
import math

from .velocity_triangles import InletTriangle, OutletTriangle

STATION_KEYS = ("hub_le", "hub_te", "shroud_le", "shroud_te")


@dataclass(frozen=True)
class StationGeom:
    """Geometry data for a station."""

    z: float
    r: float


@dataclass(frozen=True)
class StationBlade:
    """Blade-related data for a station."""

    beta_blade: float
    blade_number: int
    thickness: float
    incidence: float = 0.0
    slip_angle_mock: float | None = None
    blockage: float | None = None


@dataclass(frozen=True)
class StationFlow:
    """Flow-related inputs for a station."""

    c_m: float
    omega: float
    alpha: float | None = None


@dataclass
class Inducer:
    """Single source of truth for inducer-related inputs and derived helpers."""

    r_in_hub: float
    r_in_tip: float
    r_out_hub: float
    r_out_tip: float
    omega: float
    c_m_in: float
    c_m_out: float
    alpha_in: float
    beta_blade_in: float
    beta_blade_out: float
    blade_number: int
    thickness_in: float
    thickness_out: float
    incidence_in: float
    blockage_in: float
    blockage_out: float
    slip_out: float
    phi2_la: float | None = None
    t2: float | None = None
    flow_rate: float = 0.01
    rho: float = 1140.0
    g: float = 9.80665
    stations_geom: Dict[str, StationGeom] = field(default_factory=dict)
    stations_blade: Dict[str, StationBlade] = field(default_factory=dict)
    stations_flow: Dict[str, StationFlow] = field(default_factory=dict)
    geometry: Dict[str, Any] = field(default_factory=dict)
    operating_point: Dict[str, Any] = field(default_factory=dict)
    blade_parameters: Dict[str, Any] = field(default_factory=dict)
    velocity_triangle_inputs: Dict[str, Any] = field(default_factory=dict)
    extras: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._ensure_station_defaults()
        self.validate()

    def validate(self) -> None:
        """Validate required inputs and raise ValueError on invalid values."""
        self._validate_positive("r_in_hub", self.r_in_hub)
        self._validate_positive("r_in_tip", self.r_in_tip)
        self._validate_positive("r_out_hub", self.r_out_hub)
        self._validate_positive("r_out_tip", self.r_out_tip)
        self._validate_positive("omega", self.omega)
        self._validate_positive("c_m_in", self.c_m_in)
        self._validate_positive("c_m_out", self.c_m_out)
        self._validate_positive("blade_number", float(self.blade_number))
        self._validate_positive("blockage_in", self.blockage_in)
        self._validate_positive("blockage_out", self.blockage_out)
        self._validate_non_negative("thickness_in", self.thickness_in)
        self._validate_non_negative("thickness_out", self.thickness_out)

        for name, value in [
            ("alpha_in", self.alpha_in),
            ("beta_blade_in", self.beta_blade_in),
            ("beta_blade_out", self.beta_blade_out),
            ("incidence_in", self.incidence_in),
            ("slip_out", self.slip_out),
        ]:
            self._validate_finite(name, value)

        if self.flow_rate <= 0:
            raise ValueError("flow_rate must be a positive finite value.")
        if self.rho <= 0:
            raise ValueError("rho must be a positive finite value.")
        if self.g <= 0:
            raise ValueError("g must be a positive finite value.")

    def make_inlet_triangle(self, radius: float | None = None) -> InletTriangle:
        """Create an inlet triangle for the requested radius."""
        r = self.r_in_hub if radius is None else radius
        return InletTriangle(
            r=r,
            omega=self.omega,
            c_m=self.c_m_in,
            alpha=self.alpha_in,
            blade_number=self.blade_number,
            blockage=self.blockage_in,
            incidence=self.incidence_in,
            beta_blade=self.beta_blade_in,
        )

    def make_outlet_triangle(self, radius: float | None = None) -> OutletTriangle:
        """Create an outlet triangle for the requested radius."""
        r = self.r_out_hub if radius is None else radius
        return OutletTriangle(
            r=r,
            omega=self.omega,
            c_m=self.c_m_out,
            beta_blade=self.beta_blade_out,
            blade_number=self.blade_number,
            blockage=self.blockage_out,
            slip=self.slip_out,
            slip_angle_mock=self.slip_out,
        )

    def _ensure_station_defaults(self) -> None:
        if self.stations_geom and self.stations_blade and self.stations_flow:
            return
        self.stations_geom = {
            "hub_le": StationGeom(z=0.0, r=self.r_in_hub),
            "hub_te": StationGeom(z=1.0, r=self.r_out_hub),
            "shroud_le": StationGeom(z=0.0, r=self.r_in_tip),
            "shroud_te": StationGeom(z=1.0, r=self.r_out_tip),
        }
        self.stations_blade = {
            "hub_le": StationBlade(
                beta_blade=self.beta_blade_in,
                blade_number=self.blade_number,
                thickness=self.thickness_in,
                incidence=self.incidence_in,
            ),
            "hub_te": StationBlade(
                beta_blade=self.beta_blade_out,
                blade_number=self.blade_number,
                thickness=self.thickness_out,
                slip_angle_mock=self.slip_out,
            ),
            "shroud_le": StationBlade(
                beta_blade=self.beta_blade_in,
                blade_number=self.blade_number,
                thickness=self.thickness_in,
                incidence=self.incidence_in,
            ),
            "shroud_te": StationBlade(
                beta_blade=self.beta_blade_out,
                blade_number=self.blade_number,
                thickness=self.thickness_out,
                slip_angle_mock=self.slip_out,
            ),
        }
        self.stations_flow = {
            "hub_le": StationFlow(c_m=self.c_m_in, omega=self.omega, alpha=self.alpha_in),
            "hub_te": StationFlow(c_m=self.c_m_out, omega=self.omega, alpha=None),
            "shroud_le": StationFlow(c_m=self.c_m_in, omega=self.omega, alpha=self.alpha_in),
            "shroud_te": StationFlow(c_m=self.c_m_out, omega=self.omega, alpha=None),
        }

    def _build_inlet_triangle(self, station_key: str) -> InletTriangle:
        geom = self.stations_geom[station_key]
        blade = self.stations_blade[station_key]
        flow = self.stations_flow[station_key]
        blockage = blade.blockage if blade.blockage is not None else self.blockage_in
        return InletTriangle(
            r=geom.r,
            omega=flow.omega,
            c_m=flow.c_m,
            alpha=flow.alpha if flow.alpha is not None else self.alpha_in,
            blade_number=blade.blade_number,
            blockage=blockage,
            incidence=blade.incidence,
            beta_blade=blade.beta_blade,
        )

    def _build_outlet_triangle(self, station_key: str) -> OutletTriangle:
        geom = self.stations_geom[station_key]
        blade = self.stations_blade[station_key]
        flow = self.stations_flow[station_key]
        blockage = blade.blockage if blade.blockage is not None else self.blockage_out
        slip_angle = blade.slip_angle_mock if blade.slip_angle_mock is not None else self.slip_out
        return OutletTriangle(
            r=geom.r,
            omega=flow.omega,
            c_m=flow.c_m,
            beta_blade=blade.beta_blade,
            blade_number=blade.blade_number,
            blockage=blockage,
            slip=slip_angle,
            slip_angle_mock=blade.slip_angle_mock,
        )

    def _compute_tau(self, blade: StationBlade, geom: StationGeom) -> Optional[float]:
        denom = 2.0 * math.pi * geom.r * math.sin(blade.beta_blade)
        if abs(denom) < 1e-9:
            return None
        tau = (blade.blade_number * blade.thickness) / denom
        return max(0.0, tau)

    def _fill_pair_rows(
        self,
        row_values: Dict[str, list[Optional[float]]],
        inlet_hub: InletTriangle,
        outlet_hub: OutletTriangle,
        inlet_shroud: InletTriangle,
        outlet_shroud: OutletTriangle,
    ) -> None:
        pairs = [
            (inlet_hub, outlet_hub, 1),
            (inlet_shroud, outlet_shroud, 3),
        ]
        for inlet, outlet, idx in pairs:
            row_values["w2/w1"][idx] = outlet.w / inlet.w if inlet.w else None
            row_values["c2/c1"][idx] = outlet.c / inlet.c if inlet.c else None
            row_values["ΔαF"][idx] = outlet.alpha - inlet.alpha
            row_values["ΔβF"][idx] = outlet.beta - inlet.beta
            row_values["φ=ΔβB"][idx] = outlet.beta_blade - inlet.beta_blade_effective
            row_values["Δ(c_u·r)"][idx] = outlet.cu * outlet.r - inlet.cu * inlet.r

            gamma = self._compute_gamma(outlet)
            row_values["γ"][idx] = gamma

            torque = self.rho * self.flow_rate * row_values["Δ(c_u·r)"][idx]
            row_values["T"][idx] = torque

            h_euler = (outlet.u * outlet.cu - inlet.u * inlet.cu) / self.g
            row_values["H_euler"][idx] = h_euler
            row_values["Δp_t"][idx] = self.rho * self.g * h_euler / 1e5

    def _compute_gamma(self, outlet: OutletTriangle) -> Optional[float]:
        if self.phi2_la is None or self.t2 is None:
            return None
        if outlet.u == 0:
            return None
        tan_beta = math.tan(outlet.beta_blade)
        if abs(tan_beta) < 1e-9:
            return None
        return outlet.cu / outlet.u + (self.phi2_la / tan_beta) * (self.t2 / outlet.u)

    def _row_keys(self) -> Iterable[str]:
        return [
            "z",
            "r",
            "d",
            "αF",
            "βF",
            "u",
            "c_m",
            "c_u",
            "c_r",
            "c_z",
            "c",
            "w_u",
            "w",
            "τ",
            "i",
            "δ",
            "w2/w1",
            "c2/c1",
            "ΔαF",
            "ΔβF",
            "φ=ΔβB",
            "γ",
            "Δ(c_u·r)",
            "T",
            "H_euler",
            "Δp_t",
        ]

    def update_from_geometry(self, payload: Dict[str, Dict[str, float]]) -> "Inducer":
        """Return a new Inducer with geometry station updates applied."""
        stations_geom = dict(self.stations_geom)
        for key in STATION_KEYS:
            if key in payload:
                data = payload[key]
                stations_geom[key] = StationGeom(z=float(data["z"]), r=float(data["r"]))
        updated = replace(
            self,
            r_in_hub=stations_geom["hub_le"].r,
            r_in_tip=stations_geom["shroud_le"].r,
            r_out_hub=stations_geom["hub_te"].r,
            r_out_tip=stations_geom["shroud_te"].r,
            stations_geom=stations_geom,
        )
        return updated

    def update_from_blade_properties(self, payload: Dict[str, Any]) -> "Inducer":
        """Return a new Inducer with blade property updates applied."""
        blade_number = int(payload["blade_number"])
        incidence_hub = float(payload["incidence_hub"])
        incidence_tip = float(payload["incidence_tip"])
        slip_angle_mock_hub = float(payload["slip_angle_mock_hub"])
        slip_angle_mock_tip = float(payload["slip_angle_mock_tip"])
        thickness = payload["thickness"]

        stations_blade = dict(self.stations_blade)
        stations_blade["hub_le"] = replace(
            stations_blade["hub_le"],
            blade_number=blade_number,
            incidence=incidence_hub,
            thickness=float(thickness["hub_le"]),
        )
        stations_blade["shroud_le"] = replace(
            stations_blade["shroud_le"],
            blade_number=blade_number,
            incidence=incidence_tip,
            thickness=float(thickness["shroud_le"]),
        )
        stations_blade["hub_te"] = replace(
            stations_blade["hub_te"],
            blade_number=blade_number,
            thickness=float(thickness["hub_te"]),
            slip_angle_mock=slip_angle_mock_hub,
        )
        stations_blade["shroud_te"] = replace(
            stations_blade["shroud_te"],
            blade_number=blade_number,
            thickness=float(thickness["shroud_te"]),
            slip_angle_mock=slip_angle_mock_tip,
        )
        return replace(
            self,
            blade_number=blade_number,
            incidence_in=(incidence_hub + incidence_tip) / 2.0,
            slip_out=(slip_angle_mock_hub + slip_angle_mock_tip) / 2.0,
            thickness_in=float((thickness["hub_le"] + thickness["shroud_le"]) / 2.0),
            thickness_out=float((thickness["hub_te"] + thickness["shroud_te"]) / 2.0),
            stations_blade=stations_blade,
        )

    def build_triangles_pair(self, pair_key: str) -> tuple[InletTriangle, OutletTriangle]:
        """Build inlet/outlet triangles for a hub or shroud pair."""
        if pair_key not in {"hub", "shroud"}:
            raise ValueError("pair_key must be 'hub' or 'shroud'.")
        inlet_key = f"{pair_key}_le"
        outlet_key = f"{pair_key}_te"
        inlet = self._build_inlet_triangle(inlet_key)
        outlet = self._build_outlet_triangle(outlet_key)
        return inlet, outlet

    def build_info_snapshot(self) -> Dict[str, Any]:
        """Build a snapshot dict for the Inducer Info table."""
        station_keys = list(STATION_KEYS)
        inlet_hub, outlet_hub = self.build_triangles_pair("hub")
        inlet_shroud, outlet_shroud = self.build_triangles_pair("shroud")
        station_triangles = {
            "hub_le": inlet_hub,
            "hub_te": outlet_hub,
            "shroud_le": inlet_shroud,
            "shroud_te": outlet_shroud,
        }

        row_values: Dict[str, list[Optional[float]]] = {row: [None] * 4 for row in self._row_keys()}

        for idx, key in enumerate(station_keys):
            geom = self.stations_geom[key]
            blade = self.stations_blade[key]
            flow = self.stations_flow[key]
            tri = station_triangles[key]
            tau = self._compute_tau(blade, geom)
            blockage_factor = (
                blade.blockage
                if blade.blockage is not None
                else (self.blockage_in if key.endswith("_le") else self.blockage_out)
            )
            cm_blocked = tri.c_m * blockage_factor

            row_values["z"][idx] = geom.z
            row_values["r"][idx] = geom.r
            row_values["d"][idx] = 2.0 * geom.r
            row_values["αF"][idx] = tri.alpha
            row_values["βF"][idx] = tri.beta
            row_values["u"][idx] = tri.u
            row_values["c_m"][idx] = cm_blocked
            row_values["c_u"][idx] = tri.cu
            row_values["c_r"][idx] = None
            row_values["c_z"][idx] = None
            row_values["c"][idx] = tri.c
            row_values["w_u"][idx] = tri.wu
            row_values["w"][idx] = tri.w
            row_values["τ"][idx] = tau
            if key.endswith("_le"):
                row_values["i"][idx] = blade.beta_blade - tri.beta
            else:
                row_values["δ"][idx] = blade.beta_blade - tri.beta

        self._fill_pair_rows(
            row_values,
            inlet_hub,
            outlet_hub,
            inlet_shroud,
            outlet_shroud,
        )

        return {
            "columns": station_keys,
            "rows": row_values,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-ready dictionary of inputs."""
        return {
            "r_in_hub": float(self.r_in_hub),
            "r_in_tip": float(self.r_in_tip),
            "r_out_hub": float(self.r_out_hub),
            "r_out_tip": float(self.r_out_tip),
            "omega": float(self.omega),
            "c_m_in": float(self.c_m_in),
            "c_m_out": float(self.c_m_out),
            "alpha_in": float(self.alpha_in),
            "beta_blade_in": float(self.beta_blade_in),
            "beta_blade_out": float(self.beta_blade_out),
            "blade_number": int(self.blade_number),
            "thickness_in": float(self.thickness_in),
            "thickness_out": float(self.thickness_out),
            "incidence_in": float(self.incidence_in),
            "blockage_in": float(self.blockage_in),
            "blockage_out": float(self.blockage_out),
            "slip_out": float(self.slip_out),
            "phi2_la": float(self.phi2_la) if self.phi2_la is not None else None,
            "t2": float(self.t2) if self.t2 is not None else None,
            "flow_rate": float(self.flow_rate),
            "rho": float(self.rho),
            "g": float(self.g),
            "stations_geom": {key: {"z": geom.z, "r": geom.r} for key, geom in self.stations_geom.items()},
            "stations_blade": {
                key: {
                    "beta_blade": blade.beta_blade,
                    "blade_number": blade.blade_number,
                    "thickness": blade.thickness,
                    "incidence": blade.incidence,
                    "slip_angle_mock": blade.slip_angle_mock,
                    "blockage": blade.blockage,
                }
                for key, blade in self.stations_blade.items()
            },
            "stations_flow": {
                key: {
                    "c_m": flow.c_m,
                    "omega": flow.omega,
                    "alpha": flow.alpha,
                }
                for key, flow in self.stations_flow.items()
            },
            "geometry": dict(self.geometry),
            "operating_point": dict(self.operating_point),
            "blade_parameters": dict(self.blade_parameters),
            "velocity_triangle_inputs": dict(self.velocity_triangle_inputs),
            "extras": dict(self.extras),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Inducer":
        """Create an Inducer instance from a dictionary."""
        return cls(
            r_in_hub=float(data["r_in_hub"]),
            r_in_tip=float(data["r_in_tip"]),
            r_out_hub=float(data["r_out_hub"]),
            r_out_tip=float(data["r_out_tip"]),
            omega=float(data["omega"]),
            c_m_in=float(data["c_m_in"]),
            c_m_out=float(data["c_m_out"]),
            alpha_in=float(data["alpha_in"]),
            beta_blade_in=float(data["beta_blade_in"]),
            beta_blade_out=float(data["beta_blade_out"]),
            blade_number=int(data["blade_number"]),
            thickness_in=float(data["thickness_in"]),
            thickness_out=float(data["thickness_out"]),
            incidence_in=float(data["incidence_in"]),
            blockage_in=float(data["blockage_in"]),
            blockage_out=float(data["blockage_out"]),
            slip_out=float(data["slip_out"]),
            phi2_la=data.get("phi2_la"),
            t2=data.get("t2"),
            flow_rate=float(data.get("flow_rate", 0.01)),
            rho=float(data.get("rho", 1140.0)),
            g=float(data.get("g", 9.80665)),
            stations_geom={
                key: StationGeom(z=float(val["z"]), r=float(val["r"]))
                for key, val in data.get("stations_geom", {}).items()
            },
            stations_blade={
                key: StationBlade(
                    beta_blade=float(val["beta_blade"]),
                    blade_number=int(val["blade_number"]),
                    thickness=float(val["thickness"]),
                    incidence=float(val.get("incidence", 0.0)),
                    slip_angle_mock=val.get("slip_angle_mock"),
                    blockage=val.get("blockage"),
                )
                for key, val in data.get("stations_blade", {}).items()
            },
            stations_flow={
                key: StationFlow(
                    c_m=float(val["c_m"]),
                    omega=float(val["omega"]),
                    alpha=val.get("alpha"),
                )
                for key, val in data.get("stations_flow", {}).items()
            },
            geometry=dict(data.get("geometry", {})),
            operating_point=dict(data.get("operating_point", {})),
            blade_parameters=dict(data.get("blade_parameters", {})),
            velocity_triangle_inputs=dict(data.get("velocity_triangle_inputs", {})),
            extras=dict(data.get("extras", {})),
        )

    @staticmethod
    def _validate_positive(name: str, value: float) -> None:
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be a positive finite value.")

    @staticmethod
    def _validate_non_negative(name: str, value: float) -> None:
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"{name} must be a non-negative finite value.")

    @staticmethod
    def _validate_finite(name: str, value: float) -> None:
        if not math.isfinite(value):
            raise ValueError(f"{name} must be a finite value.")
