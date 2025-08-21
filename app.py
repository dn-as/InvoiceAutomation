from flask import Flask, jsonify
import pyodbc
import mysql.connector
print(pyodbc.version)



app = Flask(__name__)
#conn = pyodbc.connect(
#    r'DRIVER={ODBC Driver 17 for SQL Server};'
#   r'SERVER=SAMPRODBSERVER;'
#    r'DATABASE=DayNite_Test;'
#   r'Trusted_Connection=yes;'
#)

#cursor = conn.cursor()
#cursor.execute("select top 10 prchseordr_rn from prchseordrlst  ")

#for row in cursor.fetchall():
#    print(row)

#conn.close()
# MySQL connection
# conn_mysql = mysql.connector.connect(
#     host='daynite.c4qbs9ngauhk.us-east-1.rds.amazonaws.com',
#     port=3306,  
#     user='dayniteuser',
#     password='asd123ASD!@#',
#     database='marketplace'
# )
# cursor_mysql = conn_mysql.cursor(dictionary=True)
# cursor_mysql.execute( """
# SELECT 
#     invoiceID,
#     invoiceDate,
#     `InvoiceDetailSummary:SubtotalAmount`,
#     isTaxInLine,
#     `InvoiceDetailItem:Tax`,
#     `InvoiceDetailSummary:ShippingAmount`,
#     `InvoiceDetailSummary:SpecialHandlingAmount`,
#     SellerPartNumber,
#     `InvoiceDetailItem:quantity`,
#     `InvoiceDetailItem:UnitPrice`,
#     `InvoiceDetailItem:UnitOfMeasure`,
#     ItemDescription
# FROM InvoiceItems
# WHERE invoiceDate LIKE '%2025-07%'
# LIMIT 1;
# """)
# data=cursor_mysql.fetchall()
# cursor_mysql.close()
# conn_mysql.close()


def getDBRecordById(po_id):
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
        isTaxInLine,
        `InvoiceDetailItem:Tax`,
        `InvoiceDetailSummary:ShippingAmount`,
        `InvoiceDetailSummary:SpecialHandlingAmount`,
        SellerPartNumber,
        `InvoiceDetailItem:quantity`,
        `InvoiceDetailItem:UnitPrice`,
        `InvoiceDetailItem:UnitOfMeasure`,
        ItemDescription
    FROM InvoiceItems
    WHERE invoiceDate LIKE '%2025-07%' AND invoiceID = %s
                         
                         
    LIMIT 1;
    """, (po_id,))
    data=cursor_mysql.fetchall()
    cursor_mysql.close()
    conn_mysql.close()
    return data









#Simulated tax info lookup (normally  DB)
GL_ENTITY_TAX_MAP = {
    'GL123': {
        'authority_id': 'AUTH001',
        'gl_account': 'ACCT100',
        'tax_base': '1000.00',
        'rate': '0.07',
        'tax_amount': '70.00'
    },
    'GL456': {
        'authority_id': 'AUTH002',
        'gl_account': 'ACCT200',
        'tax_base': '500.00',
        'rate': '0.1',
        'tax_amount': '50.00'
    }
}


@app.route('/get_po_data/<process_order_id>', methods=['GET'])
def get_po_data(process_order_id):

    myRecord = getDBRecordById(process_order_id)

    print("Hereee")
    print(myRecord)
    print(myRecord[0]['invoiceID'])



    matches = [row for row in myRecord if row['invoiceID'] == process_order_id]
    if not matches:
        return jsonify({'error': 'PO not found'}), 404

    record = matches[0]

    # has_taxes = float(record.get('prchseordrlstgn_tx_cst', 0)) > 0
    # has_extra = record.get('prchseordrlstgn_extra', False)
    # gl_entity_id = record.get('glentty_rn')
    # tax_info = GL_ENTITY_TAX_MAP.get(gl_entity_id, {}) if has_taxes else {}

    # charges = []
    # if has_extra:
    #     charges.append({
    #         'quantity': record.get('prchseordrlstgn_qntty_ordrd'),
    #         'unitCost': record.get('prchseordrlstgn_unt_cst'),
    #         'costcategory': record.get('jbcstctgry_rn'),
    #         'description': record.get('prchseordrlstgn_dscrptn'),
    #     })

    items = []

    items.append({
        'item_id': record.get('SellerPartNumber'),
        'quantity': record.get('InvoiceDetailItem:quantity'),
        'qtybilled': record.get('InvoiceDetailItem:quantity'),
        'unit_cost': record.get('InvoiceDetailItem:UnitPrice'),
        'total_amount': record.get('InvoiceDetailSummary:SubtotalAmount'),
        
    })

    # amount_vouchered = float(record.get('prchseordrlstgn_cst_rcvd'))
    # amount_received = float(record.get('prchseordrlstgn_cst_extndd'))
    # close_po = amount_vouchered >= amount_received

    response = {
        'po_number': record.get('PONumber'),
        'invoice_id': record.get('invoiceID'),
        'invoice_date': record.get('invoiceDate'),
        'invoice_total': record.get('InvoiceDetailSummary:SubtotalAmount'),
        # 'gl_entity_id': gl_entity_id,
        'hastaxes': record.get('isTaxInLine'),
        #  'taxinfo': tax_info,
        # 'hasextracharges': has_extra,
        # 'charges': charges,
        'items': items,
        
        # 'closepo': close_po,
        # 'invoice_file_path': f"/invoices/{record.get('wrkordr_rn')}.pdf"
    }

    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True)
