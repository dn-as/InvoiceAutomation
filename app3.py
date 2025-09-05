# from flask import Flask, jsonify
# import requests
# import json
# import pyodbc
# import mysql.connector
# from decimal import Decimal
# from datetime import datetime
# # print(pyodbc.version)



# app = Flask(__name__)
# #DETERMINE TAX AUTHORITY ID BY GL_ENTITY OR JOB IDD 
# tax_mock=[]
# tax_mock = {
#     '01a99': 'nassau',
#     '02a99': 'nassau',
#     '03a99': 'nassau',
#     '06a99': 'florida',
#     '07a99': 'nassau',
#     '11a99':'maryland',
#     '12a99':'philadelphia',
#     '14a99':'florida',
#     '15a99':'massachusetts'
# }

# jobidtoglentity=[]
# #DETERMINE GL ENTITY BY JOB ID 
# #GET THE FIRST TWO LETTERS NOT THREE
# jobidtoglentity = {
#     'RE': '01a99',
#     'AL':'02a99',
#     'DA': '03a99',
#     'SC': '04a99',
#     'FL':'06a99',
#     'SF':'14a99',
#     'DC': '11a99',
#     'PE': '12a99',
#     'PL': '07a99',
#     'BO':'15a99',
#     'NC': '13a99',
# }

# glaccount=[]
# #DETERMINE GL account BY glentity #all lowercase
# glaccount = {
#     '01a99': '2401',
#     '02a99': '2401',
#     '03a99': '2401',
#     '06a99': '2411',
#     '07a99': '2401',
#     '11a99':'2407',
#     '12a99':'2404',
#     '14a99':'2411',
#     '15a99':'2409'
# }
# # po_mock = []

# # po_mock.append({
# #     'po_ID': '374618',
# #     'vendor_id': 'VEND001',
# #     'invoice_id': '2106432139',
# #     'invoice_date': '07292025',
# #     'invoice_total': 278.04,
# #     'gl_entity_id': '11R02',
# #     'total_entered': True,
# #     'effective_date': '07312025',
# #     'job_id': 'DCM397507-RIFB',
# #     'workorder_id': '960363',
# #     'item_id': 'CNTC0EA21K38DOT',
# #     "line_items": "line_item_1",
# #     'quantity': 2,
# #     'qtybilled': 1,
# #     'unit_cost': 266.250,
# #     'total_amount': 532.5,
# #     'purchase_order_description': 'CONC0EA21K38DOT TEMPERATURE CONTROL',
# #     'unit_of_measure': 'pcs',
# #     'ordered': 2,
# #     'received': 2,
# #     'vouchered': 1,
# #     'prchseordrlst_cst_rcvd_ap':200
# # })

# # po_mock.append({
# #     'po_ID': 'PO1001',
# #     'vendor_id': 'VEND001',
# #     'invoice_id': '',
# #     'invoice_date': '2025-07-25',
# #     'total_po': 1520.50,
# #     'gl_entity_id': '01A99',
# #     'total_entered': True,
# #     'effective_date': '2025-07-27',
# #     'job_id': 'JOB301',
# #     'workorder_id': 'WO401',
# #     'item_id': 'SPN-102',
# #     'quantity': 10,
# #     'qtybilled': 8,
# #     'unit_cost': 75.0002,
# #     'total_amount': 600.00,
# #     'purchase_order_description': 'Heavy-duty valve',
# #     'unit_of_measure': 'pcs',
# #     'ordered': 10,
# #     'received': 10,
# #     'vouchered': 9,
# #     'prchseordrlst_cst_rcvd_ap':200
# # })

# # po_mock.append({
# #     'po_ID': 'PO1001',
# #     'vendor_id': 'VEND001',
# #     'invoice_id': 'INV2001',
# #     'invoice_date': '2025-07-25',
# #     'total_po': 1520.50,
# #     'gl_entity_id': '01A99',
# #     'total_entered': True,
# #     'effective_date': '2025-07-27',
# #     'job_id': 'JOB301',
# #     'workorder_id': 'WO401',
# #     'item_id': 'SPN-100', 
# #     'quantity': 4,
# #     'qtybilled': 2,
# #     'unit_cost': 335.25,
# #     'total_amount': 670.50,
# #     'purchase_order_description': 'Control panel board',
# #     'unit_of_measure': 'pcs',
# #     'ordered': 4,
# #     'received': 4,
# #     'vouchered': 2,
# #    'prchseordrlst_cst_rcvd_ap':200
# # })
# #MySQL connection
# import pyodbc

# def getDBPORecordById(po_id: str):
#     """
#     Fetch PO lines with IMHSTRY quantities per line:
#       - qty_received_imhstry: sum of imhstry_qntty_rcvd on 'Receipt' rows (by item)
#       - qty_vouchered:        sum of imhstry_qntty_invcd_ap on 'AP Purchase' rows (by item)
#     Line -> item mapping is learned from 'Purchase' rows (their journal line numbers match PO lines).
#     Returns: List[dict]
#     """
#     conn = pyodbc.connect(
#         "DRIVER={ODBC Driver 17 for SQL Server};"
#         "SERVER=SAMPRODBSERVER;"
#         "DATABASE=DayNite_test;"
#         "Trusted_Connection=yes;"
#     )
#     cursor = conn.cursor()
#     try:
#         sql = """
#         DECLARE @po_id varchar(50) = ?;

#         -- 1) PO lines (LIST + LISTGN)
#         WITH all_lines AS (
#             SELECT
#                 'LIST'  AS line_source,
#                 prchseordr_rn,
#                 prchseordrlst_rn      AS ordrlst_rn,
#                 prchseordrlst_ln      AS line_no,
#                 prchseordrlst_vndr_prt_nmbr AS vendor_part,
#                 prchseordrlst_dscrptn       AS description,
#                 prchseordrlst_unt_msre      AS uom,
#                 prchseordrlst_qntty_ordrd   AS qty_ordered_line,
#                 prchseordrlst_qntty_rcvd    AS qty_received_line,
#                 prchseordrlst_unt_cst       AS unit_cost
#             FROM prchseordrlst
#             UNION ALL
#             SELECT
#                 'LISTGN',
#                 prchseordr_rn,
#                 prchseordrlstgn_rn,
#                 prchseordrlstgn_ln,
#                 prchseordrlstgn_vndr_prt_nmbr,
#                 prchseordrlstgn_dscrptn,
#                 prchseordrlstgn_unt_msre,
#                 prchseordrlstgn_qntty_ordrd,
#                 prchseordrlstgn_qntty_rcvd,
#                 prchseordrlstgn_unt_cst
#             FROM prchseordrlstgn
#         ),

#         -- 2) line_no -> item mapping from PURCHASE rows (journal line aligns with PO line)
#         line_to_item AS (
#             SELECT
#                 po_id_trim     = RTRIM(imhstry_ordr_id),
#                 line_no        = NULLIF(imhstry_srce_jrnl_ln, 0),
#                 invntryitm_rn  = MAX(NULLIF(invntryitm_rn, 0))
#             FROM imhstry
#             WHERE imhstry_ordr_type = 'P'
#               AND RTRIM(imhstry_ordr_id) = RTRIM(@po_id)
#               AND imhstry_srce_jrnl = 'Purchase'
#               AND ISNULL(imhstry_srce_jrnl_ln, 0) <> 0
#             GROUP BY RTRIM(imhstry_ordr_id), imhstry_srce_jrnl_ln
#         ),

#         -- 3) RECEIVED by PO + item (Receipt rows)
#         received_by_item AS (
#             SELECT
#                 po_id_trim = RTRIM(imhstry_ordr_id),
#                 invntryitm_rn,
#                 qty_received_imhstry =
#                     SUM(CASE WHEN imhstry_rvrsl = 'Y'
#                              THEN -TRY_CAST(imhstry_qntty_rcvd AS decimal(18,6))
#                              ELSE  TRY_CAST(imhstry_qntty_rcvd AS decimal(18,6))
#                         END)
#             FROM imhstry
#             WHERE imhstry_ordr_type = 'P'
#               AND RTRIM(imhstry_ordr_id) = RTRIM(@po_id)
#               AND imhstry_srce_jrnl = 'Receipt'
#             GROUP BY RTRIM(imhstry_ordr_id), invntryitm_rn
#         ),

#         -- 4) VOUCHERED by PO + item (AP Purchase rows)
#         vouchered_by_item AS (
#             SELECT
#                 po_id_trim = RTRIM(imhstry_ordr_id),
#                 invntryitm_rn,
#                 qty_vouchered =
#                     SUM(CASE WHEN imhstry_rvrsl = 'Y'
#                              THEN -TRY_CAST(imhstry_qntty_invcd_ap AS decimal(18,6))
#                              ELSE  TRY_CAST(imhstry_qntty_invcd_ap AS decimal(18,6))
#                         END)
#             FROM imhstry
#             WHERE imhstry_ordr_type = 'P'
#               AND RTRIM(imhstry_ordr_id) = RTRIM(@po_id)
#               AND imhstry_srce_jrnl = 'AP Purchase'
#             GROUP BY RTRIM(imhstry_ordr_id), invntryitm_rn
#         )

#         SELECT
#             p.prchseordr_id,
#             p.po_wrkordr_rn,

#             -- Vendor / GL / Job / Work Order context
#             vndr.vndr_id,
#             COALESCE(
#             gj.glentty_rn,         -- job’s GL entity
#              -- branch’s GL entity
#             glc.glentty_rn,        -- location’s GL entity
#             gcmp.glentty_rn        -- company fallback
#             ) AS glentty_rn,

#             COALESCE(
#             gj.glentty_id,
    
#             glc.glentty_id,
#             gcmp.glentty_id
#             ) AS glentty_id,

#             jb.jb_rn,
#             jb.jb_id,
#             wo.wrkordr_rn,
#             wo.wrkordr_id,

#             -- Line details
#             al.line_source,
#             al.line_no,
#             al.vendor_part,
#             al.description,
#             al.uom,
#             al.qty_ordered_line,
#             al.qty_received_line,

#             -- IMHSTRY quantities per line (via item learned from Purchase rows)
#             ISNULL(rbi.qty_received_imhstry, 0.0) AS qty_received_imhstry,
#             ISNULL(vbi.qty_vouchered,        0.0) AS qty_vouchered,

#             al.unit_cost
#         FROM prchseordr AS p
#         LEFT JOIN vndr    AS vndr ON p.vndr_rn = vndr.vndr_rn
        
#         LEFT JOIN wrkordr AS wo   ON p.po_wrkordr_rn = wo.wrkordr_rn
#         LEFT JOIN jbbllngitm      ON jbbllngitm.jbbllngitm_rn = wo.jbbllngitm_rn
#         LEFT JOIN jbcstcde        ON jbcstcde.jbcstcde_rn     = wo.jbcstcde_rn
#         LEFT JOIN jb ON jb.jb_rn = COALESCE(
#             NULLIF(p.jb_rn, 0),
#             NULLIF(jbbllngitm.jb_rn, 0),
#             NULLIF(jbcstcde.jb_rn, 0)
#         )
#         LEFT JOIN lctn   l ON p.lctn_rn  = l.lctn_rn

#         LEFT JOIN glentty AS gj   ON gj.glentty_rn   = jb.jb_glentty_glentty_rn

#         LEFT JOIN glentty AS glc  ON glc.glentty_rn  = l.glentty_rn
#         LEFT JOIN glentty AS gcmp ON gcmp.glentty_rn = p.cmpny_glentty_glentty_rn

#         LEFT JOIN all_lines AS al
#           ON p.prchseordr_rn = al.prchseordr_rn

#         -- line → item mapping (PO + line_no)
#         LEFT JOIN line_to_item AS lti
#           ON RTRIM(p.prchseordr_id) = lti.po_id_trim
#          AND al.line_no              = lti.line_no

#         -- IMHSTRY aggregates by item (PO + invntryitm_rn)
#         LEFT JOIN received_by_item AS rbi
#           ON RTRIM(p.prchseordr_id) = rbi.po_id_trim
#          AND lti.invntryitm_rn       = rbi.invntryitm_rn

#         LEFT JOIN vouchered_by_item AS vbi
#           ON RTRIM(p.prchseordr_id) = vbi.po_id_trim
#          AND lti.invntryitm_rn       = vbi.invntryitm_rn

#         WHERE RTRIM(p.prchseordr_id) = RTRIM(@po_id)
#         ORDER BY al.line_source, al.line_no;
#         """

#         cursor.execute(sql, po_id)  # bind @po_id once

#         cols = [c[0] for c in cursor.description]
#         rows = [dict(zip(cols, r)) for r in cursor.fetchall()]
#         return rows

#     finally:
#         try:
#             cursor.close()
#         finally:
#             conn.close()

    
# def getDBRecordById(invoice_id):

#     conn_mysql = mysql.connector.connect(
#     host='daynite.c4qbs9ngauhk.us-east-1.rds.amazonaws.com',
#     port=3306,  
#     user='dayniteuser',
#     password='asd123ASD!@#',
#     database='marketplace'
# )
#     cursor_mysql = conn_mysql.cursor(dictionary=True)
#     cursor_mysql.execute( """
#     SELECT 
#         PONumber,
#         invoiceID,
#         invoiceDate,
#         `InvoiceDetailSummary:SubtotalAmount`,
#         `InvoiceDetailSummary:NetAmount`,
#         `InvoiceDetailSummary:GrossAmount`,
#         isTaxInLine,
#         `InvoiceDetailItem:Tax`,
#         `InvoiceDetailSummary:ShippingAmount`,
#         `InvoiceDetailSummary:SpecialHandlingAmount`,
#         SellerPartNumber,
#         `InvoiceDetailItem:quantity`,
#         `InvoiceDetailItem:UnitPrice`,
#         `InvoiceDetailItem:UnitOfMeasure`,
#         ItemDescription,
#         createdAt,
#         updatedAt
                 
#     FROM InvoiceItems
#     WHERE invoiceID = %s
    
#     """,(invoice_id,))
#     data=cursor_mysql.fetchall()
#     cursor_mysql.close()
#     conn_mysql.close()
#     return data
# #invoice_mock = []

# #Shared fields
# # netamount=278.04 # total invoice amount including tax? and freight/shipping 
# # shared_invoice_id = '2106432139'
# # shared_po_number = '374618'
# # shared_invoice_date = '07292025'
# # shared_subtotal = 0
# # shared_tax = 27
# # if shared_tax is None:
# #     shared_tax = 0
# # IsInlineTax='Yes'
# # shared_shipping = 0
# # if shared_shipping is None:
# #     shared_shipping = 0
# # shared_special_handling = 11.79
# # if shared_special_handling is None:
# #     shared_special_handling = 0
# #shared_is_tax_in_line = True

# # Line item 1
# # invoice_mock.append({
    
# #     'invoiceID': shared_invoice_id,
# #     'invoiceDate': shared_invoice_date,
# #     'InvoiceDetailSummary:SubtotalAmount': shared_subtotal, # ?total invoice amount EXLUDING tax and freight/shipping 
# #     'InvoiceDetailSummary:NetAmount':netamount, # ?total invoice amount INCLUDING freight/shipping (tax?)   
# #     'isTaxInLine': IsInlineTax,
# #     'InvoiceDetailItem:Tax': shared_tax,
# #     'PONumber': shared_po_number,
# #     'InvoiceDetailSummary:ShippingAmount': shared_shipping,
# #     'InvoiceDetailSummary:SpecialHandlingAmount': shared_special_handling, #special handling is for the total of the invoice
# #     'SellerPartNumber': 'CONC0EA21K38DOT',
# #     'InvoiceDetailItem:quantity': 2,
# #     'InvoiceDetailItem:UnitPrice': 266.25,
# #     'InvoiceDetailItem:UnitOfMeasure': 'EA',
# #     'ItemDescription': 'ELECTRIC TEMP CONTROL, REF,DIG,WHT'
# # })

# # #Line item 2
# # # invoice_mock.append({
# # #     'invoiceID': shared_invoice_id,
# # #     'invoiceDate': shared_invoice_date,
# # #     'InvoiceDetailSummary:SubtotalAmount': shared_subtotal,
# # #     'InvoiceDetailSummary:NetAmount':netamount,
# # #     'isTaxInLine': shared_is_tax_in_line,
# # #     'InvoiceDetailItem:Tax': shared_tax,
# # #     'PONumber': shared_po_number,
# # #     'InvoiceDetailSummary:ShippingAmount': shared_shipping,
# # #     'InvoiceDetailSummary:SpecialHandlingAmount': shared_special_handling,
# # #     'SellerPartNumber': 'SPN-108',
# # #     'InvoiceDetailItem:quantity': 5,
# # #     'InvoiceDetailItem:UnitPrice': 150.00,
# # #     'InvoiceDetailItem:UnitOfMeasure': 'pcs',
# # #     'ItemDescription': 'Aluminum Bracket'
# # # })

# # # Line item 3
# # invoice_mock.append({
# #     'invoiceID': shared_invoice_id,
# #     'invoiceDate': shared_invoice_date,
# #     'InvoiceDetailSummary:SubtotalAmount': shared_subtotal,
# #     'InvoiceDetailSummary:NetAmount':netamount,
# #     'isTaxInLine': IsInlineTax,
# #     'InvoiceDetailItem:Tax': shared_tax,
# #     'PONumber': shared_po_number,
# #     'InvoiceDetailSummary:ShippingAmount': shared_shipping,
# #     'InvoiceDetailSummary:SpecialHandlingAmount': shared_special_handling,
# #     'SellerPartNumber': 'sPn-102',
# #     'InvoiceDetailItem:quantity': 3,
# #     'InvoiceDetailItem:UnitPrice': 85,
# #     'InvoiceDetailItem:UnitOfMeasure': 'pcs',
# #     'ItemDescription': 'Control Module Relay'
# # })
# # convert values from DB that come as Varchar

# #convert varchar values from db

# def clean_po_line_data(rows):
#     """
#     Cleans PO/line rows with fields like:
#     prchseordr_id, po_wrkordr_rn, vndr_id, glentty_rn, glentty_id,
#     jb_rn, jb_id, wrkordr_rn, wrkordr_id, line_source, line_no,
#     vendor_part, description, uom, qty_ordered_line, qty_received_line,
#     qty_received_imhstry, qty_vouchered, unit_cost
#     """
#     cleaned = []

#     for r in rows:
#         try:
#             cleaned_record = {
#             # Header / identifiers
#             'prchseordr_id' : str(r.get('prchseordr_id', '')).strip(),
#             'vndr_id' : str(r.get('vndr_id', '')).strip(),
#             'glentty_rn' : int_or_zero(r.get('glentty_rn')),
#             'glentty_id' : str(r.get('glentty_id', '')).strip().upper(),
#             'jb_rn' : int_or_zero(r.get('jb_rn')),
#             'jb_id' : str(r.get('jb_id', '')).strip(),

            
#             'workorder_rn' : int_or_zero(r.get('wrkordr_rn') if r.get('wrkordr_rn') not in (None, '') else r.get('po_wrkordr_rn')),
#             'workorder_id' : str(r.get('wrkordr_id', '')).strip(),

#             # Line & item
#             'line_source' : str(r.get('line_source', '')).strip().lower(),
#             'line_no' : int_or_zero(r.get('line_no')),
#             'vendor_part' : str(r.get('vendor_part', '')).strip(),
#             'description' : str(r.get('description', '')).strip(),
#             'uom' : str(r.get('uom', '')).strip(),  # keep '' if all spaces

#             # Quantities & price
#             'qty_ordered_line' : to_decimal(r.get('qty_ordered_line')),
#             'qty_received_line' : to_decimal(r.get('qty_received_line')),
#             'qty_received_imhstry' : to_decimal(r.get('qty_received_imhstry')),
#             'qty_vouchered' : to_decimal(r.get('qty_vouchered')),
#             'unit_cost' : to_decimal(r.get('unit_cost'))
#             }
           

           

#             cleaned.append(cleaned_record)

#         except Exception as e:
#             print(f"Error processing record: {e}")

#     return cleaned
# def clean_invoice_data(invoice_data):
#     cleaned = []
 
#     for record in invoice_data:
#         try:
#             cleaned_record = {
#                 'invoiceID': str(record.get('invoiceID', '')).strip(),
#                 'invoiceDate': format_date(record.get('invoiceDate')),
#                 'InvoiceDetailSummary:SubtotalAmount': to_decimal(record.get('InvoiceDetailSummary:SubtotalAmount')),
#                 'InvoiceDetailSummary:NetAmount': to_decimal(record.get('InvoiceDetailSummary:NetAmount')),
#                 'isTaxInLine': str(record.get('isTaxInLine', 'No')).strip().lower(),
#                 'InvoiceDetailItem:Tax': to_decimal(record.get('InvoiceDetailItem:Tax')),
#                 'PONumber': str(record.get('PONumber', '')).strip(),
#                 'InvoiceDetailSummary:ShippingAmount': to_decimal(record.get('InvoiceDetailSummary:ShippingAmount')),
#                 'InvoiceDetailSummary:SpecialHandlingAmount': to_decimal(record.get('InvoiceDetailSummary:SpecialHandlingAmount')),
#                 'SellerPartNumber': str(record.get('SellerPartNumber', '')).strip(),
#                 'InvoiceDetailItem:quantity': int_or_zero(record.get('InvoiceDetailItem:quantity')),
#                 'InvoiceDetailItem:UnitPrice': to_decimal(record.get('InvoiceDetailItem:UnitPrice')),
#                 'InvoiceDetailItem:UnitOfMeasure': str(record.get('InvoiceDetailItem:UnitOfMeasure', '')).strip(),
#                 'ItemDescription': str(record.get('ItemDescription', '')).strip(),
#                 'createdAt': format_date(record.get('createdAt'))
                
#             }

#             cleaned.append(cleaned_record)
#         except Exception as e:
#             print(f"Error processing record: {e}")
    
#     return cleaned

# def to_decimal(val):
#     if val in (None, '', ' '):
#         return Decimal('0.00')
#     try:
#         return Decimal(str(val).strip())
#     except:
#         return Decimal('0.00')

# def int_or_zero(val):
#     try:
#         return int(str(val).strip())
#     except:
#         return 0

# def format_date(val):
#     if isinstance(val, datetime):
#         return val.strftime('%m%d%Y')
#     if isinstance(val, str):
#         try:
#             parsed = datetime.strptime(val.strip(), '%Y-%m-%d')
#             return parsed.strftime('%m%d%Y')
#         except:
#             return val.strip()
#     return ''
# def norm(v):
#         return str(v).strip() if v is not None else None

# def transform_for_ui(response):
#     output = []
#     invoice_total = Decimal(response['invoice_total'])
#     # 1️ Invoice header (first JSON object)
#     header = {
#         "type": "general_info",
#         "po_number": str(response['po_number']),
#         "invoice_number": str(response['invoice_number']),
#         "invoice_date": str(response['invoice_date']),
#         "invoice_total": f"{invoice_total:.2f}",
#         "gl_entity_id": str(response['gl_entity_id']),
#         "line_item_count": str(response['line_item_count']),
#         "has_taxes": str(response['has_taxes']).lower(),
#         "has_extra_charges": str(response['has_extra_charges']).lower(),
#         "extra_charge_count": str(response['extra_charge_count']),
#         "close_po": str(response['close_po']).lower(),
#         "invoice_file_path": str(response['invoice_file_path'])
#     }
#     output.append(header)

#     # 2️ Line items
#     for idx, item in enumerate(response['line_items'], start=1):
#         output.append({
#             "type": "line_item",
#             "line_number": str(idx),
#             "line_item_id": item['item_id'],
#             "quantity": str(item['quantity']),
#             "unit_cost": f"{item['unit_cost']:.3f}",
#             "amount": f"{item['amount']:.2f}"
#         })

#     # 3️ Tax info
#     if response.get('has_taxes') and response.get('tax_info'):
#         tax = response['tax_info']
#         output.append({
#         "type": "tax_info",
#         "authority_id": tax['authority_id'],
#         "gl_account": tax['gl_account'],
#         "tax_base": str(tax['tax_base']),
#         "rate": str(tax['rate']),
#         "tax_amount": str(tax['tax_amount'])
#     })


#     # 4️ Extra charges
#     for idx, charge in enumerate(response['extra_charges'], start=1):
#         output.append({
#             "type": "extra_charges",
#             "charge_number": str(idx),
#             "quantity": str(charge['quantity']),
#             "unit_cost": f"{charge['unit_cost']:.2f}",
#             "cost_category": charge['cost_category'],
#             "description": charge['description']
#         })

#     return output
# def sortlinenumbers(podata,line_items):
#     poview=[]
#     for po  in podata:
#         part_number_po=po['vendor_part']
#         ordered = po['qty_ordered_line']
#         received = po['qty_received_imhstry']
#         vouchered = po['qty_vouchered']
#         unitcost=po['unit_cost']
#         elegibletobevouchered=received - vouchered
#         if(elegibletobevouchered>0):
#              poview.append({
#             'line_number': po.get('line_no'),
#             'item_id': po.get('vendor_part', ''),
#             'quantity': '0',       
#             'unit_cost': '0',    
#             'amount': '0'          
#         })
      

#     items_by_line = {
#         norm(item.get('line_number')): item
#         for item in line_items
#         if item.get('line_number') is not None
#     }

#     for i, row in enumerate(poview):
#         key = norm(row.get('line_number'))
#         if key in items_by_line:
#             # Replace the whole dict with the corresponding line_item
#             poview[i] = items_by_line[key].copy()  # .copy() to avoid aliasing

#       # renumber line_number from 1..N in current order
#     for new_num, item in enumerate(poview, start=1):
#         item['line_number'] = new_num

#     return poview
# #determine authority_id by gl_entty or job id
# def check_taxinfo(PoData,invoice_data): 
    
#     gl_entity = PoData[0]['gl_entity_id'].lower()
    
    
#     job_id = PoData[0]['job_id'].upper()
#     job_id = job_id[:2]
#     glaccountvalue=''
#     print('JOBBBBBBBB ID:' )
    
#     if  gl_entity:
#         gl_entity = gl_entity[:2] + 'a99'
#         authorityid = tax_mock.get(gl_entity) # returns value or None if not found
#         glaccountvalue=glaccount.get(gl_entity)
#         print("TTTAAAXXX-gl:")
#     else:
#         gl_entity=jobidtoglentity.get(job_id)
#         authorityid = tax_mock.get(gl_entity) # returns value or None if not found
#         glaccountvalue=glaccount.get(gl_entity)
#         print("TTTAAAXXX-jobid:")
    
#     taxbase=invoice_data[0]['InvoiceDetailSummary:NetAmount'] - invoice_data[0]['InvoiceDetailItem:Tax'] - invoice_data[0]['InvoiceDetailSummary:SpecialHandlingAmount']
#     taxamount=invoice_data[0]['InvoiceDetailItem:Tax']
#     rate = round(taxamount / taxbase * 100, 4)  if taxbase else 0.0
    
    
#     tax_info = {
#         "authority_id": authorityid,
#         "gl_account": glaccountvalue,
#         "tax_base": f"{taxbase:.3f}",
#         "rate": f"{rate:.4f}",
#         "tax_amount": f"{taxamount:.3f}"
#     }
#     print(tax_info)
    
#     return tax_info
# def send_email(emailcontent):
 

#     # === STEP 1: CONFIGURATION ===
  

#     # === STEP 2: AUTHENTICATE AND GET TOKEN ===
#     token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
#     token_data = {
#         'grant_type': 'client_credentials',
#         'client_id': client_id,
#         'client_secret': client_secret,
#         'scope': 'https://graph.microsoft.com/.default'
#     }

#     try:
#         token_response = requests.post(token_url, data=token_data)
#         token_response.raise_for_status()
#         access_token = token_response.json()['access_token']
#         print(" Authenticated successfully.")
#     except Exception as e:
#         print(f" Failed to authenticate: {e}")
#         exit(1)

#     # === STEP 3: SET AUTH HEADER ===
#     headers = {
#         'Authorization': f'Bearer {access_token}',
#         'Content-Type': 'application/json'
#     }

#     # === STEP 4: BUILD EMAIL PAYLOAD ===
#     email_payload = {
#         "message": {
#             "subject": "INV05",
#             "body": {
#                 "contentType": "Text",
#                 "content": emailcontent
#             },
#             "toRecipients": [
#                 {
#                     "emailAddress": {
#                         "address": "AutomationTool@wearetheone.com"  # Replace with recipient email
#                         #"address": "henri.sula@gmail.com" 
#                     }
#                 }
#             ]
#         },
#         "saveToSentItems": "true"
#     }

#     # === STEP 5: SEND THE EMAIL ===
#     send_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/sendMail"

#     try:
#         send_response = requests.post(send_url, headers=headers, json=email_payload)
#         if send_response.status_code == 202:
#             print("Email sent successfully.")
#         else:
#             print(f"Failed to send email: {send_response.status_code} - {send_response.text}")
#     except Exception as e:
#         print(f" Error sending email: {e}")

        
# def can_close_po(invoice_items, po_items):
#     #how many units are invoiced per item
#     invoice_qty_by_item = {}
#     for item in invoice_items:
#         part_number = item['SellerPartNumber'].lower()
#         invoice_qty_by_item[part_number] = invoice_qty_by_item.get(part_number, 0) + int(item['InvoiceDetailItem:quantity'])

#     close_po = True  

#     for po in po_items:
#         item_id = po['vendor_part'].lower()
#         ordered = po['qty_ordered_line']
#         received = po['qty_received_imhstry']
#         vouchered = po['qty_vouchered']

#         eligible_to_voucher = received - vouchered
#         invoice_qty = invoice_qty_by_item.get(item_id, 0)

#         #  If item not fully received, PO cannot be closed
#         if received < ordered:
#             close_po = False
#             print(f" Cannot close PO: item '{item_id}' not fully received.")
#             continue

#         # If invoice does not voucher all received-but-unvouchered units
#         if invoice_qty < eligible_to_voucher:
#             close_po = False
#             print(f" Cannot close PO: item '{item_id}' still has {eligible_to_voucher - invoice_qty} unvouchered units.")

#     return close_po


# # keep in mind check here if invoice has multiple same SellerPartNumber id-s , if it has add the quantities of those  items together.
# #validate if invoice is trying to overvouch
# def validatevouch(invoice_items, po_items):
#     matching_pos = []
#     for item in invoice_items:
#         part_number = item['SellerPartNumber'].lower()
#         matching_pos += [po for po in po_items if po['vendor_part'].lower() == part_number]
        
#     isVoucherEligible = True;     
        
#     for match in matching_pos:
#         part_number_po=match['vendor_part']
#         ordered = match['qty_ordered_line']
#         received = match['qty_received_imhstry']
#         vouchered = match['qty_vouchered']
#         unitcost=match['unit_cost']
#         elegibletobevouchered=received - vouchered

#         totalpo_line_item=ordered*unitcost
#         allowed_price_peritem=(totalpo_line_item +100) /ordered

       
#         invoice_item = next((item for item in invoice_items if item['SellerPartNumber'].lower() == part_number_po.lower()),None)# there will always be one
#         if (elegibletobevouchered < int(invoice_item['InvoiceDetailItem:quantity']) or ordered < received or  allowed_price_peritem < int(invoice_item['InvoiceDetailItem:UnitPrice'])):
#             isVoucherEligible = False
#         print("Part Number:")    
#         print(f"{part_number_po}:Quantity Ordered={ordered},Quantity Received={received},Quantity Vouchered={vouchered},elegibletobevouchered={elegibletobevouchered}, Quantity(invoiced)={invoice_item['InvoiceDetailItem:quantity']}, po_price={match['unit_cost']}, invoice_price={invoice_item['InvoiceDetailItem:UnitPrice']}")
#      # Find matching PO line item
        
#         print("ALLOWED PRICE PER ITEM:")
        
#         print(allowed_price_peritem)
#         print("Total item PO_line:")
#         print(totalpo_line_item)
    
#     print(isVoucherEligible)
#     return isVoucherEligible;    

# def check_for_duplicate_items(invoice):
#     seen = set()
#     duplicates = set()

#     for item in invoice:
#         part_number = item['SellerPartNumber'].lower().strip()
#         if part_number in seen:
#             duplicates.add(part_number)
#         else:
#             seen.add(part_number)

#     if duplicates:
#         print("Duplicate item IDs found:", list(duplicates))
#         return False

#     return True
    
     
    
#     # validate if each item in the po exists in the invoice.
# def validate_invoice_items_against_po(invoice_items, po_items):
    
#     invoice_item_ids = {item['SellerPartNumber'].lower() for item in invoice_items}
#     po_item_ids = {item['vendor_part'].lower() for item in po_items}

    
#     unmatched_items = invoice_item_ids - po_item_ids

#     if unmatched_items:
#         print("These item_ids are not in the PO:", unmatched_items)
#         return False
#     else:
#         print("All item_ids in the invoice are present in the PO.")
#         return True
    
# #check if invoice exist and then if po exists
# def validate_single_po(invoiceID,invoice_data,PoData):
#     # Find invoice by ID
    
#     invoice = next((inv for inv in invoice_data if inv['invoiceID'].lower() == invoiceID.lower()), None)
    
    
#     if not invoice:
#         return {'status': 'error', 'message': f'Invoice ID {invoiceID} not found.'}, 404

#     invoice_po_number = invoice['PONumber'].lower()
#     invoice_no = invoice['invoiceID'].lower()
#     print('InvoiceNo:')
#     print(invoice_no)
#     print('PONumber:')
#     print(invoice_po_number)
   
#     #invoice_po_number='368526'  #Delete later 
#     purchase_order = next((po for po in PoData if po['prchseordr_id'].lower() == invoice_po_number), None)
    
#     if not purchase_order:
#         return {'status': 'error', 'message': f'purchase order id  {invoice_po_number} not found.'}, 404
#     print("FOUND PO FOR THIS INVOICE")
   
#     return True   

    
    
# # API Endpoint
# @app.route('/invoice/<string:invoiceID>', methods=['GET'])
# def get_po_data(invoiceID):
#     # result=invoice_data
#     line_items=[]
#     charges=[]
#     tax_info = []
#     extra_charge_count=0
#     line_item_count=0

#     dbinvoicedata = getDBRecordById(invoiceID)
#     invoice_data=clean_invoice_data(dbinvoicedata)

#     invoice_datapo=invoice_datapo = next(
#     (rec.get('PONumber') for rec in (invoice_data or []) if isinstance(rec, dict) and 'PONumber' in rec),
#     None
# )

#     testinvoice_datapo='368526'

#     PoDbData=getDBPORecordById(invoice_datapo)
#     PoData= clean_po_line_data(PoDbData)

#     #print(PoData)
    
#     #print(invoice_data)
#     #Validate Invoice against PO if it passes calculate tax etc.
#     result = validate_single_po(invoiceID,invoice_data,PoData)
    
    
#     if result is not True:
#         return jsonify(result[0]), result[1]

#     if not validate_invoice_items_against_po(invoice_data, PoData):
#         return jsonify({'status': 'error', 'message': 'Invoice item mismatch'}), 400
#     if not check_for_duplicate_items(invoice_data):
#         return jsonify({'status': 'error', 'message': 'Duplicate item IDs found'}), 400
#     if not validatevouch(invoice_data, PoData):
#         return jsonify({'status': 'error', 'message': 'Vouchering failed'}), 400
    
    
#     close_po=can_close_po(invoice_data, PoData)
#     print("Can close po:")
#     print(close_po)
#     #check Db if it has taxes
#     IsInlineTax=invoice_data[0]['isTaxInLine']
#     shared_special_handling=invoice_data[0]['InvoiceDetailSummary:SpecialHandlingAmount']

#     if IsInlineTax=='yes':
#         hastax=True
#         tax_info=check_taxinfo(PoData,invoice_data)
        
#     else:
#         hastax=False
        
    
#         #check if freight is there 
#     if shared_special_handling is not None and shared_special_handling > 0 and shared_special_handling<=500:
#         hasextracharges=True
#         extra_charge_count=extra_charge_count+1
        
#         charges.append({
#             'charge_number':extra_charge_count,
#             'quantity': ('1'),
#             'unit_cost': shared_special_handling,
#             'cost_category': ('FREIGHT'),
#             'description': ('Freight Charge'),
#         })
#         print("Extra Charges:")
#         print(charges)
#     elif shared_special_handling>500:
#          return jsonify({'status': 'error', 'message': 'Freight needs manual review, Freight exceeds 500 Dollars!'}), 400
#     else:
#         hasextracharges=False
        
    
        

#     # if shared_shipping is not None and shared_shipping >0 and shared_shipping<=200:
#     #       hasextracharges=True
#     #       extra_charge_count=extra_charge_count+1
#     #       charges.append({
#     #         'charge_number':extra_charge_count,
#     #         'quantity': ('1'),
#     #         'unit_cost': shared_shipping,
#     #         'cost_category': ('202'),
#     #         'description': ('Handling fee'),
#     #     })
          

#     for item in invoice_data:
#         item_id = item['SellerPartNumber'].lower()
#         unit_price = item['InvoiceDetailItem:UnitPrice'] 
#         quantity = item['InvoiceDetailItem:quantity']
#         line_item_count=line_item_count+1
#         poitem= next((po for po in PoData if po['vendor_part'].lower() == item_id), None)
#         line_number=poitem['line_no']
#         line_items.append({
#         'line_number':line_number,#this value has to come from sampro db
#         'item_id': item_id,
#         'quantity': quantity,
#         'unit_cost': unit_price,
#         'amount': int(quantity)*unit_price
        
            
        
#     })
        
#     poview=sortlinenumbers(PoData,line_items)
#     print(poview)

#    #get gl_entity by glentty or by job_id
#     short_gl=''
#     gl_entity = PoData[0]['glentty_id'].lower()
#     job_id = PoData[0]['jb_id'].upper()
    
#     if  gl_entity:
#         short_gl = PoData[0]['glentty_id'].lower()
#         gl_entty = short_gl[:2] + 'a99'
#     else:
#         job_id = job_id[:2]
#         gl_entty=jobidtoglentity.get(job_id)
#         gl_entty = gl_entty[:2] + 'a99'
        
#         print("glentity-jobid:")
#     response = {
#         'type': 'general_info',
#         'po_number': invoice_data[0]['PONumber'],    
#         'invoice_number': invoice_data[0]['invoiceID'],
#         #'invoice_date': invoice_data[0]['createdAt'],
#         'invoice_date': "08132025",
#         'invoice_total': invoice_data[0]['InvoiceDetailSummary:NetAmount'],
#         'gl_entity_id':gl_entty,
#         'has_taxes': hastax,
#         'tax_info': tax_info,
#         'has_extra_charges': hasextracharges,
#         'extra_charge_count':extra_charge_count,
#         'extra_charges': charges,
#         'line_items':line_items,
        
#         'line_item_count':line_item_count,
        
#         'close_po': close_po, 
#         'invoice_file_path': ""
#     }

#     uiresponse=transform_for_ui(response)
#     #emailcontent = "\n".join(json.dumps(obj) for obj in uiresponse)
#     emailcontent = ""

#     chunks = [json.dumps(obj) for obj in uiresponse]
#     emailcontent = chunks[0]  # first object with no delimiter

#     for chunk in chunks[1:]:
#         emailcontent += "\n?()?\n" + chunk

#     #emailcontent += "\n?()?\n"
#     send_email(emailcontent)
#     print("Invoice Processed Successfully.")
#     print("TOTAL:",invoice_data[0]['InvoiceDetailSummary:NetAmount'])



#     print(charges)

#     return jsonify(uiresponse)

# if __name__ == '__main__':
#     app.run(debug=True)
