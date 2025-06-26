# Static-Code-Analyzer


Static Code Analyzer designed for C programming. Its main purpose is to analyze C code without running it and detect common programming mistakes that can lead to bugs, crashes, or security vulnerabilities. This includes identifying:
•	Dangerous functions like gets()
•	Missing break statements in switch-case blocks
•	Use of uninitialized variables
•	Unused variables and functions
•	Constant true/false conditions in if/while
•	Empty block bodies
We used Python with Clang’s Python bindings (libclang) to walk through the Abstract Syntax Tree (AST) of C programs. Our analyzer applies multiple custom rules to scan the code and generate helpful warnings.
