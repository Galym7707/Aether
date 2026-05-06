# Task: group integers by parity into a Map<String, List<Int>>

Write `partition(xs: List<Int>) returns Map<String, List<Int>>` returning a map with keys "even" and "odd". Both keys are always present (use empty lists when no member). Then write `render(m: Map<String, List<Int>>) returns String` that produces "even=[...] odd=[...]" with the items separated by commas (no spaces).

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
