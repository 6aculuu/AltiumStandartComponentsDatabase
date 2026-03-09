import os
import pyodbc
import itertools

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
SRC_DB_PATH = os.path.join(BASE_DIR, "AltiumParameters.accdb")
DST_DB_PATH = os.path.join(BASE_DIR, "AltiumStandartComponentsDatabase.accdb")

for path in (SRC_DB_PATH, DST_DB_PATH):
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Файл базы данных не найден: {path}")

def connect_accdb(path):
    return pyodbc.connect(
        rf"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};"
        rf"DBQ={path};"
    )

COMPONENTS_CONFIG = {
    "Resistor": {
        "src_table":    "Resistor_params",
        "param_fields": ["Package", "Value", "Tolerance"],  
        "dst_table":    "Resistor",
        "dst_fields": [
            "Part Number","Description",
            "Library Ref","Footprint Ref",
            "Library Path","Footprint Path",
            "Package","Value","Tolerance"
        ],
        "templates": {
            "Part Number":    "R_{Package}_{Value}_{Tolerance}",
            "Description":    "Resistor {Value} tolerance:{Tolerance} package:{Package}",
            "Library Ref":    "Resistor",
            "Footprint Ref":  "STACKPOLE CSR{Package}",
            "Library Path":   "SCH - PASSIVES - RESISTOR.SchLib",
            "Footprint Path": "PCB - RESISTOR - CHIP - STACKPOLE CSR{Package}.PcbLib"
        }
    },
    "CAPACITOR MLCC": {
        "src_table":    "Capacitor_MLCC_params",
        "param_fields": ["Package", "Capacity", "Voltage"],  
        "dst_table":    "Capacitor_MLCC",
        "dst_fields": [
            "Part Number","Description",
            "Library Ref","Footprint Ref",
            "Library Path","Footprint Path",
            "Package", "Capacity", "Voltage"
        ],
        "templates": {
            "Part Number":    "C_MLCC_{Package}_{Capacity}_{Voltage}",
            "Description":    "Capacitor MLCC {Capacity} {Voltage} package:{Package}",
            "Library Ref":    "Capacitor",
            "Footprint Ref":  "CAP {Package}",
            "Library Path":   "SCH - PASSIVES - CAPACITOR.SchLib",
            "Footprint Path": "PCB - CAPACITOR - MLCC - CAP {Package}.PcbLib"
        }
    },
    "LED": {
        "src_table":    "LED_params",
        "param_fields": ["Package", "Color", "Forward Voltage", "Forward Current"],
        "dst_table":    "LED",
        "dst_fields": [
            "Part Number","Description",
            "Library Ref","Footprint Ref",
            "Library Path","Footprint Path",
            "Package","Color","Forward Voltage","Forward Current"
        ],
        "templates": {
            "Part Number":    "LED_{Package}_{Color}",
            "Description":    "LED {Color} package:{Package}",
            "Library Ref":    "LED",
            "Footprint Ref":  "LED {Package} {Color}",
            "Library Path":   "SCH - DIODES - LED.SchLib",
            "Footprint Path": "PCB - LED - LED {Package} {Color}.PcbLib"
        }
    },
}

def fetch_distinct(conn, table, field):
    """
    Пытаемся вернуть уникальные непустые значения field из table.
    Если поле не существует или другой SQL-ошибки — возвращаем [''].
    """
    sql = (
        f"SELECT DISTINCT [{field}] "
        f"FROM [{table}] "
        f"WHERE [{field}] IS NOT NULL AND [{field}] <> ''"
    )
    cur = conn.cursor()
    try:
        rows = cur.execute(sql)
        vals = [getattr(row, field) for row in rows]
        # если строк не было, считаем, что есть только пустое
        return vals if vals else [""]
    except pyodbc.Error as e:
        print(f"Warning: cannot fetch field '{field}' from '{table}': {e}. Using [''].")
        return [""]

def process_component(cfg):
    # 1) Собираем список списков значений параметров,
    #    подставляя [""] если нет ни одного реального.
    conn_src = connect_accdb(SRC_DB_PATH)
    param_lists = [
        fetch_distinct(conn_src, cfg["src_table"], fld)
        for fld in cfg["param_fields"]
    ]
    conn_src.close()

    # 2) Очищаем целевую таблицу
    conn_dst = connect_accdb(DST_DB_PATH)
    cur_dst = conn_dst.cursor()
    cur_dst.execute(f"DELETE FROM [{cfg['dst_table']}];")
    conn_dst.commit()

    # 3) Готовим INSERT
    placeholders = ", ".join("?" for _ in cfg["dst_fields"])
    fields_sql   = ", ".join(f"[{f}]" for f in cfg["dst_fields"])
    insert_sql = (
        f"INSERT INTO [{cfg['dst_table']}] "
        f"({fields_sql}) VALUES ({placeholders});"
    )

    # 4) Генерируем все комбинации и вставляем
    count = 0
    for combo in itertools.product(*param_lists):
        params = dict(zip(cfg["param_fields"], combo))
        row_values = []
        # сначала шаблонные поля
        for fld in cfg["templates"]:
            row_values.append(cfg["templates"][fld].format(**params))
        # затем сами значения полей (включая пустые)
        for fld in cfg["param_fields"]:
            row_values.append(params[fld])
        cur_dst.execute(insert_sql, row_values)
        count += 1

    conn_dst.commit()
    cur_dst.close()
    conn_dst.close()
    print(f"[{cfg['dst_table']}] inserted {count} rows.")

if __name__ == "__main__":
    for name, cfg in COMPONENTS_CONFIG.items():
        print(f"Processing {name}…")
        process_component(cfg)
