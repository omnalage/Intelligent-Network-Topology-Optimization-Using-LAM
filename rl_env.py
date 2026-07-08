"""
Step 1: RL environment wrapper for cache placement.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class RouterMetrics:
    name: str
    cache_occupancy: float
    chr_value: float
    latency_ms: float
    cmba: float
    global_avg_chr: float
    global_avg_latency: float


class CacheEnvironment:
    """
    Minimal RL-style environment:
    - reset()
    - step(action)
    """

    def __init__(
        self,
        routers: List[Any],
        publishers: Optional[List[Any]] = None,
        subscribers: Optional[List[Any]] = None,
        episode_length: int = 100,
        w1: float = 0.25,
        w2: float = 0.25,
        w3: float = 0.25,
        w4: float = 0.25,
        refresh_metrics_fn: Optional[Callable[..., Any]] = None,
        auto_refresh_on_reset: bool = True,
        auto_refresh_on_step: bool = True,
    ) -> None:
        if not routers:
            raise ValueError("routers must be non-empty")
        if episode_length <= 0:
            raise ValueError("episode_length must be > 0")
        self.routers = routers
        self.publishers = publishers or []
        self.subscribers = subscribers or []
        self.episode_length = episode_length
        self.w1 = w1
        self.w2 = w2
        self.w3 = w3
        self.w4 = w4
        self.refresh_metrics_fn = refresh_metrics_fn
        self.auto_refresh_on_reset = auto_refresh_on_reset
        self.auto_refresh_on_step = auto_refresh_on_step
        self._step_count = 0

    def reset(self) -> np.ndarray:
        self._step_count = 0
        if self.auto_refresh_on_reset:
            self._refresh_metrics()
        return self._get_state()

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict[str, Any]]:
        if not isinstance(action, int):
            raise TypeError("action must be an integer router index")
        if action < 0 or action >= len(self.routers):
            raise IndexError(f"action out of bounds: {action}")

        metrics = self._collect_router_metrics()
        selected = metrics[action]

        chr_norm = self._clip01(selected.chr_value)
        occ_norm = self._normalize_occupancy(selected.cache_occupancy, self.routers[action])
        lat_norm = self._normalize_latency(selected.latency_ms, metrics)
        cmba_norm = self._normalize_cmba(selected.cmba, metrics)

        reward = self.w1 * chr_norm + self.w2 * cmba_norm - self.w3 * lat_norm - self.w4 * occ_norm

        self._step_count += 1
        done = self._step_count >= self.episode_length
        if self.auto_refresh_on_step:
            self._refresh_metrics(action=action)
        next_state = self._get_state()

        info = {
            "selected_router_index": action,
            "selected_router_name": selected.name,
            "metrics": {
                "cache_occupancy": selected.cache_occupancy,
                "chr": selected.chr_value,
                "latency_ms": selected.latency_ms,
                "cmba": selected.cmba,
            },
            "reward_components": {
                "chr_norm": chr_norm,
                "latency_norm": lat_norm,
                "cache_occupancy_norm": occ_norm,
                "cmba_norm": cmba_norm,
            },
            "formula": "reward = w1 * CHR + w2 * CMBA - w3 * latency - w4 * cache_occupancy",
        }
        return next_state, float(reward), done, info

    def update_network(
        self,
        new_routers: List[Any],
        new_publishers: Optional[List[Any]] = None,
        new_subscribers: Optional[List[Any]] = None,
    ) -> np.ndarray:
        if not new_routers:
            raise ValueError("new_routers must be non-empty")
        self.routers = new_routers
        if new_publishers is not None:
            self.publishers = new_publishers
        if new_subscribers is not None:
            self.subscribers = new_subscribers
        return self.reset()

    def _get_state(self) -> np.ndarray:
        metrics = self._collect_router_metrics()
        
        # Normalize all features to 0-1 across routers for consistency
        def normalize_feature(vals: List[float]) -> List[float]:
            mn = min(vals) if vals else 0.0
            mx = max(vals) if vals else 0.0
            if mx > mn:
                return [(v - mn) / (mx - mn) for v in vals]
            else:
                return [0.0] * len(vals)
        
        occ_vals = [m.cache_occupancy for m in metrics]
        chr_vals = [m.chr_value for m in metrics]
        lat_vals = [m.latency_ms for m in metrics]
        cmba_vals = [m.cmba for m in metrics]
        global_chr_vals = [m.global_avg_chr for m in metrics]
        global_lat_vals = [m.global_avg_latency for m in metrics]
        
        occ_norm = normalize_feature(occ_vals)
        chr_norm = normalize_feature(chr_vals)
        lat_norm = normalize_feature(lat_vals)
        cmba_norm = normalize_feature(cmba_vals)
        global_chr_norm = normalize_feature(global_chr_vals)
        global_lat_norm = normalize_feature(global_lat_vals)
        
        flat = []
        for i in range(len(metrics)):
            flat.extend([occ_norm[i], chr_norm[i], lat_norm[i], cmba_norm[i], global_chr_norm[i], global_lat_norm[i]])
        return np.asarray(flat, dtype=np.float32)

    def _collect_router_metrics(self) -> List[RouterMetrics]:
        out = []
        chr_values = []
        latency_values = []
        for r in self.routers:
            name = str(getattr(r, "name", "unknown"))

            cs = getattr(r, "cs", [])
            try:
                occ = float(len(cs))
            except Exception:
                occ = 0.0

            cache_hits = float(getattr(r, "cache_hits", 0.0))
            total_requests = float(getattr(r, "total_requests", 0.0))
            chr_value = (cache_hits / total_requests) if total_requests > 0 else 0.0

            total_cache_access_time = float(getattr(r, "total_cache_access_time", 0.0))
            if total_requests > 0:
                latency_ms = (total_cache_access_time / total_requests) * 1000.0
            else:
                latency_ms = float(getattr(r, "avg_cache_latency_ms", 0.0) or 0.0)

            cmba = getattr(r, "CMBA", None)
            if cmba is None:
                cmba = getattr(r, "cmba", 0.0)
            try:
                cmba = float(cmba)
            except Exception:
                cmba = 0.0

            chr_clipped = self._clip01(chr_value)
            lat_clipped = max(0.0, latency_ms)

            chr_values.append(chr_clipped)
            latency_values.append(lat_clipped)

            out.append(
                RouterMetrics(
                    name=name,
                    cache_occupancy=occ,
                    chr_value=chr_clipped,
                    latency_ms=lat_clipped,
                    cmba=cmba,
                    global_avg_chr=0.0,  # placeholder
                    global_avg_latency=0.0,  # placeholder
                )
            )

        # Compute global averages for cooperation features
        if chr_values:
            global_avg_chr = sum(chr_values) / len(chr_values)
            global_avg_latency = sum(latency_values) / len(latency_values)
        else:
            global_avg_chr = 0.0
            global_avg_latency = 0.0

        # Update all metrics with global averages
        for m in out:
            m.global_avg_chr = global_avg_chr
            m.global_avg_latency = global_avg_latency

        return out

    def _refresh_metrics(self, action: Optional[int] = None) -> None:
        if not callable(self.refresh_metrics_fn):
            return
        try:
            self.refresh_metrics_fn(action=action)
        except TypeError:
            self.refresh_metrics_fn()

    @staticmethod
    def _clip01(x: float) -> float:
        return max(0.0, min(1.0, float(x)))

    @staticmethod
    def _normalize_occupancy(occ: float, router: Any) -> float:
        cache_limit = getattr(router.__class__, "CACHE_LIMIT", None)
        if cache_limit is None:
            cache_limit = getattr(router, "CACHE_LIMIT", None)
        if cache_limit and float(cache_limit) > 0:
            return CacheEnvironment._clip01(occ / float(cache_limit))
        return 0.0

    @staticmethod
    def _normalize_latency(selected_latency_ms: float, all_metrics: List[RouterMetrics]) -> float:
        lat_vals = [m.latency_ms for m in all_metrics]
        mn = min(lat_vals) if lat_vals else 0.0
        mx = max(lat_vals) if lat_vals else 0.0
        if mx - mn < 1e-12:
            return 0.0
        return CacheEnvironment._clip01((selected_latency_ms - mn) / (mx - mn))

    @staticmethod
    def _normalize_cmba(selected_cmba: float, all_metrics: List[RouterMetrics]) -> float:
        cmba_vals = [m.cmba for m in all_metrics]
        mn = min(cmba_vals) if cmba_vals else 0.0
        mx = max(cmba_vals) if cmba_vals else 0.0
        if mx - mn < 1e-12:
            return 0.0
        return CacheEnvironment._clip01((selected_cmba - mn) / (mx - mn))


if __name__ == "__main__":
    from main import load_network

    network = load_network()
    if not network:
        raise RuntimeError("No saved network found. Create one first.")

    routers, publishers, subscribers = network
    env = CacheEnvironment(routers=routers, episode_length=5)
    state = env.reset()
    print("Initial state shape:", state.shape)

    next_state, reward, done, info = env.step(action=0)
    print("Step reward:", reward)
    print("Done:", done)
    print("Selected router:", info["selected_router_name"])
