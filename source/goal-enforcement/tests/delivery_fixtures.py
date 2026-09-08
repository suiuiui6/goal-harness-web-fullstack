from copy import deepcopy


def draft_delivery():
    return {
        "schema_version": 1,
        "profile": "web-fullstack",
        "contract": {
            "revision": 1,
            "outcome": "A user creates and reads their own note.",
            "actors": ["owner", "anonymous"],
            "flows": ["create then read", "reject anonymous write"],
            "non_goals": ["production deployment"],
            "constraints": ["retain the existing stack"],
            "unknowns": [],
            "delivery_target": "local-runnable",
            "approval": {
                "revision": 1,
                "confirmation_id": "fixture-approval-1",
                "source": "fixture://approval/1",
                "recorded_at": "2026-09-08T00:00:00+00:00",
            },
        },
        "slices": [],
        "criteria": [],
        "evidence": [],
        "invalidations": [],
    }


def valid_surface(applicability="reused"):
    return {
        "applicability": applicability,
        "rationale": "Covered by the existing application contract.",
        "evidence_ids": [],
    }


def draft_slice(slice_id="notes", criterion_ids=None):
    return {
        "slice_id": slice_id,
        "outcome": "The owner can persist a note.",
        "criterion_ids": list(criterion_ids or []),
        "depends_on": [],
        "surfaces": {
            name: valid_surface("changed" if name in {"api", "data"} else "reused")
            for name in ("data", "api", "ui", "authorization", "deployment")
        },
    }


def draft_criterion(criterion_id="notes.persist", slice_id="notes"):
    return {
        "criterion_id": criterion_id,
        "slice_id": slice_id,
        "outcome": "A saved note remains after a reload.",
        "revision": 1,
        "required": True,
        "status": "pending",
        "applicability_rationale": "Required by the approved flow.",
        "verification": {
            "entry_id": "fixture-check",
            "cwd": ".",
            "kind": "command",
            "entry": ["python", "-B", "fixture_check.py"],
            "environment_keys": [],
        },
        "evidence_ids": [],
        "judgment": None,
    }


def clone(value):
    return deepcopy(value)


def observed_evidence(
    evidence_id="E1",
    criterion_id="notes.persist",
    invalidation_count=0,
    started_at="2026-09-08T00:00:01+00:00",
    finished_at="2026-09-08T00:00:02+00:00",
):
    return {
        "evidence_id": evidence_id,
        "criterion_id": criterion_id,
        "revision": 1,
        "provenance": "observed_execution",
        "entry_id": "fixture-check",
        "cwd": ".",
        "started_at": started_at,
        "finished_at": finished_at,
        "observer": "fixture-runner",
        "result": "pass",
        "exit_code": 0,
        "source_fingerprint": {
            "algorithm": "sha256-manifest-v1",
            "value": "a" * 64,
            "scope": "regular-files-excluding-governance",
            "captured_at": started_at,
        },
        "environment": {
            "facts": {"python": "3.14.3"},
            "observed_at": started_at,
            "source": "fixture-runner",
            "status": "observed",
        },
        "isolation": {
            "mode": "isolated-snapshot",
            "snapshot_id": f"snapshot-{evidence_id}",
            "source_digest": "b" * 64,
            "observer": "fixture-runner",
        },
        "outputs": [
            {
                "path": ".codex/evidence/result.json",
                "sha256": "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
                "bytes": 2,
            }
        ],
        "invalidation_count": invalidation_count,
    }


def passing_judgment(
    evidence_id="E1",
    invalidation_count=0,
    at="2026-09-08T00:00:03+00:00",
):
    return {
        "result": "pass",
        "reason": "Observed persistence and authorization checks passed.",
        "source": "fixture://judgment",
        "at": at,
        "evidence_ids": [evidence_id],
        "invalidation_count": invalidation_count,
    }


def accepted_delivery():
    delivery = draft_delivery()
    criterion = draft_criterion()
    criterion["status"] = "pass"
    criterion["evidence_ids"] = ["E1"]
    criterion["judgment"] = passing_judgment()
    delivery["slices"] = [draft_slice(criterion_ids=[criterion["criterion_id"]])]
    delivery["criteria"] = [criterion]
    delivery["evidence"] = [observed_evidence()]
    return delivery
