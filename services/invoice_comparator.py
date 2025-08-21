from typing import List, Dict, Tuple
from models.invoice_models import InvoiceItem, POItem

def compare_invoices_to_pos(invoices: List[InvoiceItem], pos: List[POItem]):
    po_map: Dict[Tuple[str, str], POItem] = {}
    po_remaining_qty: Dict[Tuple[str, str], int] = {}
    mismatches = []
    valid_items = []
   
    # Map each PO item and track its remaining quantity
    for po in pos:
        key = (po.purchase_order_id, po.item_id)
        po_map[key] = po
        po_remaining_qty[key] = po.quantity
      
    # Check each invoice line one-by-one
    for inv in invoices:
        key = (inv.purchase_order_id, inv.item_id)
        po_item = po_map.get(key)

        if not po_item:
            mismatches.append(f"{key}: Item not in PO")
            continue

        if inv.price != po_item.price:
            mismatches.append(f"{key}: Price mismatch")
            continue

        if inv.unit != po_item.unit:
            mismatches.append(f"{key}: Unit mismatch")
            continue

        remaining_qty = po_remaining_qty.get(key, 0)
        if inv.quantity > remaining_qty:
            mismatches.append(f"{key}: Invoiced {inv.quantity} exceeds remaining PO quantity {remaining_qty}")
            continue

        # Passed all checks — accept invoice
        po_remaining_qty[key] -= inv.quantity
        valid_items.append({
            'purchase_order_id': inv.purchase_order_id,
            'item_id': inv.item_id,
            'price': inv.price,
            'unit': inv.unit,
            'quantity': inv.quantity
        })

    return valid_items, mismatches
