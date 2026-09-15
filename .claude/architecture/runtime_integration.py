"""Deterministic Deputy runtime integration facade.

This module connects the sealed architecture contracts to the existing Skill Engine
and Store without introducing a second runtime, memory, authority, or task database.
It is deliberately provider-neutral and fail-closed.
"""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
try:
    from .brain_router import route
    from .work_orchestrator import create_node, validate_graph
except ImportError:
    from brain_router import route
    from work_orchestrator import create_node, validate_graph

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / ".claude" / "skills"
if str(SKILLS) not in sys.path:
    sys.path.insert(0, str(SKILLS))

class RuntimeBlocked(RuntimeError):
    pass


def _stable(*parts):
    return hashlib.sha256("|".join(str(x) for x in parts).encode()).hexdigest()[:16]


def resolve_truth(sources):
    """Resolve a primitive without silently averaging contradictory authority."""
    rows = list(sources or [])
    if not rows:
        raise RuntimeBlocked("NO_SOURCE")
    for row in rows:
        if not row.get("provenance"):
            raise RuntimeBlocked("MISSING_PROVENANCE")
    live = [r for r in rows if r.get("authority") == "current" and r.get("freshness") != "stale"]
    if not live:
        raise RuntimeBlocked("NO_CURRENT_AUTHORITY")
    values = {json.dumps(r.get("value"), sort_keys=True, default=str) for r in live}
    if len(values) > 1:
        raise RuntimeBlocked("CONFLICTING_AUTHORITATIVE_SOURCES")
    return {"value": live[0].get("value"), "authority": live[0].get("owner"),
            "provenance": [r["provenance"] for r in live], "status": "RESOLVED"}


class DeputyRuntime:
    """One Deputy identity, one Store, one Action Runtime boundary."""
    identity = "DEPUTY"

    def __init__(self, *, state_dir=None, knowledge=None, vault=None, capabilities=None):
        self._store_module = None
        import store
        self._store_module = store
        self.store = store.get(state_dir)
        self.knowledge = knowledge
        self.vault = vault
        self.capabilities = capabilities or {}
        if self.identity != "DEPUTY":
            raise RuntimeBlocked("INVALID_DEPUTY_IDENTITY")

    def discover_capability(self, capability_id):
        row = self.capabilities.get(capability_id)
        if not row or row.get("certification") != "certified" or row.get("registered") is not True:
            raise RuntimeBlocked("CAPABILITY_UNAVAILABLE")
        return dict(row)

    def plan(self, request, *, owner="GEV", source=None, events=None):
        routing = route(request)
        if any(x["brain_id"] not in {b["id"] for b in json.loads((Path(__file__).parent / "professional_brains.json").read_text())["brains"]} for x in routing["selected_brains"]):
            raise RuntimeBlocked("UNSUPPORTED_BRAIN")
        graph = [create_node("ACTION_PLAN", request, owner=owner, brains=[x["brain_id"] for x in routing["selected_brains"]], source=source, approval="NOT_REQUIRED")]
        errors = validate_graph(graph)
        if errors: raise RuntimeBlocked("INVALID_WORK_GRAPH:" + ";".join(errors))
        payload = {"runtime":"DEPUTY", "identity":self.identity, "request":request,
                   "routing":routing, "events":events or [], "graph":graph,
                   "authority":{"writes":"ACTION_RUNTIME_ONLY", "approval":"GEV_REQUIRED_FOR_MATERIAL_MUTATION"},
                   "synthesis":{"required":routing["synthesis_required"], "status":"ONE_DEPUTY_CONTEXT"}}
        oid = _stable("action-plan", request, owner)
        saved = self.store.record("commitments", oid, payload)
        return {"status":"PLANNED", "op_id":oid, "duplicate":saved["status"] == "DUPLICATE", **payload}

    def load_plan(self, op_id):
        row = self.store.get("commitments", op_id)
        if not row: raise RuntimeBlocked("PLAN_UNAVAILABLE")
        return row

    def complete(self, node, evidence):
        updated = dict(node); updated["status"] = "VERIFIED"; updated["evidence"] = evidence
        errors = validate_graph([updated])
        if errors: raise RuntimeBlocked("COMPLETION_EVIDENCE_REQUIRED")
        return updated

    def knowledge_context(self, query):
        if not self.knowledge: raise RuntimeBlocked("KNOWLEDGE_UNAVAILABLE")
        return self.knowledge.search(query)

    def vault_context(self, reference_id):
        if not self.vault: raise RuntimeBlocked("VAULT_UNAVAILABLE")
        return self.vault.vault_reference(reference_id)

    def strategy_assessment(self, strategy, *, evidence=None, kpis=None, capacity=None):
        """Produce a non-mutating Strategy/PMO assessment; execution remains approval-bound."""
        evidence = list(evidence or []); kpis = list(kpis or [])
        gaps = []
        if not kpis: gaps.append("MISSING_KPI")
        if not evidence: gaps.append("MISSING_CURRENT_STATE_EVIDENCE")
        if capacity is not None and capacity.get("required", 0) > capacity.get("available", 0):
            gaps.append("CAPACITY_CONTRADICTION")
        return {"status":"ANALYSIS", "lifecycle":"DIAGNOSIS", "strategy":strategy,
                "gaps":gaps, "recommendation_required":bool(gaps),
                "authority":"NON_MUTATING_ANALYSIS", "owner_decision_required":bool(gaps)}

    def reconcile_inbound(self, event, *, existing_ids=None):
        """Normalize untrusted inbound evidence without granting authority or creating tasks."""
        if not event.get("provenance") or event.get("trusted_authority"):
            raise RuntimeBlocked("UNTRUSTED_INPUT_BOUNDARY")
        eid = event.get("source_id") or _stable(event.get("channel"), event.get("text"))
        duplicate = eid in set(existing_ids or [])
        classes = list(event.get("classes") or ["NO_ACTION"])
        return {"event_id":eid, "duplicate":duplicate, "classes":classes,
                "status":"PROPOSAL_ONLY", "authority_granted":False,
                "canonical_knowledge":False, "approval_required":any(c in classes for c in ("ACTION","DECISION_REQUIRED"))}

    def compose_output(self, output_type, *, template=None, provenance=None):
        """Resolve output readiness without becoming a second Design System."""
        if not provenance: raise RuntimeBlocked("MISSING_PROVENANCE")
        if not template: return {"status":"TEMPLATE_GAP", "output_type":output_type, "provenance":provenance}
        return {"status":"STRUCTURALLY_VALIDATED", "output_type":output_type,
                "template":template, "visual_certification":"REQUIRED", "provenance":provenance}

    def follow_through(self, nodes):
        """Return management exceptions from the same persisted work graph."""
        rows=[]
        for n in nodes:
            if n.get("status") in ("BLOCKED",) or n.get("status") not in ("VERIFIED", "COMPLETED"):
                rows.append({"id":n.get("id"), "status":n.get("status"), "owner":n.get("owner"),
                             "next_action":n.get("next_action"), "exception":n.get("status")})
        return {"status":"READY", "exceptions":rows, "views":["DAILY","WEEKLY","MONTHLY"],
                "authority":"COMMAND_CENTER_OPERATIONAL_STATE"}

    def prepare_material_action(self, action):
        return {"status":"APPROVAL_REQUIRED", "action":action, "authority":"ACTION_RUNTIME", "approved":False}
