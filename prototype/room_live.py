"""Hardware-in-the-loop Classroom Resource Management controller & WebSocket hub.

Implements CampusFlow's tiered policy for live AMB82-Mini occupancy telemetry
and instant WebSocket appliance control on an Android phone (/room-panel):
  - Auto-wake / instant hold when occupancy is detected (2 consecutive frames)
  - Tier 1 (Auto): Turn Lights & Fans Off after sustained vacancy when no class is scheduled
  - Tier 2 (Facilities Approval): Projector Standby OR any mid-schedule vacancy shutdown
  - Commit-time occupancy, freshness, and wall-override re-check before applying Tier 2
  - Closed-loop ACK verification from the Android phone simulator
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import time
from typing import Any, Callable, Optional
from uuid import uuid4


ACTIVE_DEVICES = {"Lights": "On", "Fans": "On", "Projector": "On"}


class RoomPolicyError(Exception):
    """Raised when a live room command violates safety, freshness, or version policy."""


@dataclass
class RoomLiveController:
    room: str = "C-101"
    vacant_threshold_sec: float = 15.0
    max_frame_age_sec: float = 5.0
    min_confidence: float = 0.55
    wake_frames_required: int = 2
    clock: Callable[[], float] = time.time

    devices: dict[str, str] = field(default_factory=lambda: dict(ACTIVE_DEVICES))
    class_scheduled: bool = False
    wall_override: bool = False
    version: int = 0

    # Latest sensor telemetry
    last_count: Optional[int] = None
    last_confidence: Optional[float] = None
    last_source: str = "none"
    last_sample_at: Optional[float] = None
    vacant_since: Optional[float] = None
    occupied_streak: int = 0

    # Policy & approval state
    status: str = "idle"  # idle | occupied | counting_vacant | tier1_auto_off | pending_approval | verified | fail_safe_hold
    status_detail: str = "Waiting for AMB82-Mini telemetry over USB Serial."
    pending_proposal: Optional[dict[str, Any]] = None

    # Closed-loop WebSocket command/ACK tracking
    pending_command: Optional[dict[str, Any]] = None
    last_ack: Optional[dict[str, Any]] = None
    audit: list[dict[str, Any]] = field(default_factory=list)

    # Connected WebSocket clients: ws -> role ("phone" | "console")
    clients: dict[Any, str] = field(default_factory=dict)

    def _now(self) -> float:
        return float(self.clock())

    def _log(self, stage: str, title: str, detail: str) -> None:
        self.audit.insert(0, {
            "id": uuid4().hex[:8],
            "at": round(self._now(), 3),
            "stage": stage,
            "title": title,
            "detail": detail,
        })
        if len(self.audit) > 80:
            self.audit.pop()

    def connected_phones(self) -> int:
        return sum(1 for role in self.clients.values() if role == "phone")

    def frame_age(self, now: Optional[float] = None) -> Optional[float]:
        if self.last_sample_at is None:
            return None
        return max(0.0, (now if now is not None else self._now()) - self.last_sample_at)

    def vacant_seconds(self, now: Optional[float] = None) -> float:
        if self.vacant_since is None:
            return 0.0
        return max(0.0, (now if now is not None else self._now()) - self.vacant_since)

    def _is_fresh(self, now: float) -> bool:
        age = self.frame_age(now)
        return age is not None and age <= self.max_frame_age_sec

    def _revoke_pending(self, reason: str) -> bool:
        if self.pending_proposal is None:
            return False
        revoked_id = self.pending_proposal["id"]
        self.pending_proposal = None
        self.version += 1
        self._log("Adapt", "Pending proposal revoked", f"Proposal {revoked_id[:8]} revoked: {reason}")
        return True

    def _issue_command(self, target_devices: dict[str, str], reason: str, tier: str) -> dict[str, Any]:
        cmd_id = f"cmd-{uuid4().hex[:6]}"
        sent_at = self._now()
        self.devices = dict(target_devices)
        self.version += 1
        cmd = {
            "type": "command",
            "cmd_id": cmd_id,
            "room": self.room,
            "tier": tier,
            "reason": reason,
            "devices": dict(self.devices),
            "sent_at": sent_at,
        }
        self.pending_command = {
            "cmd_id": cmd_id,
            "tier": tier,
            "reason": reason,
            "devices": dict(self.devices),
            "sent_at": sent_at,
            "acked": False,
        }
        self._log("Act", f"Command sent ({tier})", f"{cmd_id}: {self.devices} — {reason}")
        return cmd

    def _stage_proposal(self, target_devices: dict[str, str], reason: str, scope: str) -> None:
        # Avoid re-creating identical pending proposal
        if (
            self.pending_proposal is not None
            and self.pending_proposal["target_devices"] == target_devices
            and self.pending_proposal["scope"] == scope
        ):
            return
        self.version += 1
        self.pending_proposal = {
            "id": uuid4().hex,
            "version": self.version,
            "room": self.room,
            "scope": scope,  # "projector_standby" | "mid_schedule_shutdown"
            "target_devices": dict(target_devices),
            "reason": reason,
            "created_at": self._now(),
        }
        self.status = "pending_approval"
        self.status_detail = reason
        self._log("Plan", "Facilities approval requested (Tier 2)", f"{scope}: {reason}")

    def ingest_telemetry(
        self, person_count: int, confidence: float, source: str = "amb82-npu"
    ) -> tuple[dict[str, Any], Optional[dict[str, Any]]]:
        """Process one AMB82/bridge occupancy reading. Returns (snapshot, optional_ws_command)."""
        now = self._now()
        if person_count < 0:
            raise RoomPolicyError("person_count must be >= 0.")
        if not (0.0 <= confidence <= 1.0):
            raise RoomPolicyError("confidence must be between 0.0 and 1.0.")

        self.last_count = int(person_count)
        self.last_confidence = round(float(confidence), 3)
        self.last_source = source
        self.last_sample_at = now
        outbound_cmd: Optional[dict[str, Any]] = None

        # 1. Fail-safe: Wall Manual Override always wins
        if self.wall_override:
            self.vacant_since = None
            self.occupied_streak = 0
            self._revoke_pending("Wall manual override is active on classroom panel.")
            self.status = "fail_safe_hold"
            self.status_detail = "Wall manual override active — appliances held On."
            return self.snapshot(now), None

        # 2. Fail-safe: Low confidence frame -> hold appliances ON
        if self.last_confidence < self.min_confidence:
            self.vacant_since = None
            self.occupied_streak = 0
            self._revoke_pending(f"Low confidence reading ({self.last_confidence:.2f} < {self.min_confidence:.2f}).")
            self.status = "fail_safe_hold"
            self.status_detail = (
                f"Uncertain CV confidence ({self.last_confidence:.2f}) — fail-safe holding appliances On."
            )
            self._log("Adapt", "Low-confidence safety hold", self.status_detail)
            return self.snapshot(now), None

        # 3. Occupied -> Instant hold + revoke any proposal + auto-wake Lights/Fans
        if self.last_count >= 1:
            self.vacant_since = None
            self.occupied_streak += 1
            revoked = self._revoke_pending(f"{self.last_count} person(s) detected in {self.room}.")
            self.status = "occupied"
            self.status_detail = f"Occupied ({self.last_count} person, conf {self.last_confidence:.2f})."
            if revoked:
                self.status_detail += " Pending shutdown revoked."

            # Auto-wake Lights & Fans if they were turned off (after wake_frames_required)
            needs_wake = self.devices["Lights"] != "On" or self.devices["Fans"] != "On"
            if needs_wake and self.occupied_streak >= self.wake_frames_required:
                target = dict(self.devices)
                target["Lights"] = "On"
                target["Fans"] = "On"
                outbound_cmd = self._issue_command(
                    target,
                    f"Auto-wake: {self.last_count} person(s) verified across {self.occupied_streak} frames.",
                    tier="auto_wake",
                )
                self.status_detail = f"Auto-woke Lights & Fans for {self.last_count} occupant(s)."
            return self.snapshot(now), outbound_cmd

        # 4. Vacant (person_count == 0, confidence >= min_confidence)
        self.occupied_streak = 0
        if self.vacant_since is None:
            self.vacant_since = now
            self._log("Sense", "Vacancy timer started", f"{self.room} vacant (conf {self.last_confidence:.2f}).")

        elapsed = self.vacant_seconds(now)
        if elapsed < self.vacant_threshold_sec:
            remaining = max(0.0, self.vacant_threshold_sec - elapsed)
            self.status = "counting_vacant"
            self.status_detail = f"Vacant {elapsed:.1f}s / {self.vacant_threshold_sec:.0f}s ({remaining:.1f}s left)."
            return self.snapshot(now), None

        # 5. Sustained vacancy reached -> Apply Tiered Policy!
        if self.class_scheduled:
            # Mid-schedule vacancy: NEVER auto-shutdown; require Facilities approval for all devices
            if self.devices != {"Lights": "Off", "Fans": "Off", "Projector": "Standby"}:
                self._stage_proposal(
                    {"Lights": "Off", "Fans": "Off", "Projector": "Standby"},
                    f"Mid-schedule vacancy ({elapsed:.0f}s) while class is still booked. Facilities approval required.",
                    scope="mid_schedule_shutdown",
                )
            else:
                self.status = "verified"
                self.status_detail = "Room already in verified standby."
            return self.snapshot(now), None

        # Unscheduled sustained vacancy:
        # Tier 1: Auto-shutdown Lights & Fans immediately
        if self.devices["Lights"] == "On" or self.devices["Fans"] == "On":
            target = dict(self.devices)
            target["Lights"] = "Off"
            target["Fans"] = "Off"
            outbound_cmd = self._issue_command(
                target,
                f"Tier 1 auto-off: {elapsed:.0f}s sustained vacancy with no class scheduled.",
                tier="tier1_auto_off",
            )
            self.status = "tier1_auto_off"
            self.status_detail = "Tier 1 auto-off sent for Lights & Fans. Projector Standby awaits Facilities approval."

        # Tier 2: Projector Standby ALWAYS requires Facilities Supervisor approval
        if self.devices["Projector"] == "On":
            target = dict(self.devices)
            target["Lights"] = "Off"
            target["Fans"] = "Off"
            target["Projector"] = "Standby"
            self._stage_proposal(
                target,
                f"Lights/Fans auto-off complete. Approve Projector → Standby (protects lamp cooldown).",
                scope="projector_standby",
            )
        else:
            self.status = "verified"
            self.status_detail = "Lights & Fans Off; Projector in verified Standby."

        return self.snapshot(now), outbound_cmd

    def set_schedule(
        self, class_scheduled: bool, vacant_threshold_sec: Optional[float] = None
    ) -> dict[str, Any]:
        self.class_scheduled = bool(class_scheduled)
        if vacant_threshold_sec is not None:
            if not (2.0 <= vacant_threshold_sec <= 120.0):
                raise RoomPolicyError("vacant_threshold_sec must be between 2 and 120 seconds.")
            self.vacant_threshold_sec = float(vacant_threshold_sec)
        self.version += 1
        self._revoke_pending("Timetable state changed — re-evaluating room policy.")
        label = "Class SCHEDULED (mid-schedule approval guard active)" if self.class_scheduled else "No class scheduled (relocated / free)"
        self._log("Think", "Timetable state updated", f"{self.room}: {label}.")
        self.status_detail = label
        return self.snapshot()

    def set_wall_override(self, active: bool, source: str = "phone") -> tuple[dict[str, Any], Optional[dict[str, Any]]]:
        self.wall_override = bool(active)
        self.version += 1
        outbound_cmd: Optional[dict[str, Any]] = None
        if self.wall_override:
            self.vacant_since = None
            self._revoke_pending(f"Wall manual override activated ({source}).")
            self.status = "fail_safe_hold"
            self.status_detail = f"Wall manual override ON ({source}) — appliances locked On."
            self._log("Sense", "Wall manual override ON", f"Triggered from {source}. All auto/pending shutdowns blocked.")
            if self.devices != ACTIVE_DEVICES:
                outbound_cmd = self._issue_command(
                    dict(ACTIVE_DEVICES),
                    f"Manual wall override ON ({source}) — restoring appliances.",
                    tier="manual_override",
                )
        else:
            self.status = "idle"
            self.status_detail = f"Wall manual override released ({source}). Resuming live occupancy watch."
            self._log("Sense", "Wall manual override OFF", f"Released from {source}.")
        return self.snapshot(), outbound_cmd

    def review_proposal(
        self, proposal_id: str, decision: str, role: str = "Facilities supervisor"
    ) -> tuple[dict[str, Any], Optional[dict[str, Any]]]:
        """Tier 2 approval with atomic commit-time live occupancy, freshness, and override re-check."""
        now = self._now()
        if self.pending_proposal is None or self.pending_proposal["id"] != proposal_id:
            raise RoomPolicyError("Proposal is stale or already revoked. Review the latest room evidence.")

        if decision == "reject":
            pid = self.pending_proposal["id"][:8]
            self.pending_proposal = None
            self.version += 1
            self.status = "fail_safe_hold"
            self.status_detail = f"{role} rejected proposal {pid}. Appliances remain unchanged."
            self._log("Explain", "Tier 2 proposal rejected", self.status_detail)
            return self.snapshot(now), None

        if decision != "approve":
            raise RoomPolicyError("decision must be 'approve' or 'reject'.")

        # === COMMIT-TIME SAFETY RE-CHECK ===
        if self.wall_override:
            self._revoke_pending("Commit-time re-check blocked: wall override is ON.")
            self.status = "fail_safe_hold"
            self.status_detail = "Stale approval blocked: wall manual override is active."
            raise RoomPolicyError(self.status_detail)

        if not self._is_fresh(now):
            age = self.frame_age(now)
            self._revoke_pending(f"Commit-time re-check blocked: camera feed stale ({age:.1f}s old).")
            self.status = "fail_safe_hold"
            self.status_detail = "Stale approval blocked: AMB82 telemetry is stale (> 5s). Keep devices On."
            raise RoomPolicyError(self.status_detail)

        if self.last_count is None or self.last_count > 0:
            self._revoke_pending(f"Commit-time re-check blocked: {self.last_count} person(s) detected.")
            self.status = "occupied"
            self.status_detail = f"Stale approval blocked: {self.last_count} person(s) returned to {self.room}!"
            raise RoomPolicyError(self.status_detail)

        if self.last_confidence is None or self.last_confidence < self.min_confidence:
            self._revoke_pending("Commit-time re-check blocked: low confidence reading.")
            self.status = "fail_safe_hold"
            self.status_detail = "Stale approval blocked: uncertain CV confidence."
            raise RoomPolicyError(self.status_detail)

        if self.vacant_seconds(now) < self.vacant_threshold_sec:
            self._revoke_pending("Commit-time re-check blocked: vacancy interval incomplete.")
            raise RoomPolicyError("Sustained vacancy window is no longer satisfied.")

        # Commit approved Tier 2 command!
        proposal = self.pending_proposal
        self.pending_proposal = None
        cmd = self._issue_command(
            proposal["target_devices"],
            f"Tier 2 approved by {role} ({proposal['scope']}); commit-time occupancy re-check passed.",
            tier="tier2_approved",
        )
        self.status = "verified"
        self.status_detail = f"Approved by {role}. Command {cmd['cmd_id']} pushed to Android controller."
        return self.snapshot(now), cmd

    def handle_phone_ack(self, cmd_id: str, reported_devices: dict[str, str]) -> dict[str, Any]:
        now = self._now()
        latency_ms = None
        matched = False
        if self.pending_command and self.pending_command["cmd_id"] == cmd_id:
            latency_ms = round((now - self.pending_command["sent_at"]) * 1000.0, 1)
            matched = reported_devices == self.pending_command["devices"]
            self.pending_command["acked"] = matched

        self.last_ack = {
            "cmd_id": cmd_id,
            "verified": matched,
            "latency_ms": latency_ms,
            "devices": dict(reported_devices),
            "at": round(now, 3),
        }
        if matched:
            self._log(
                "Verify",
                f"Phone ACK verified ({latency_ms} ms)" if latency_ms is not None else "Phone ACK verified",
                f"{cmd_id} confirmed on Android panel: {reported_devices}.",
            )
        else:
            self.status = "fail_safe_hold"
            self.status_detail = f"Readback mismatch on {cmd_id} — flagged NEEDS_REVIEW."
            self._log("Verify", "Readback mismatch — NEEDS_REVIEW", f"Reported {reported_devices} != expected {self.devices}.")
        return self.snapshot(now)

    def reset(self) -> tuple[dict[str, Any], dict[str, Any]]:
        self.devices = dict(ACTIVE_DEVICES)
        self.class_scheduled = False
        self.wall_override = False
        self.last_count = None
        self.last_confidence = None
        self.last_source = "none"
        self.last_sample_at = None
        self.vacant_since = None
        self.occupied_streak = 0
        self.pending_proposal = None
        self.last_ack = None
        self.audit = []
        self.status = "idle"
        self.status_detail = "Room reset to All On. Waiting for AMB82-Mini telemetry."
        cmd = self._issue_command(dict(ACTIVE_DEVICES), "Demo reset — restoring all classroom appliances On.", tier="reset")
        return self.snapshot(), cmd

    def snapshot(self, now: Optional[float] = None) -> dict[str, Any]:
        t = now if now is not None else self._now()
        age = self.frame_age(t)
        stale = age is not None and age > self.max_frame_age_sec

        # Auto-flag stale on read so dashboards immediately see camera disconnects
        status = self.status
        detail = self.status_detail
        if stale and not self.wall_override and status not in {"idle", "verified"}:
            status = "fail_safe_hold"
            detail = f"AMB82 feed stale ({age:.1f}s > {self.max_frame_age_sec:.0f}s) — fail-safe holding appliances On."

        return {
            "room": self.room,
            "version": self.version,
            "status": status,
            "status_detail": detail,
            "devices": dict(self.devices),
            "class_scheduled": self.class_scheduled,
            "wall_override": self.wall_override,
            "policy": {
                "vacant_threshold_sec": self.vacant_threshold_sec,
                "max_frame_age_sec": self.max_frame_age_sec,
                "min_confidence": self.min_confidence,
                "wake_frames_required": self.wake_frames_required,
            },
            "telemetry": {
                "person_count": self.last_count,
                "confidence": self.last_confidence,
                "source": self.last_source,
                "frame_age_sec": round(age, 2) if age is not None else None,
                "stale": stale,
                "vacant_seconds": round(self.vacant_seconds(t), 2),
                "occupied_streak": self.occupied_streak,
            },
            "connected_phones": self.connected_phones(),
            "pending_proposal": dict(self.pending_proposal) if self.pending_proposal else None,
            "pending_command": dict(self.pending_command) if self.pending_command else None,
            "last_ack": dict(self.last_ack) if self.last_ack else None,
            "audit": list(self.audit[:30]),
        }

    async def broadcast(self, message: dict[str, Any], target_role: Optional[str] = None) -> None:
        dead = []
        for ws, role in list(self.clients.items()):
            if target_role is not None and role != target_role:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.clients.pop(ws, None)
