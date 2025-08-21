from models.invoice_models import InvoiceItem, POItem

def load_data():
    po_data = [
        POItem("001", "ITEM001",10, "pcs", 10),
        POItem("001", "ITEM002", 15.0, "pcs", 5),
        POItem("002", "ITEM003", 20.0, "box", 6)
    ]

    inv_data = [
        InvoiceItem("001", "ITEM001", 10.0, "pcs", 7),
        InvoiceItem("001", "ITEM001", 10.0, "pcs", 5),
        InvoiceItem("001", "ITEM002", 15.0, "pcs", 5),  # Over
        InvoiceItem("002", "ITEM003", 20.0, "pack", 2), # Unit mismatch
        InvoiceItem("003", "ITEM004", 30.0, "pcs", 1)   # Not in PO
    ]

    return inv_data, po_data