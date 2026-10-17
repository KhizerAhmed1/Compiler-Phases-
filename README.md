**# 🧩 Interactive Compiler Phase & Optimization Analyzer
**
An interactive Python desktop application for learning, analyzing, and demonstrating core concepts of **Compiler Construction**. The application brings compiler phases, intermediate code generation, code optimization, grammar analysis, and parsing-related utilities into one graphical interface.

Developed as a Compiler Construction Lab project by Computer Science students.

## 📌 Project Overview

Understanding compiler construction becomes easier when each phase can be tested and observed independently. This project provides a GUI-based laboratory environment where users can enter source code or grammar rules, select an operation, and view the corresponding results.

Built with Python and Tkinter, the application is designed for students who want to explore how source code is analyzed, how intermediate code is generated, how optimization transforms code, and how context-free grammars are processed.

## ✨ Features

### Compiler Analysis
- **Lexical Analysis:** Identifies keywords, identifiers, numbers, strings, operators, and symbols. Reports invalid characters with line information.
- **Syntax Analysis:** Performs basic structural checks, including delimiter matching and common statement-termination errors.
- **Semantic Analysis:** Builds a basic symbol table and checks for duplicate declarations, undeclared variables, and selected type-related errors.
- **Intermediate Code Generation:** Generates Three-Address Code (TAC) for supported arithmetic assignments, respecting arithmetic precedence and parentheses.
- **AST / Parsing Utilities:** Supports the implemented parsing-related functionality for the project's educational language.

### Code Optimization
Explore five source-level optimization techniques:

| Technique | Purpose |
|---|---|
| Constant Folding | Evaluates supported constant arithmetic expressions. |
| Copy Propagation | Reuses values from simple variable assignments. |
| Dead Code Elimination | Removes assignments whose results are not used later. |
| Common Subexpression Elimination | Reuses previously calculated expressions when recognized. |
| Avoid Unnecessary Calculations | Simplifies patterns such as `x + 0`, `x * 1`, and `x * 2`. |

The optimization interface displays code transformations so users can observe how the source changes.

### Grammar Analysis and Parsing
- **CFG Analysis:** Processes context-free grammar productions.
- **FIRST and FOLLOW:** Calculates FIRST and FOLLOW sets for supported grammars.
- **LL(1) Parsing Table:** Builds a parsing table and reports conflicts where detected.
- **LMD / RMD:** Demonstrates leftmost and rightmost derivations for supported grammars and target strings.
- **Ambiguity Demonstration:** Illustrates ambiguity using a built-in grammar example.
- **Left Recursion Removal:** Transforms grammars containing supported immediate left recursion.
- **Left Factoring:** Extracts common prefixes from grammar alternatives.

### Full Compiler Pipeline
The integrated pipeline combines the major implemented stages into a single workflow, including source analysis, intermediate code generation, optimization, and code-generation-style output.

### Desktop Interface
- Interactive Tkinter graphical interface.
- Source-code and grammar input editor.
- Operation-selection sidebar.
- Syntax highlighting for supported source-language elements.
- Scrollable input and output areas.
- Example input for experimentation.
- Load and save source text.
- Export generated reports to text files.
- Status messages for operations and results.

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core compiler-analysis and transformation logic |
| Tkinter | Desktop graphical user interface |
| Regular Expressions (`re`) | Token recognition and pattern-based analysis |
| `ast` | Safe parsing of supported arithmetic expressions for evaluation |
| `operator` | Arithmetic operations used by the expression evaluator |

**External dependencies:** The documented implementation uses Python's standard library and does not require third-party packages for its core functionality.

## 🏗️ System Architecture

The application follows a modular architecture in which the GUI collects user input, dispatches the selected operation, and displays the generated result.

```text
              User Input
                  |
                  v
          +------------------+
          |   Tkinter GUI    |
          +------------------+
                  |
                  v
          +------------------+
          | Operation        |
          | Dispatcher       |
          +------------------+
                  |
        +---------+----------+
        |         |          |
        v         v          v
     Compiler  Optimization  Grammar
      Phases     Modules     Utilities
        |         |          |
        +---------+----------+
                  |
                  v
          +------------------+
          | Output & Reports |
          +------------------+
```

## 🚀 Getting Started

### Prerequisites

- Python 3 installed on your computer.
- A working Python installation with Tkinter support.
- Git (optional, for cloning the repository).

Check your Python installation:

```bash
python --version
```

On Windows, if `python` is not recognized, try:

```bash
py --version
```

### Installation

**1. Clone the repository**

Replace `YOUR_USERNAME` with your GitHub username.

```bash
git clone https://github.com/YOUR_USERNAME/compiler-construction-lab.git
```

**2. Navigate to the project directory**

```bash
cd compiler-construction-lab
```

**3. Run the application**

If the main source file is named `compiler_construction_lab.py`, run:

```bash
python compiler_construction_lab.py
```

Alternatively, on Windows:

```bash
py compiler_construction_lab.py
```

If your main file has a different name, replace the filename in the command accordingly.

The application should open in a desktop window where you can select an operation, enter source code or grammar rules, and inspect the results.

## 💻 Usage Guide

### Example 1: Lexical Analysis

Enter the following source code:

```c
int age = 20;
float price = 15.5;
```

Select **Lexical Analysis** and run the operation.

The analyzer identifies tokens such as keywords, identifiers, numbers, operators, and symbols.

### Example 2: Intermediate Code Generation

Input:

```c
int result = 2 + 3 * 4;
```

Possible output:

```text
t1 = 3 * 4
t2 = 2 + t1
result = t2
```

This demonstrates how operator precedence is reflected in the generated Three-Address Code.

### Example 3: Code Optimization

Input:

```c
int result = 10 + 20;
int value = result + 0;
```

Constant folding can transform the first expression into:

```c
int result = 30;
int value = result + 0;
```

The unnecessary addition can subsequently be simplified by the applicable optimization rule.

### Example 4: FIRST and FOLLOW

Enter a grammar such as:

```text
E -> T E'
E' -> + T E' | ε
T -> id
```

Select the relevant grammar-analysis operation to calculate FIRST and FOLLOW sets and inspect the generated results.

### Example 5: Left Recursion Removal

Input:

```text
E -> E + T | T
```

The transformation produces the familiar predictive-parsing form:

```text
E -> T E'
E' -> + T E' | ε
```

These examples illustrate the intended workflow; actual output depends on the selected operation and the application's supported input syntax.

## 📚 Supported Language and Scope

The source-code analyzer works with a defined subset of C-like syntax, including:

- Basic types: `int`, `float`, `char`, `string`, and `bool`.
- Variables and assignment statements.
- Arithmetic expressions and parentheses.
- Supported control-flow constructs such as `if`, `else`, and `while`.
- Functions, parameters, arrays, and expressions supported by the implemented parser.
- Common operators, literals, and comments.

Grammar utilities support production rules using arrows such as `->`, `-->`, and `=>`, with supported alternatives separated by `|`.

**Important:** This is an educational compiler laboratory, not a complete standards-compliant C compiler. Some analysis modules use simplified rules, and supported syntax varies by operation. Optimization transformations are pattern-based and are not a substitute for a production compiler's full control-flow and data-flow analysis.

## 📸 Screenshots

Add screenshots of the actual running application to a `screenshots/` directory in your repository.

Suggested screenshots:

| Screenshot | What to show |
|---|---|
| Main Interface | Application window and operation sidebar |
| Lexical Analysis | Token classification output |
| Syntax Analysis | Syntax-checking results |
| Semantic Analysis | Symbol table and semantic errors |
| Intermediate Code | Generated Three-Address Code |
| Code Optimization | Before-and-after transformations |
| FIRST / FOLLOW | Calcul
