from flask import Blueprint, jsonify
from services.invoice_comparator import compare_invoices_to_pos
from data.hardcoded_data import load_data

invoice_blueprint = Blueprint('invoice', __name__)

@invoice_blueprint.route('/compare', methods=['GET'])
def compare():
    invoices, pos = load_data()
    valid_items, mismatches = compare_invoices_to_pos(invoices, pos)
    return jsonify({
        "valid_items": valid_items,
        "mismatches": mismatches
    })

@invoice_blueprint.route('/compare/<po_id>', methods=['GET'])
def compare_by_po(po_id):
    invoices, pos = load_data()

    # Filter by the given po_id
    filtered_invoices = [inv for inv in invoices if inv.purchase_order_id == po_id]
    filtered_pos = [po for po in pos if po.purchase_order_id == po_id]

    if not filtered_invoices and not filtered_pos:
        return jsonify({"error": f"No data found for PO ID '{po_id}'"}), 404

    valid_items, mismatches = compare_invoices_to_pos(filtered_invoices, filtered_pos)
    return jsonify({
        "po_id": po_id,
        "valid_items": valid_items,
        "mismatches": mismatches
    })