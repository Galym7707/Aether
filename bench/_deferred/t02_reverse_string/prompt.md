# Task: reverse a string

Write an Aether program with a function `reverseString(s: String) returns String` that
returns its argument reversed. The function must be `pure`. Then in `main`, print:

    reverseString("aether")
    reverseString("")
    reverseString("a")
    reverseString("racecar")

one per line.

Expected output:

    rehtea
    
    a
    racecar

(Note: the second line is empty because the empty string reversed is the empty string.)

You may not call any pre-built reverse function on a String — you must build it
character-by-character using `slice` and `join` and `length`, possibly via a `List<String>`.
