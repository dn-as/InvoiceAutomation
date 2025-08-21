from dataclasses import dataclass

# Data Expected:
# STRING:        PO #
# STRING:        Invoice #
# STRING:        Invoice Date
# STRING:        Invoice Total
# STRING:        GL Entity ID
 
# BOOL:           hasTaxes
# DICT:            TaxInfo   
# {
#     STRING:        Authority ID
#     STRING:        GL Account
#     STRING:        Tax Base
#     STRING:        Rate
#     STRING:        Tax Amount
# }
#     Note: TaxInfo is empty if hasTaxes is false
#     Note: TaxInfo can be found by looking up 
#                   GL Entity ID on the Notion Document 
#                   with relevant GL Entities
 
# BOOLEAN:    hasExtraCharges
# ARRAY:          Charges
# [
#     {
#         STRING:        Quantity
#         STRING:        UnitCost
#             Note: This is the charge written on the invoice
#         STRING:        CostCategory
#         STRING:        UnitCost
#         STRING:        Description
#     },
#     {Repeat Previous Structure}
# ]
 
# BOOLEAN:    ClosePO
#     Note: This is done by comparing a PO's
#                   Amount Vouchered vs Amount Received
 
# STRING:        Invoice File Path





@dataclass
class InvoiceItem:
    purchase_order_id: str
    invoice_number: str
    invoice_date: str
    invoice_total: str
    gl_entity_id: str
    hasTaxes: bool
    taxInfo: dict
    item_id: str
    price: float
    unit: str
    quantity: int


@dataclass
class TaxInfo:
    authority_id: str
    gl_account: str
    tax_base: str
    rate: str
    tax_amount: str

@dataclass
class POItem:
    purchase_order_id: str
    invoice_number: str
    invoice_date: str
    invoice_total: str
    gl_entity_id: str
    hasTaxes: bool
    taxInfo: dict
    hasExtraCharges: bool
    charges: list
    closePo: bool



@dataclass
class Charges:
    quantity: str
    unit_cost: str
    cost_category: str
    description: str