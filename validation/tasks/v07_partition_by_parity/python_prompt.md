# Task: group integers by parity into a dict[str, list[int]]

Write `partition(xs: list[int]) -> dict[str, list[int]]` returning a dictionary
with keys `"even"` and `"odd"`. Both keys are always present, using empty lists
when no member exists. Then write `render(m: dict[str, list[int]]) -> str` that
produces `even=[...] odd=[...]` with the items separated by commas and no
spaces inside the lists.

In `main`, print the rendered partition for each list, one per line:

    [1, 2, 3, 4, 5]
    []
    [2, 4, 6]
    [1]

Expected output:

    even=[2,4] odd=[1,3,5]
    even=[] odd=[]
    even=[2,4,6] odd=[]
    even=[] odd=[1]
