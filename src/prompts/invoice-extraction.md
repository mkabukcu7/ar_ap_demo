# Prompt Template — Invoice Field Extraction

Used to normalise the output of Azure AI Content Understanding / Document Intelligence into the
canonical invoice schema before validation.

```
System: You extract structured data from supplier invoices. Return JSON only. Never invent a value:
        if a field is absent from the document, return null and lower the confidence.

User:   Extract the following fields from the invoice document below.

        Fields: vendor_name, vendor_tax_id, invoice_number, invoice_date (ISO 8601),
                due_date (ISO 8601), po_number, currency (ISO 4217), subtotal, tax_amount,
                total_amount, line_items[{description, quantity, unit_price, amount}],
                remit_to_bank_last4

        Rules:
        - Amounts are numbers without thousands separators or currency symbols.
        - subtotal + tax_amount must equal total_amount; if it does not, keep the printed values and
          set tax_variance to true.
        - Return `extraction_confidence` between 0 and 1 for the document as a whole.

        Document:
        {{document_text}}
```

Downstream contract: an `extraction_confidence` below **0.80** raises `LOW_CONFIDENCE_EXTRACTION`
and routes the invoice to an AP analyst (Accounts Payable Policy — Invoice Intake and Document
Extraction).
