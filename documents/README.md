# Financial Documents

This folder is organized by NSE symbol.

Drop company PDFs into the matching folder:

```text
documents/TCS/Q4_FY26_results.pdf
documents/TCS/Annual_Report_FY25.pdf
documents/INFY/Q1_FY26_results.pdf
```

Preferred sources:

- company investor-relations pages
- NSE/BSE disclosures
- annual reports
- quarterly results
- investor presentations
- earnings-call transcripts

After adding or updating PDFs, rebuild the local vector database:

```powershell
python app.py --ingest-documents
```

