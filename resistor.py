import os
import pyodbc
import itertools

# Определяем директорию скрипта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Полные пути к файлам .accdb
SRC_DB_PATH = os.path.join(BASE_DIR, "AltiumParameters.accdb")
DST_DB_PATH = os.path.join(BASE_DIR, "AltiumStandartComponentsDatabase.accdb")

# Проверяем существование файлов перед подключением
for path in (SRC_DB_PATH, DST_DB_PATH):
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Файл базы данных не найден: {path}")

# Функция для создания соединения
def connect_accdb(db_path):
    conn_str = (
        rf"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};"
        rf"DBQ={db_path};"
    )
    return pyodbc.connect(conn_str)

# 1) Читаем параметры из первой БД, сразу фильтруем пустые/NULL значения
conn_src = connect_accdb(SRC_DB_PATH)
cur_src = conn_src.cursor()

# Используем WHERE … IS NOT NULL AND <> '' для отсева пустых строк
packages = [
    row.Package for row in cur_src.execute(
        "SELECT DISTINCT Package FROM Resistor_params "
        "WHERE Package IS NOT NULL AND Package <> ''"
    )
]
resistances = [
    row.Resistance for row in cur_src.execute(
        "SELECT DISTINCT Resistance FROM Resistor_params "
        "WHERE Resistance IS NOT NULL AND Resistance <> ''"
    )
]
tolerances = [
    row.Tolerance for row in cur_src.execute(
        "SELECT DISTINCT Tolerance FROM Resistor_params "
        "WHERE Tolerance IS NOT NULL AND Tolerance <> ''"
    )
]

cur_src.close()
conn_src.close()

# 2) Очищаем вторую БД и вставляем все комбинации
conn_dst = connect_accdb(DST_DB_PATH)
cur_dst = conn_dst.cursor()

# очищаем таблицу Resistor
cur_dst.execute("DELETE FROM Resistor;")
conn_dst.commit()

insert_sql = """
INSERT INTO Resistor
  ([Part Number],[Description],[Library Ref],[Footprint Ref],
   [Library Path],[Footprint Path],[Package],[Value],[Tolerance],[Comment])
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

count = 0
for pkg, res, tol in itertools.product(packages, resistances, tolerances):
    # формируем и вставляем только если все три параметра непустые
    if not (pkg and res and tol):
        continue

    part_number    = f"R_{pkg}_{res}_{tol}%"
    description    = f"Resistor {res} tolerance:{tol}% package:{pkg}"
    library_ref    = "Resistor"
    footprint_ref  = f"STACKPOLE CSR{pkg}"
    library_path   = "SCH - PASSIVES - RESISTOR.SchLib"
    footprint_path = f"PCB - RESISTOR - CHIP - STACKPOLE CSR{pkg}.PcbLib"
    comment = f"{res}"

    cur_dst.execute(insert_sql, (
        part_number,
        description,
        library_ref,
        footprint_ref,
        library_path,
        footprint_path,
        pkg,
        res,
        tol,
        comment
    ))
    count += 1

conn_dst.commit()
cur_dst.close()
conn_dst.close()

print(f"Inserted {count} resistor components into the database.")
