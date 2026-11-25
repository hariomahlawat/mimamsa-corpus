import csv, sys
T = list(csv.DictReader(open(sys.argv[1])))
for t in T:
    if t["source_key"] == sys.argv[2] and t["pdf_page"] == sys.argv[3]:
        print(f'{t["seq"]:>3} {t["form_family_id"][5:]:<18} {t["field_kind"][:5]:<5} {t["legibility"][:5]} | {t["field_label_as_printed"]}')
