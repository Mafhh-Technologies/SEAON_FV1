# SAMPLE DATA IMPORTER: Excel files in Backend/sample_data are converted into SQLite records.
import hashlib
import json
import re
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import openpyxl
from django.core.management.base import BaseCommand
from django.db import transaction

from erp.models import StockRecord, Product, Inventory, StockMovement, InventoryBatch

NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")

def text(value):
    return "" if value is None else str(value).strip()

def number(value):
    if value is None or text(value) == "":
        return None
    try:
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        m = NUMBER_RE.search(text(value))
        return Decimal(m.group()) if m else None

def norm(value):
    return re.sub(r"[^a-z0-9]+", " ", text(value).lower()).strip()

def find_col(headers, *names):
    for name in names:
        target=norm(name)
        for i,h in enumerate(headers):
            if target == norm(h) or target in norm(h):
                return i
    return None

def row_value(row, headers, *names):
    i=find_col(headers,*names)
    return row[i] if i is not None and i < len(row) else None

def looks_like_header(row):
    vals=[norm(x) for x in row]
    joined=" ".join(vals)
    return ("s no" in joined or "item name" in joined or "item" in vals or "name" in vals) and (
        "minimum" in joined or "available" in joined or "qty" in joined
    )

def is_number_first(row):
    return bool(row) and row[0] is not None and text(row[0]).replace(".","",1).isdigit()

def title_from_context(context, filename, sheet):
    title=[text(x) for x in context if text(x)]
    return title[-1] if title else f"{Path(filename).stem} / {sheet}"

def detect_date(rows):
    for row in rows[:4]:
        for value in row:
            if isinstance(value, (datetime,date)):
                return value.date() if isinstance(value,datetime) else value
    return None

class Command(BaseCommand):
    help="Import all supplied SEAON Excel stock sheets into SQLite."

    @transaction.atomic
    def handle(self,*args,**kwargs):
        base=Path(__file__).resolve().parents[3]/"sample_data"
        if not base.exists():
            self.stdout.write(self.style.WARNING("sample_data folder not found; nothing to import."))
            return

        total=0
        for path in sorted(base.glob("*.xlsx")):
            wb=openpyxl.load_workbook(path,data_only=True,read_only=True)
            for ws in wb.worksheets:
                rows=list(ws.iter_rows(values_only=True))
                stock_date=detect_date(rows)
                current_context=[Path(path).stem, ws.title]
                headers=None

                for row_index,row in enumerate(rows,start=1):
                    values=[text(x) for x in row]

                    if looks_like_header(row):
                        headers=list(row)
                        continue

                    if headers is None:
                        # Boxes sheet has its header in the first row and no S.No label.
                        joined=" ".join(values).lower()
                        if "minimum stock" in joined and ("available" in joined or "qty" in joined):
                            headers=list(row)
                        continue

                    if not is_number_first(row):
                        non_empty=[text(x) for x in row if text(x)]
                        if len(non_empty) == 1:
                            current_context=[non_empty[0]]
                        continue

                    if is_number_first(row):
                        # Do not turn an empty template row into fake stock.
                        if sum(1 for value in row if text(value)) < 2:
                            continue
                        raw={text(headers[i]) if i < len(headers) else f"column_{i+1}":
                             row[i] for i in range(len(row)) if row[i] is not None}

                        item=row_value(row,headers,"item name","item","name")
                        size=row_value(row,headers,"size","size (mm x mtr)")
                        color=row_value(row,headers,"colour","color")
                        thickness=row_value(row,headers,"thickness (mm)","thickness x meter")
                        width=row_value(row,headers,"width (mm)")
                        length=row_value(row,headers,"length (meters)")
                        jumbo=row_value(row,headers,"jumbo rolls","minimum stock log rolls")
                        minimum=row_value(row,headers,"minimum stock")
                        unit=row_value(row,headers,"unit of measure","units of measure")
                        available=row_value(row,headers,"available stock","available qty","qty")
                        required=row_value(row,headers,"required stock","required  stock")
                        remark=row_value(row,headers,"remark")

                        # In a section like VHB LOG, item name may be present and
                        # the section title is useful context.
                        category=title_from_context(current_context,path.name,ws.title)
                        if text(item):
                            current_context=[category]

                        record_defaults={
                            "stock_date":stock_date,
                            "category":category,
                            "item_name":text(item),
                            "size":text(size),
                            "color":text(color),
                            "thickness":text(thickness),
                            "width":text(width),
                            "length":text(length),
                            "jumbo_rolls":number(jumbo),
                            "minimum_stock":number(minimum),
                            "unit":text(unit),
                            "available_stock":number(available),
                            "required_stock":number(required),
                            "remark":text(remark),
                            "raw_data":json.dumps(raw,default=str),
                        }

                        obj,created=StockRecord.objects.update_or_create(
                            source_file=path.name,
                            source_sheet=ws.title,
                            source_row=row_index,
                            defaults=record_defaults,
                        )
                        total += int(created)

                        if obj.item_name:
                            # Give each source row a stable SKU so re-imports never duplicate it.
                            raw_key=f"{path.name}|{ws.title}|{row_index}"
                            sku="IMP-"+hashlib.sha1(raw_key.encode()).hexdigest()[:12].upper()
                            variant=" ".join(x for x in [obj.size,obj.color,obj.thickness,obj.width,obj.length] if x)
                            product_name=obj.item_name if not variant else f"{obj.item_name} - {variant}"
                            product_type="raw-material"
                            low_category=category.lower()
                            if "box" in low_category: product_type="finished"
                            if "gasket" in low_category: product_type="component"
                            if "foam" in low_category: product_type="raw-material"

                            product,_=Product.objects.update_or_create(
                                sku=sku,
                                defaults={
                                    "name":product_name[:160],
                                    "product_type":product_type,
                                    "unit":obj.unit or "pcs",
                                    "minimum_stock":obj.minimum_stock or 0,
                                    "location":"Imported Stock",
                                    "size":obj.size,
                                    "color":obj.color,
                                    "thickness":number(obj.thickness),
                                    "is_active":True,
                                }
                            )
                            Inventory.objects.update_or_create(
                                product=product,
                                defaults={"quantity":obj.available_stock or 0},
                            )

                            # Create one opening/import batch so FIFO can work immediately.
                            batch_code="IMP-"+hashlib.sha1(raw_key.encode()).hexdigest()[:16].upper()
                            received=obj.stock_date or date.today()
                            qty=obj.available_stock or Decimal("0")
                            InventoryBatch.objects.update_or_create(
                                batch_code=batch_code,
                                defaults={
                                    "product":product,
                                    "received_date":received,
                                    "vendor":"",
                                    "quantity":qty,
                                    "remaining_quantity":qty,
                                    "unit_cost":Decimal("0"),
                                },
                            )

            wb.close()

        self.stdout.write(self.style.SUCCESS(f"Imported/updated {total} stock rows from {len(list(base.glob('*.xlsx')))} Excel files."))
