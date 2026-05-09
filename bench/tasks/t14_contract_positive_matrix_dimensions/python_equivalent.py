def matrix_cells(rows, cols):
    rows = rows if rows > 0 else 1
    cols = cols if cols > 0 else 1
    return rows * cols


print(matrix_cells(0, 5))
