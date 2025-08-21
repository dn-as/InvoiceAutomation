from flask import Flask, jsonify
import requests
import json
import pyodbc
import mysql.connector
from decimal import Decimal
from datetime import datetime
import copy, hashlib, re
from openai import OpenAI
import os
from typing import Optional
# print(pyodbc.version)



app = Flask(__name__)
#DETERMINE TAX AUTHORITY ID BY GL_ENTITY OR JOB IDD 
tax_mock=[]
tax_mock = {
    '01a99': 'nassau',
    '02a99': 'nassau',
    '03a99': 'nassau',
    '06a99': 'florida',
    '07a99': 'nassau',
    '11a99':'maryland',
    '12a99':'philadelphia',
    '14a99':'florida',
    '15a99':'massachusetts'
}

jobidtoglentity=[]
#DETERMINE GL ENTITY BY JOB ID 
#GET THE FIRST TWO LETTERS NOT THREE
jobidtoglentity = {
    'RE': '01a99',
    'AL':'02a99',
    'DA': '03a99',
    'SC': '04a99',
    'FL':'06a99',
    'SF':'14a99',
    'DC': '11a99',
    'PE': '12a99',
    'PL': '07a99',
    'BO':'15a99',
    'NC': '13a99',
}

glaccount=[]
#DETERMINE GL account BY glentity #all lowercase
glaccount = {
    '01a99': '2401',
    '02a99': '2401',
    '03a99': '2401',
    '06a99': '2411',
    '07a99': '2401',
    '11a99':'2407',
    '12a99':'2404',
    '14a99':'2411',
    '15a99':'2409'
}

import pyodbc

def getDBPORecordById(po_id: str):
    """
    Fetch PO lines with IMHSTRY quantities per line:
      - qty_received_imhstry: sum of imhstry_qntty_rcvd on 'Receipt' rows (by item)
      - qty_vouchered:        sum of imhstry_qntty_invcd_ap on 'AP Purchase' rows (by item)
    Line -> item mapping is learned from 'Purchase' rows (their journal line numbers match PO lines).
    Returns: List[dict]
    """
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=SAMPRODBSERVER;"
        "DATABASE=DayNite_test;"
        "Trusted_Connection=yes;"
    )
    cursor = conn.cursor()
    try:
        sql = """
        DECLARE @po_id VARCHAR(50) = ?;

-- 1) PO lines (LIST + LISTGN)
WITH all_lines AS (
    SELECT
        'LIST'  AS line_source,
        prchseordr_rn,
        prchseordrlst_rn      AS ordrlst_rn,
        prchseordrlst_ln      AS line_no,
        prchseordrlst_vndr_prt_nmbr AS vendor_part,
        prchseordrlst_dscrptn       AS description,
        prchseordrlst_unt_msre      AS uom,
        prchseordrlst_qntty_ordrd   AS qty_ordered_line,
        prchseordrlst_qntty_rcvd    AS qty_received_line,
        prchseordrlst_unt_cst       AS unit_cost
    FROM prchseordrlst
    UNION ALL
    SELECT
        'LISTGN',
        prchseordr_rn,
        prchseordrlstgn_rn,
        prchseordrlstgn_ln,
        prchseordrlstgn_vndr_prt_nmbr,
        prchseordrlstgn_dscrptn,
        prchseordrlstgn_unt_msre,
        prchseordrlstgn_qntty_ordrd,
        prchseordrlstgn_qntty_rcvd,
        prchseordrlstgn_unt_cst
    FROM prchseordrlstgn
),

-- 2) Map PO line_no → item using PURCHASE rows
line_to_item AS (
    SELECT
        po_id_trim     = RTRIM(imhstry_ordr_id),
        line_no        = NULLIF(imhstry_srce_jrnl_ln, 0),
        invntryitm_rn  = MAX(NULLIF(invntryitm_rn, 0))
    FROM imhstry
    WHERE imhstry_ordr_type = 'P'
      AND RTRIM(imhstry_ordr_id) = RTRIM(@po_id)
      AND imhstry_srce_jrnl = 'Purchase'
      AND ISNULL(imhstry_srce_jrnl_ln, 0) <> 0
    GROUP BY RTRIM(imhstry_ordr_id), imhstry_srce_jrnl_ln
),

-- 3a) RECEIVED by PO + item (inventory lines)
received_by_item AS (
    SELECT
        po_id_trim = RTRIM(imhstry_ordr_id),
        invntryitm_rn,
        qty_received_imhstry =
            SUM(CASE WHEN imhstry_rvrsl = 'Y'
                     THEN -TRY_CAST(imhstry_qntty_rcvd AS decimal(18,6))
                     ELSE  TRY_CAST(imhstry_qntty_rcvd AS decimal(18,6))
                END)
    FROM imhstry
    WHERE imhstry_ordr_type = 'P'
      AND RTRIM(imhstry_ordr_id) = RTRIM(@po_id)
      AND imhstry_srce_jrnl = 'Receipt'      -- receipts only
    GROUP BY RTRIM(imhstry_ordr_id), invntryitm_rn
),

-- 3b) RECEIVED by PO + line_no (general lines or fallback)
received_by_line AS (
    SELECT
        po_id_trim = RTRIM(imhstry_ordr_id),
        line_no    = NULLIF(imhstry_srce_jrnl_ln, 0),
        qty_received_imhstry =
            SUM(CASE WHEN imhstry_rvrsl = 'Y'
                     THEN -TRY_CAST(imhstry_qntty_rcvd AS decimal(18,6))
                     ELSE  TRY_CAST(imhstry_qntty_rcvd AS decimal(18,6))
                END)
    FROM imhstry
    WHERE imhstry_ordr_type = 'P'
      AND RTRIM(imhstry_ordr_id) = RTRIM(@po_id)
      AND imhstry_srce_jrnl = 'Receipt'      -- receipts only
      AND ISNULL(imhstry_srce_jrnl_ln, 0) <> 0
    GROUP BY RTRIM(imhstry_ordr_id), imhstry_srce_jrnl_ln
),

-- 4a) VOUCHERED by PO + item (inventory lines)
vouchered_by_item AS (
    SELECT
        po_id_trim = RTRIM(imhstry_ordr_id),
        invntryitm_rn,
        qty_vouchered =
            SUM(CASE WHEN imhstry_rvrsl = 'Y'
                     THEN -TRY_CAST(imhstry_qntty_invcd_ap AS decimal(18,6))
                     ELSE  TRY_CAST(imhstry_qntty_invcd_ap AS decimal(18,6))
                END)
    FROM imhstry
    WHERE imhstry_ordr_type = 'P'
      AND RTRIM(imhstry_ordr_id) = RTRIM(@po_id)
      AND imhstry_srce_jrnl = 'AP Purchase'  -- AP/voucher postings
    GROUP BY RTRIM(imhstry_ordr_id), invntryitm_rn
),

-- 4b) VOUCHERED by PO + line_no (general lines or fallback)
vouchered_by_line AS (
    SELECT
        po_id_trim = RTRIM(imhstry_ordr_id),
        line_no    = NULLIF(imhstry_srce_jrnl_ln, 0),
        qty_vouchered =
            SUM(CASE WHEN imhstry_rvrsl = 'Y'
                     THEN -TRY_CAST(imhstry_qntty_invcd_ap AS decimal(18,6))
                     ELSE  TRY_CAST(imhstry_qntty_invcd_ap AS decimal(18,6))
                END)
    FROM imhstry
    WHERE imhstry_ordr_type = 'P'
      AND RTRIM(imhstry_ordr_id) = RTRIM(@po_id)
      AND imhstry_srce_jrnl = 'AP Purchase'  -- AP/voucher postings
      AND ISNULL(imhstry_srce_jrnl_ln, 0) <> 0
    GROUP BY RTRIM(imhstry_ordr_id), imhstry_srce_jrnl_ln
)

SELECT
    p.prchseordr_id,
    p.po_wrkordr_rn,

    vndr.vndr_id,

    COALESCE(gj.glentty_rn, glc.glentty_rn, gcmp.glentty_rn) AS glentty_rn,
    COALESCE(gj.glentty_id, glc.glentty_id, gcmp.glentty_id) AS glentty_id,

    jb.jb_rn,
    jb.jb_id,
    wo.wrkordr_rn,
    wo.wrkordr_id,

    al.line_source,
    al.line_no,
    al.vendor_part,
    al.description,
    al.uom,
    al.qty_ordered_line,
    al.qty_received_line,

    -- Received: prefer item mapping; fallback to line_no (always use line_no for LISTGN)
    ISNULL(
        CASE WHEN al.line_source = 'LISTGN' OR lti.invntryitm_rn IS NULL
             THEN rbl.qty_received_imhstry
             ELSE rbi.qty_received_imhstry
        END, 0.0
    ) AS qty_received_imhstry,

    -- Vouchered: same selection logic
    ISNULL(
        CASE WHEN al.line_source = 'LISTGN' OR lti.invntryitm_rn IS NULL
             THEN vbl.qty_vouchered
             ELSE vbi.qty_vouchered
        END, 0.0
    ) AS qty_vouchered,

    al.unit_cost

FROM prchseordr           AS p
LEFT JOIN vndr            AS vndr ON p.vndr_rn = vndr.vndr_rn
LEFT JOIN wrkordr         AS wo   ON p.po_wrkordr_rn = wo.wrkordr_rn
LEFT JOIN jbbllngitm             ON jbbllngitm.jbbllngitm_rn = wo.jbbllngitm_rn
LEFT JOIN jbcstcde               ON jbcstcde.jbcstcde_rn     = wo.jbcstcde_rn
LEFT JOIN jb                     ON jb.jb_rn = COALESCE(NULLIF(p.jb_rn, 0), NULLIF(jbbllngitm.jb_rn, 0), NULLIF(jbcstcde.jb_rn, 0))
LEFT JOIN lctn             AS l   ON p.lctn_rn  = l.lctn_rn
LEFT JOIN glentty          AS gj  ON gj.glentty_rn   = jb.jb_glentty_glentty_rn
LEFT JOIN glentty          AS glc ON glc.glentty_rn  = l.glentty_rn
LEFT JOIN glentty          AS gcmp ON gcmp.glentty_rn = p.cmpny_glentty_glentty_rn

LEFT JOIN all_lines        AS al  ON p.prchseordr_rn = al.prchseordr_rn

LEFT JOIN line_to_item     AS lti ON RTRIM(p.prchseordr_id) = lti.po_id_trim
                                 AND al.line_no              = lti.line_no

LEFT JOIN received_by_item AS rbi ON RTRIM(p.prchseordr_id) = rbi.po_id_trim
                                 AND lti.invntryitm_rn       = rbi.invntryitm_rn
LEFT JOIN vouchered_by_item AS vbi ON RTRIM(p.prchseordr_id) = vbi.po_id_trim
                                  AND lti.invntryitm_rn       = vbi.invntryitm_rn

LEFT JOIN received_by_line AS rbl ON RTRIM(p.prchseordr_id) = rbl.po_id_trim
                                 AND al.line_no              = rbl.line_no
LEFT JOIN vouchered_by_line AS vbl ON RTRIM(p.prchseordr_id) = vbl.po_id_trim
                                  AND al.line_no              = vbl.line_no

WHERE RTRIM(p.prchseordr_id) = RTRIM(@po_id)
ORDER BY al.line_source, al.line_no;

        """

        cursor.execute(sql, po_id)  

        cols = [c[0] for c in cursor.description]
        rows = [dict(zip(cols, r)) for r in cursor.fetchall()]
        return rows

    finally:
        try:
            cursor.close()
        finally:
            conn.close()

    
def getDBRecordById(invoice_id):

    conn_mysql = mysql.connector.connect(
    host='daynite.c4qbs9ngauhk.us-east-1.rds.amazonaws.com',
    port=3306,  
    user='dayniteuser',
    password='asd123ASD!@#',
    database='marketplace'
)
    cursor_mysql = conn_mysql.cursor(dictionary=True)
    cursor_mysql.execute( """
    SELECT 
        PONumber,
        invoiceID,
        invoiceDate,
        `InvoiceDetailSummary:SubtotalAmount`,
        `InvoiceDetailSummary:NetAmount`,
        `InvoiceDetailSummary:GrossAmount`,
        isTaxInLine,
        `InvoiceDetailItem:Tax`,
        `InvoiceDetailSummary:ShippingAmount`,
        `InvoiceDetailSummary:SpecialHandlingAmount`,
        SellerPartNumber,
        `InvoiceDetailItem:quantity`,
        `InvoiceDetailItem:UnitPrice`,
        `InvoiceDetailItem:UnitOfMeasure`,
        ItemDescription,
        createdAt,
        updatedAt
                 
    FROM InvoiceItems
    WHERE invoiceID = %s
    
    """,(invoice_id,))
    data=cursor_mysql.fetchall()
    cursor_mysql.close()
    conn_mysql.close()
    return data


def clean_po_line_data(rows):
    """
    Cleans PO/line rows with fields like:
    prchseordr_id, po_wrkordr_rn, vndr_id, glentty_rn, glentty_id,
    jb_rn, jb_id, wrkordr_rn, wrkordr_id, line_source, line_no,
    vendor_part, description, uom, qty_ordered_line, qty_received_line,
    qty_received_imhstry, qty_vouchered, unit_cost
    """
    cleaned = []

    for r in rows:
        try:
            cleaned_record = {
            # Header / identifiers
            'prchseordr_id' : str(r.get('prchseordr_id', '')).strip(),
            'vndr_id' : str(r.get('vndr_id', '')).strip(),
            'glentty_rn' : int_or_zero(r.get('glentty_rn')),
            'glentty_id' : str(r.get('glentty_id', '')).strip().upper(),
            'jb_rn' : int_or_zero(r.get('jb_rn')),
            'jb_id' : str(r.get('jb_id', '')).strip(),

            
            'workorder_rn' : int_or_zero(r.get('wrkordr_rn') if r.get('wrkordr_rn') not in (None, '') else r.get('po_wrkordr_rn')),
            'workorder_id' : str(r.get('wrkordr_id', '')).strip(),

            # Line & item
            'line_source' : str(r.get('line_source', '')).strip().lower(),
            'line_no' : int_or_zero(r.get('line_no')),
            'vendor_part' : str(r.get('vendor_part', '')).strip(),
            'description' : str(r.get('description', '')).strip(),
            'uom' : str(r.get('uom', '')).strip(),  # keep '' if all spaces

            # Quantities & price
            'qty_ordered_line' : to_decimal(r.get('qty_ordered_line')),
            'qty_received_line' : to_decimal(r.get('qty_received_line')),
            'qty_received_imhstry' : to_decimal(r.get('qty_received_imhstry')),
            'qty_vouchered' : to_decimal(r.get('qty_vouchered')),
            'unit_cost' : to_decimal(r.get('unit_cost'))
            }
           

           

            cleaned.append(cleaned_record)

        except Exception as e:
            print(f"Error processing record: {e}")

    return cleaned
def clean_invoice_data(invoice_data):
    cleaned = []
 
    for record in invoice_data:
        try:
            cleaned_record = {
                'invoiceID': str(record.get('invoiceID', '')).strip(),
                'invoiceDate': format_date(record.get('invoiceDate')),
                'InvoiceDetailSummary:SubtotalAmount': to_decimal(record.get('InvoiceDetailSummary:SubtotalAmount')),
                'InvoiceDetailSummary:NetAmount': to_decimal(record.get('InvoiceDetailSummary:NetAmount')),
                'isTaxInLine': str(record.get('isTaxInLine', 'No')).strip().lower(),
                'InvoiceDetailItem:Tax': to_decimal(record.get('InvoiceDetailItem:Tax')),
                'PONumber': str(record.get('PONumber', '')).strip(),
                'InvoiceDetailSummary:ShippingAmount': to_decimal(record.get('InvoiceDetailSummary:ShippingAmount')),
                'InvoiceDetailSummary:SpecialHandlingAmount': to_decimal(record.get('InvoiceDetailSummary:SpecialHandlingAmount')),
                'SellerPartNumber': str(record.get('SellerPartNumber', '')).strip(),
                'InvoiceDetailItem:quantity': int_or_zero(record.get('InvoiceDetailItem:quantity')),
                'InvoiceDetailItem:UnitPrice': to_decimal(record.get('InvoiceDetailItem:UnitPrice')),
                'InvoiceDetailItem:UnitOfMeasure': str(record.get('InvoiceDetailItem:UnitOfMeasure', '')).strip(),
                'ItemDescription': str(record.get('ItemDescription', '')).strip(),
                'createdAt': format_date(record.get('createdAt'))
                
            }

            cleaned.append(cleaned_record)
        except Exception as e:
            print(f"Error processing record: {e}")
    
    return cleaned
def _normalize_for_id(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"[\W_]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s
def to_decimal(val):
    if val in (None, '', ' '):
        return Decimal('0.00')
    try:
        return Decimal(str(val).strip())
    except:
        return Decimal('0.00')

def int_or_zero(val):
    try:
        return int(str(val).strip())
    except:
        return 0

def format_date(val):
    if isinstance(val, datetime):
        return val.strftime('%m%d%Y')
    if isinstance(val, str):
        try:
            parsed = datetime.strptime(val.strip(), '%Y-%m-%d')
            return parsed.strftime('%m%d%Y')
        except:
            return val.strip()
    return ''
def norm(v):
        return str(v).strip() if v is not None else None
def _norm(s): 
    return (s or "").strip().lower()
def _get_env(name: str, required: bool = True, default: Optional[str] = None) -> str:
    val = os.getenv(name, default)
    if required and not val:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val
#transform response as UI expects it 
def transform_for_ui(response):
    output = []
    invoice_total = Decimal(response['invoice_total'])
    # 1️ Invoice header (first JSON object)
    header = {
        "type": "general_info",
        "po_number": str(response['po_number']),
        "invoice_number": str(response['invoice_number']),
        "invoice_date": str(response['invoice_date']),
        "invoice_total": f"{invoice_total:.2f}",
        "gl_entity_id": str(response['gl_entity_id']),
        "line_item_count": str(response['line_item_count']),
        "has_taxes": str(response['has_taxes']).lower(),
        "has_extra_charges": str(response['has_extra_charges']).lower(),
        "extra_charge_count": str(response['extra_charge_count']),
        "close_po": str(response['close_po']).lower(),
        "invoice_file_path": str(response['invoice_file_path'])
    }
    output.append(header)

    # 2️ Line items
    for idx, item in enumerate(response['line_items'], start=1):
        output.append({
            "type": item['line_source'],
            "line_number": str(idx),
            "line_item_id": item['item_id'],
            "quantity": str(item['quantity']),
            "unit_cost": f"{item['unit_cost']:.3f}",
            "amount": f"{item['amount']:.3f}"
        })

    # 3️ Tax info
    if response.get('has_taxes') and response.get('tax_info'):
        tax = response['tax_info']
        output.append({
        "type": "tax_info",
        "authority_id": tax['authority_id'],
        "gl_account": tax['gl_account'],
        "tax_base": str(tax['tax_base']),
        "rate": str(tax['rate']),
        "tax_amount": str(tax['tax_amount'])
    })


    # 4️ Extra charges
    for idx, charge in enumerate(response['extra_charges'], start=1):
        output.append({
            "type": "extra_charges",
            "charge_number": str(idx),
            "quantity": str(charge['quantity']),
            "unit_cost": f"{charge['unit_cost']:.2f}",
            "cost_category": charge['cost_category'],
            "description": charge['description']
        })

    return output
#determine authority_id by gl_entty or job id





client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def chatgpt_match_by_description(invoice_items_wo_ids: list[dict],
                                 po_items_wo_ids: list[dict]) -> dict:
    system_msg = {
        "role": "system",
        "content": (
            "You are an expert at matching invoice items to purchase order items "
            "based solely on textual description. "
            "Only output valid JSON in the requested schema. "
            "For each invoice line, decide if it matches one PO line. "
            "Be strict: if no good match, mark decision='no_match' and matched_po_line_no=null. "
            "Return all attempted matches, even failures."
        )
    }

    user_payload = {
        "invoice_items": invoice_items_wo_ids,
        "po_items": po_items_wo_ids
    }

    user_msg = {
        "role": "user",
        "content": (
            "Match the following invoice items to purchase order items by description only.\n\n"
            f"{json.dumps(user_payload, indent=2)}\n\n"
            "Return JSON with keys: matches, unmatched_po_lines."
        )
    }

    resp = client.chat.completions.create(   # <-- NEW CALL STYLE
        model="gpt-4o-mini",
        messages=[system_msg, user_msg],
        temperature=0,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "InvoicePOMatches",
                "schema": {
                    "type": "object",
                    "properties": {
                        "matches": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "invoice_line_no": {"type": "integer"},
                                    "invoice_description": {"type": "string"},
                                    "decision": {"enum": ["match", "no_match"]},
                                    "matched_po_line_no": {"type": ["integer", "null"]},
                                    "confidence": {"type": "number"},
                                    "evidence_tokens": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    }
                                },
                                "required": [
                                    "invoice_line_no",
                                    "invoice_description",
                                    "decision",
                                    "matched_po_line_no",
                                    "confidence",
                                    "evidence_tokens"
                                ]
                            }
                        },
                        "unmatched_po_lines": {
                            "type": "array",
                            "items": {"type": "integer"}
                        }
                    },
                    "required": ["matches", "unmatched_po_lines"]
                }
            }
        }
    )
    
    content = resp.choices[0].message.content
    print(json.loads(content))
    return json.loads(content)



def _assign_invoice_line_numbers(invoice_id: str, items: list[dict]) -> list[dict]:
    out = []
    for idx, it in enumerate(items, start=1):  # 1-based index
        key_src = f"{invoice_id}|{idx}|{it.get('SellerPartNumber','')}|{it.get('ItemDescription','')}"
        uid = hashlib.sha1(key_src.encode()).hexdigest()[:12]
        it = {**it} #make a copy of dict
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

    # 1)Assign line_number to invoice 
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
                po_ref = po_list[i]  
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

    # Add invoice lines with missing/bad IDs to DESCRIPTION pool
    for inv in invoice_items:
        if inv["invoice_line_uid"] in matched_invoice_uids:
            continue
        sid = _norm(inv.get("SellerPartNumber"))
        if not sid or sid not in po_by_id:
            inv_unmatched_for_desc.append(inv)

    # 4) DESC fallback only against UNUSED PO lines (strict one-to-one across ID + DESC)
    desc_matches = []
    ai_resp=''
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

    invoice_items_resolved = [dict(x) for x in invoice_items]
    po_items_resolved      = [dict(x) for x in po_items]
    patch_log = []
    #ASSIGN ID-S TO THE MATCHED DESCRIPTION MATCHES
    if all_matched:
        # Fast index by line numbers
        inv_idx_by_line = {int(i.get("invoice_line_no", idx+1)): idx for idx, i in enumerate(invoice_items_resolved)}
        po_idx_by_line  = {int(p.get("line_no")): idx for idx, p in enumerate(po_items_resolved) if p.get("line_no") is not None}

        # Helper: stable synthetic ID if PO vendor_part missing
        def make_assigned_id(inv_desc: str, po_desc: str) -> str:
            key = _normalize_for_id(f"{inv_desc}|{po_desc}")
            return "ai_" + hashlib.sha1(key.encode()).hexdigest()[:12]

        # Only desc matches need enrichment (ID matches already agree by definition)
        for m in desc_matches:
            iln = int(m["invoice_line_no"])
            pln = int(m["po_line_no"])
            inv_i = inv_idx_by_line[iln]
            po_i  = po_idx_by_line[pln]

            inv_line = invoice_items_resolved[inv_i]
            po_line  = po_items_resolved[po_i]

            po_vendor = (po_line.get("vendor_part") or "").strip()
            if po_vendor:
                old = (inv_line.get("SellerPartNumber") or "").strip()
                if old.lower() != po_vendor.lower():
                    inv_line["SellerPartNumber"] = po_vendor
                    inv_line["ai_resolution"] = "desc_match"
                    patch_log.append({
                        "invoice_line_no": iln,
                        "po_line_no": pln,
                        "action": "set_seller_part_from_po_vendor_part",
                        "value": po_vendor
                    })
            else:
                # generate deterministic ID and set on both sides
                assigned = make_assigned_id(inv_line.get("ItemDescription",""), po_line.get("description",""))
                inv_line["SellerPartNumber"] = assigned
                po_line["vendor_part"] = assigned
                inv_line["ai_resolution"] = "desc_match"
                po_line["ai_resolution"] = "desc_match"
                patch_log.append({
                    "invoice_line_no": iln,
                    "po_line_no": pln,
                    "action": "assign_synthetic_id_both_sides",
                    "value": assigned
                })

    return {
        "po_id": po_items[0].get("prchseordr_id") if po_items else None,
        "invoice_id": invoice_id,
        "pass": all_matched,
        "fail_reasons": ([] if all_matched else [{"reason": "unmatched-invoice-lines", "lines": [x["invoice_line_no"] for x in unmatched_invoice_lines]}]),
        "id_matches": id_matches,
        "desc_matches": desc_matches,
        "unmatched_invoice_lines": unmatched_invoice_lines,
        "unused_po_lines": unused_po_lines,
        "accept_threshold": accept_threshold,
        # NEW:
        "invoice_items_resolved": invoice_items_resolved,
        "po_items_resolved": po_items_resolved,
        "patch_log": patch_log,
        "ai_resp":ai_resp
        
        
        
    }







def sortlinenumbers(podata,line_items):
    poview=[]
    for po  in podata:
        part_number_po=po['vendor_part']
        ordered = po['qty_ordered_line']
        received = po['qty_received_imhstry']
        vouchered = po['qty_vouchered']
        unitcost=po['unit_cost']
        elegibletobevouchered=received - vouchered
        if(elegibletobevouchered>0):
             poview.append({
            'line_source':po.get('line_source'),   #might delete later
            'line_number': po.get('line_no'),
            'item_id': po.get('vendor_part', '').lower(),
            'quantity': '0',       
            'unit_cost': 0,    
            'amount': 0         
        })
      

    items_by_line = {
        norm(item.get('line_number')): item
        for item in line_items
        if item.get('line_number') is not None
    }

    for i, row in enumerate(poview):
        key = norm(row.get('line_number'))
        if key in items_by_line:
            # Replace the whole dict with the corresponding line_item
            poview[i] = items_by_line[key].copy()  # .copy() to avoid aliasing

      # renumber line_number from 1..N in current order
    for new_num, item in enumerate(poview, start=1):
        item['line_number'] = new_num

    return poview


def check_taxinfo(PoData,invoice_data): 
    
    
    gl_entity = PoData[0]['gl_entity_id'].lower()
    
    
    job_id = PoData[0]['job_id'].upper()
    job_id = job_id[:2]
    glaccountvalue=''
    print('JOBBBBBBBB ID:' )
    
    if  gl_entity:
        gl_entity = gl_entity[:2] + 'a99'
        authorityid = tax_mock.get(gl_entity) # returns value or None if not found
        glaccountvalue=glaccount.get(gl_entity)
        print("TTTAAAXXX-gl:")
    else:
        gl_entity=jobidtoglentity.get(job_id)
        authorityid = tax_mock.get(gl_entity) # returns value or None if not found
        glaccountvalue=glaccount.get(gl_entity)
        print("TTTAAAXXX-jobid:")
    
    taxbase=invoice_data[0]['InvoiceDetailSummary:NetAmount'] - invoice_data[0]['InvoiceDetailItem:Tax'] - invoice_data[0]['InvoiceDetailSummary:SpecialHandlingAmount']
    taxamount=invoice_data[0]['InvoiceDetailItem:Tax']
    rate = round(taxamount / taxbase * 100, 4)  if taxbase else 0.0
    
    
    tax_info = {
        "authority_id": authorityid,
        "gl_account": glaccountvalue,
        "tax_base": f"{taxbase:.3f}",
        "rate": f"{rate:.4f}",
        "tax_amount": f"{taxamount:.3f}"
    }
    print(tax_info)
    
    return tax_info





def send_email(emailcontent: str):
    # === STEP 1: CONFIGURATION from environment ===
    tenant_id    = _get_env("AZURE_TENANT_ID")
    client_id    = _get_env("AZURE_CLIENT_ID")
    client_secret= _get_env("AZURE_CLIENT_SECRET")
    user_email   = _get_env("AZURE_GRAPH_USER_EMAIL")  # mailbox to send-as

    # === STEP 2: AUTHENTICATE AND GET TOKEN ===
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    token_data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default"
    }

    try:
        token_response = requests.post(token_url, data=token_data, timeout=20)
        token_response.raise_for_status()
        access_token = token_response.json()["access_token"]
        print("Authenticated successfully.")
    except Exception as e:
        raise RuntimeError(f"Failed to authenticate: {e}")

    # === STEP 3: SET AUTH HEADER ===
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # === STEP 4: BUILD EMAIL PAYLOAD ===
    email_payload = {
        "message": {
            "subject": "INV12",
            "body": {"contentType": "Text", "content": emailcontent},
            "toRecipients": [{"emailAddress": {"address": user_email}}],  # change if needed
        },
        "saveToSentItems": "true",
    }

    # === STEP 5: SEND THE EMAIL ===
    send_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/sendMail"
    try:
        send_response = requests.post(send_url, headers=headers, json=email_payload, timeout=20)
        if send_response.status_code == 202:
            print("Email sent successfully.")
        else:
            raise RuntimeError(f"Failed to send email: {send_response.status_code} - {send_response.text}")
    except Exception as e:
        raise RuntimeError(f"Error sending email: {e}")

 

   

        
def can_close_po(invoice_items, po_items):
    #how many units are invoiced per item
    invoice_qty_by_item = {}
    for item in invoice_items:
        part_number = item['SellerPartNumber'].lower()
        invoice_qty_by_item[part_number] = invoice_qty_by_item.get(part_number, 0) + int(item['InvoiceDetailItem:quantity'])

    close_po = True  

    for po in po_items:
        item_id = po['vendor_part'].lower()
        ordered = po['qty_ordered_line']
        received = po['qty_received_imhstry']
        vouchered = po['qty_vouchered']

        eligible_to_voucher = received - vouchered
        invoice_qty = invoice_qty_by_item.get(item_id, 0)

        #  If item not fully received, PO cannot be closed
        if received < ordered:
            close_po = False
            print(f" Cannot close PO: item '{item_id}' not fully received.")
            continue

        # If invoice does not voucher all received-but-unvouchered units
        if invoice_qty < eligible_to_voucher:
            close_po = False
            print(f" Cannot close PO: item '{item_id}' still has {eligible_to_voucher - invoice_qty} unvouchered units.")

    return close_po


# keep in mind check here if invoice has multiple same SellerPartNumber id-s , if it has add the quantities of those  items together.
#validate if invoice is trying to overvouch
def validatevouch(invoice_items, po_items):
    matching_pos = []
    for item in invoice_items:
        part_number = item['SellerPartNumber'].lower()
        matching_pos += [po for po in po_items if po['vendor_part'].lower() == part_number]
        
    isVoucherEligible = True;     
        
    for match in matching_pos:
        part_number_po=match['vendor_part']
        ordered = match['qty_ordered_line']
        received = match['qty_received_imhstry']
        vouchered = match['qty_vouchered']
        unitcost=match['unit_cost']
        elegibletobevouchered=received - vouchered

        totalpo_line_item=ordered*unitcost
        allowed_price_peritem=(totalpo_line_item +100) /ordered

       
        invoice_item = next((item for item in invoice_items if item['SellerPartNumber'].lower() == part_number_po.lower()),None)# there will always be one
        if (elegibletobevouchered < int(invoice_item['InvoiceDetailItem:quantity']) or ordered < received or  match['unit_cost'] == int(invoice_item['InvoiceDetailItem:UnitPrice'])) :
            isVoucherEligible = False
        print("Part Number:")    
        print(f"{part_number_po}:Quantity Ordered={ordered},Quantity Received={received},Quantity Vouchered={vouchered},elegibletobevouchered={elegibletobevouchered}, Quantity(invoiced)={invoice_item['InvoiceDetailItem:quantity']}, po_price={match['unit_cost']}, invoice_price={invoice_item['InvoiceDetailItem:UnitPrice']}")
     # Find matching PO line item
        
        print("ALLOWED PRICE PER ITEM:")
        
        print(allowed_price_peritem)
        print("Total item PO_line:")
        print(totalpo_line_item)
    
    print(isVoucherEligible)
    return isVoucherEligible;    

def check_for_duplicate_items(invoice):
    seen = set()
    duplicates = set()

    for item in invoice:
        part_number = item['SellerPartNumber'].lower().strip()
        if part_number in seen:
            duplicates.add(part_number)
        else:
            seen.add(part_number)

    if duplicates:
        print("Duplicate item IDs found:", list(duplicates))
        return False

    return True
    
     
    
    # validate if each item in the po exists in the invoice.
def validate_invoice_items_against_po(invoice_items, po_items):
    
    invoice_item_ids = {item['SellerPartNumber'].lower() for item in invoice_items}
    po_item_ids = {item['vendor_part'].lower() for item in po_items}

    
    unmatched_items = invoice_item_ids - po_item_ids

    if unmatched_items:
        print("These item_ids are not in the PO:", unmatched_items)
        return False
    else:
        print("All item_ids in the invoice are present in the PO.")
        return True
    
#check if invoice exist and then if po exists
def validate_single_po(invoiceID,invoice_data,PoData):
    # Find invoice by ID
    
    invoice = next((inv for inv in invoice_data if inv['invoiceID'].lower() == invoiceID.lower()), None)
    
    
    if not invoice:
        return {'status': 'error', 'message': f'Invoice ID {invoiceID} not found.'}, 404

    invoice_po_number = invoice['PONumber'].lower()
    invoice_no = invoice['invoiceID'].lower()
    print('InvoiceNo:')
    print(invoice_no)
    print('PONumber:')
    print(invoice_po_number)
   
    #invoice_po_number='368526'  #Delete later 
    purchase_order = next((po for po in PoData if po['prchseordr_id'].lower() == invoice_po_number), None)
    
    if not purchase_order:
        return {'status': 'error', 'message': f'purchase order id  {invoice_po_number} not found.'}, 404
    print("FOUND PO FOR THIS INVOICE")
   
    return True   

    
    
# API Endpoint
@app.route('/invoice/<string:invoiceID>', methods=['GET'])
def get_po_data(invoiceID):
    # result=invoice_data
    line_items=[]
    charges=[]
    tax_info = []
    extra_charge_count=0
    line_item_count=0
    
    dbinvoicedata = getDBRecordById(invoiceID)
    invoice_data=clean_invoice_data(dbinvoicedata)

    invoice_datapo=invoice_datapo = next(
    (rec.get('PONumber') for rec in (invoice_data or []) if isinstance(rec, dict) and 'PONumber' in rec),
    None
)

    testinvoice_datapo='368526'

    PoDbData=getDBPORecordById(invoice_datapo)
    PoData= clean_po_line_data(PoDbData)
    print(PoData)
    #print(PoData)
    
    print(invoice_data)
    #Validate Invoice against PO if it passes calculate tax etc.
    result = validate_single_po(invoiceID,invoice_data,PoData)
    
    
    if result is not True:
        return jsonify(result[0]), result[1]


    #function to replace 
    # if not validate_invoice_items_against_po(invoice_data, PoData):
    #     return jsonify({'status': 'error', 'message': 'Invoice item mismatch'}), 400
    
    resp = validate_and_match_invoice_items_against_po_strict(
    invoice_id=invoice_data[0]['invoiceID'],
    invoice_items=invoice_data,
    po_items=PoData,
    ai_match_fn=chatgpt_match_by_description,
    accept_threshold=0.80
    )

    if resp["pass"]:
        # New po and invoice structures from validate_and_match function with all the id-s 
        invoice_items_ready = resp["invoice_items_resolved"]
        po_items_ready      = resp["po_items_resolved"]
    else:
        # Inspect why it failed
        #print("aiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiii response")
        #print(resp["ai_resp"])
        
        #print(resp.get("desc_attempts", []))
        return {
        "fail_reasons": resp["fail_reasons"],
        #"desc_matches": resp["desc_matches"],
        #"AI_Response": resp["ai_resp"]
        }
        
       

    #print("INVOICE ITEMS AFTER VALIDAAAAATIIIIIONNNNNNN")
    #print(invoice_items_ready)

    if not check_for_duplicate_items(invoice_data):

        return jsonify({'status': 'error', 'message': 'Duplicate item IDs found'}), 400
    if not validatevouch(invoice_data, PoData):
        return jsonify({'status': 'error', 'message': 'Vouchering failed'}), 400
    
    
    close_po=can_close_po(invoice_data, PoData)
    print("Can close po:")
    print(close_po)
    #check Db if it has taxes
    IsInlineTax=invoice_data[0]['isTaxInLine']
    shared_special_handling=invoice_data[0]['InvoiceDetailSummary:SpecialHandlingAmount']

    if IsInlineTax=='yes':
        hastax=True
        tax_info=check_taxinfo(PoData,invoice_data)
        
    else:
        hastax=False
        
    
        #check if freight is there 
    if shared_special_handling is not None and shared_special_handling > 0 and shared_special_handling<=500:
        hasextracharges=True
        extra_charge_count=extra_charge_count+1
        
        charges.append({
            'charge_number':extra_charge_count,
            'quantity': ('1'),
            'unit_cost': shared_special_handling,
            'cost_category': ('FREIGHT'),
            'description': ('Freight Charge'),
        })
        print("Extra Charges:")
        print(charges)
    elif shared_special_handling>500:
         return jsonify({'status': 'error', 'message': 'Freight needs manual review, Freight exceeds 500 Dollars!'}), 400
    else:
        hasextracharges=False
        
    
        

    # if shared_shipping is not None and shared_shipping >0 and shared_shipping<=200:
    #       hasextracharges=True
    #       extra_charge_count=extra_charge_count+1
    #       charges.append({
    #         'charge_number':extra_charge_count,
    #         'quantity': ('1'),
    #         'unit_cost': shared_shipping,
    #         'cost_category': ('202'),
    #         'description': ('Handling fee'),
    #     })
          
    
    for item in invoice_data:
        item_id = item['SellerPartNumber'].lower()
        unit_price = item['InvoiceDetailItem:UnitPrice'] 
        quantity = item['InvoiceDetailItem:quantity']
        line_item_count=line_item_count+1
        poitem= next((po for po in PoData if po['vendor_part'].lower() == item_id), None)
        line_number=poitem['line_no']
        line_source=poitem['line_source']
        line_items.append({
        'line_number':line_number,#this value has to come from sampro db
        'line_source':line_source,
        'item_id': item_id,
        'quantity': quantity,
        'unit_cost': unit_price,
        'amount': int(quantity)*unit_price
        
            
        
    })
        
    poview=sortlinenumbers(PoData,line_items)
    print(poview)

   #get gl_entity by glentty or by job_id
    short_gl=''
    gl_entity = PoData[0]['glentty_id'].lower()
    job_id = PoData[0]['jb_id'].upper()
    
    if  gl_entity:
        short_gl = PoData[0]['glentty_id'].lower()
        gl_entty = short_gl[:2] + 'a99'
    else:
        job_id = job_id[:2]
        gl_entty=jobidtoglentity.get(job_id)
        gl_entty = gl_entty[:2] + 'a99'
       
        
        print("glentity-jobid:")
    response = {
        'type': 'general_info',
        'po_number': invoice_data[0]['PONumber'],    
        'invoice_number': invoice_data[0]['invoiceID'],
        'invoice_date': invoice_data[0]['createdAt'],
        
        'invoice_total': invoice_data[0]['InvoiceDetailSummary:NetAmount'],
        'gl_entity_id':gl_entty,
        'has_taxes': hastax,
        'tax_info': tax_info,
        'has_extra_charges': hasextracharges,
        'extra_charge_count':extra_charge_count,
        'extra_charges': charges,
        'line_items':poview,
        
        'line_item_count':line_item_count,
        
        'close_po': close_po, 
        'invoice_file_path': ""
    }

    uiresponse=transform_for_ui(response)
    #emailcontent = "\n".join(json.dumps(obj) for obj in uiresponse)
    emailcontent = ""

    chunks = [json.dumps(obj) for obj in uiresponse]
    emailcontent = chunks[0]  # first object with no delimiter

    for chunk in chunks[1:]:
        emailcontent += "\n?()?\n" + chunk

    #emailcontent += "\n?()?\n"
    send_email(emailcontent)
    print("Invoice Processed Successfully.")
    print("TOTAL:",invoice_data[0]['InvoiceDetailSummary:NetAmount'])



    print(charges)

    return jsonify(uiresponse)

if __name__ == '__main__':
    app.run(debug=True)
