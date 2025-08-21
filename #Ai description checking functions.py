#Ai description checking functions

import hashlib

def _norm(s): 
    return (s or "").strip().lower()

def _assign_invoice_line_numbers(invoice_id: str, items: list[dict]) -> list[dict]:
    out = []
    for idx, it in enumerate(items, start=1):  # 1-based index
        key_src = f"{invoice_id}|{idx}|{it.get('SellerPartNumber','')}|{it.get('ItemDescription','')}"
        uid = hashlib.sha1(key_src.encode()).hexdigest()[:12]
        it = {**it}
        it.setdefault("invoice_line_no", idx)
        it["invoice_line_uid"] = f"inv_{uid}"
        out.append(it)
    return out

def validate_and_match_invoice_items_against_po_strict(
    invoice_id: str,
    invoice_items: list[dict],
    po_items: list[dict],
    ai_match_fn=None,                 # callable(invoice_wo_ids, po_wo_ids) -> {"matches":[...], "unmatched_po_lines":[...]}
    accept_threshold: float = 0.80,
):
    """
    Strict identity-only validator:
      - Fails if invoice has more lines than PO (no extras logic here).
      - Enforces one-to-one mapping across ID + DESC.
      - Uses DESC fallback only for ID-unmatched lines vs unused PO lines.
    """
    # 0) Hard count rule
    if len(invoice_items) > len(po_items):
        return {
            "po_id": po_items[0].get("prchseordr_id") if po_items else None,
            "invoice_id": invoice_id,
            "pass": False,
            "fail_reasons": [{
                "reason": "invoice-has-more-lines-than-po",
                "invoice_line_count": len(invoice_items),
                "po_line_count": len(po_items),
            }],
            "id_matches": [],
            "desc_matches": [],
            "unmatched_invoice_lines": [
                {"invoice_line_no": i+1, "description": it.get("ItemDescription","")}
                for i, it in enumerate(invoice_items[len(po_items):])
            ],
            "unused_po_lines": [{"po_line_no": p.get("line_no"), "description": p.get("description","")} for p in po_items],
        }

    # 1) Stable numbering
    invoice_items = _assign_invoice_line_numbers(invoice_id, invoice_items)

    # 2) Build PO maps (by vendor_part) and an index by line_no
    po_by_id: dict[str, list[dict]] = {}
    po_by_line_no = {}
    for po in po_items:
        po_by_line_no[po.get("line_no")] = po
        vid = _norm(po.get("vendor_part"))
        if vid:
            po_by_id.setdefault(vid, []).append(po)

    # 3) Exact ID matches — strict consume-once
    id_matches = []
    used_po_line_nos = set()
    matched_invoice_uids = set()
    inv_unmatched_for_desc = []

    # Group invoice lines by SellerPartNumber
    inv_by_id: dict[str, list[dict]] = {}
    for inv in invoice_items:
        sid = _norm(inv.get("SellerPartNumber"))
        if sid:
            inv_by_id.setdefault(sid, []).append(inv)

    # Pair by order, but consume each PO line at most once
    for sid, inv_list in inv_by_id.items():
        po_list = po_by_id.get(sid, [])
        for i, inv in enumerate(inv_list):
            if i < len(po_list):
                po_ref = po_list[i]  # consume the i-th PO occurrence
                pln = po_ref.get("line_no")
                if pln in used_po_line_nos:
                    # shouldn't happen if PO IDs are unique per occurrence, but guard anyway
                    inv_unmatched_for_desc.append(inv)
                    continue
                id_matches.append({
                    "type": "id_match",
                    "invoice_line_no": inv["invoice_line_no"],
                    "invoice_line_uid": inv["invoice_line_uid"],
                    "invoice_description": inv.get("ItemDescription",""),
                    "po_line_no": pln,
                    "po_description": po_ref.get("description",""),
                    "confidence": 1.0,
                })
                used_po_line_nos.add(pln)
                matched_invoice_uids.add(inv["invoice_line_uid"])
            else:
                # More occurrences on invoice than PO -> leave for DESC step (will likely fail if no unused PO lines remain)
                inv_unmatched_for_desc.append(inv)

    # Add invoice lines with missing/bad IDs to DESC pool
    for inv in invoice_items:
        if inv["invoice_line_uid"] in matched_invoice_uids:
            continue
        sid = _norm(inv.get("SellerPartNumber"))
        if not sid or sid not in po_by_id:
            inv_unmatched_for_desc.append(inv)

    # 4) DESC fallback only against UNUSED PO lines (strict one-to-one across ID + DESC)
    desc_matches = []
    if ai_match_fn and inv_unmatched_for_desc:
        po_unused = [po for po in po_items if po.get("line_no") not in used_po_line_nos]
        if po_unused:
            ai_invoice_payload = [
                {"invoice_line_no": inv["invoice_line_no"], "description": inv.get("ItemDescription","")}
                for inv in inv_unmatched_for_desc
            ]
            ai_po_payload = [
                {"po_line_no": po.get("line_no"), "description": po.get("description","")}
                for po in po_unused
            ]
            ai_resp = ai_match_fn(ai_invoice_payload, ai_po_payload)

            # One-to-one within DESC, and also against ID-consumed lines
            desc_used_po = set()
            desc_used_inv = set()
            for m in ai_resp.get("matches", []):
                if m.get("decision") != "match":
                    continue
                if m.get("matched_po_line_no") is None:
                    continue
                if float(m.get("confidence", 0.0)) < accept_threshold:
                    continue
                iln = int(m["invoice_line_no"])
                pln = int(m["matched_po_line_no"])
                if pln in used_po_line_nos or pln in desc_used_po:
                    continue
                if iln in desc_used_inv:
                    continue

                # accept
                inv = next((x for x in inv_unmatched_for_desc if x["invoice_line_no"] == iln), None)
                po  = po_by_line_no.get(pln)
                if not inv or not po:
                    continue
                desc_matches.append({
                    "type": "desc_match",
                    "invoice_line_no": iln,
                    "invoice_line_uid": inv["invoice_line_uid"],
                    "invoice_description": inv.get("ItemDescription",""),
                    "po_line_no": pln,
                    "po_description": po.get("description",""),
                    "confidence": float(m.get("confidence", 0.0)),
                    "evidence_tokens": m.get("evidence_tokens", []),
                })
                desc_used_po.add(pln)
                desc_used_inv.add(iln)

            # Merge used PO lines from DESC into the global used set
            used_po_line_nos |= desc_used_po

    # 5) Final strict decision: every invoice line must be matched (count already ≤ PO count)
    matched_invoice_nos = {m["invoice_line_no"] for m in id_matches} | {m["invoice_line_no"] for m in desc_matches}
    unmatched_invoice_lines = [
        {"invoice_line_no": inv["invoice_line_no"], "description": inv.get("ItemDescription","")}
        for inv in invoice_items
        if inv["invoice_line_no"] not in matched_invoice_nos
    ]
    unused_po_lines = [
        {"po_line_no": po.get("line_no"), "description": po.get("description","")}
        for po in po_items if po.get("line_no") not in used_po_line_nos
    ]

    all_matched = len(unmatched_invoice_lines) == 0
    return {
        "po_id": po_items[0].get("prchseordr_id") if po_items else None,
        "invoice_id": invoice_id,
        "pass": all_matched,
        "fail_reasons": ([] if all_matched else [{"reason": "unmatched-invoice-lines", "lines": [x["invoice_line_no"] for x in unmatched_invoice_lines]}]),
        "id_matches": id_matches,
        "desc_matches": desc_matches,
        "unmatched_invoice_lines": unmatched_invoice_lines,
        "unused_po_lines": unused_po_lines,
        "accept_threshold": accept_threshold
    }

########################################################################


def chatgpt_match_by_description(invoice_items_wo_ids: list[dict], po_items_wo_ids: list[dict]) -> dict:
    """
    Expects two arrays:
      invoice_items_wo_ids = [{"invoice_line_no": int, "description": str}, ...]
      po_items_wo_ids      = [{"po_line_no": int,      "description": str}, ...]
    Returns:
      {"matches":[{...}], "unmatched_po_lines":[...]}
    """
    # PSEUDOCODE: call your LLM here and return parsed JSON.
    # Use temperature=0 and the system/user prompts we already drafted.
    raise NotImplementedError

def validate_invoice_items_against_po(invoice_items, po_items):
    resp = validate_and_match_invoice_items_against_po(
        invoice_id=str(invoice_items[0].get('invoiceID', 'unknown')),
        invoice_items=invoice_items,
        po_items=po_items,
        ai_match_fn=None  # set to chatgpt_match_by_description when ready
    )
    return resp["id_validation"]["all_invoice_ids_found_in_po"]