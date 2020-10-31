# C_CppTestCoverage

This is a simple Python based program that creates a copy of C or C++ files
and adds some instrumentation to them. The modified executables will
save files that can be analyzed later by a Python based statistics module.
This software keeps track of the number of times each path has been taken
so it can also be used for optimization.

* cCovInstr.py - Modifies C++ code by looking for conditional statements
 (if, for, while, else) that affect the path taken through the code.
 It creates a copy of the C++ source code and modifies them by incrementing
 a counter for each of these conditionals.

* cCovStats.py - Reads the output from the executed C++ code and generates
 readable statistics.

[coverage.html](coverage.html)
