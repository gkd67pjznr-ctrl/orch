# Python Hello World Program

## Overview

The "Hello World" program is traditionally the first program written when learning a new programming language. It demonstrates the basic syntax for displaying output to the user.

## The Code

```python
# This is a comment - it's ignored by the Python interpreter
print("Hello, World!")
```

## Explanation

### Line-by-Line Breakdown

#### Line 1: Comment
```python
# This is a comment - it's ignored by the Python interpreter
```
- Comments in Python start with the `#` symbol
- Everything after `#` on that line is ignored during execution
- Comments are used to document code and make it more readable

#### Line 2: Print Statement
```python
print("Hello, World!")
```
- `print()` is a built-in Python function that displays output
- The text `"Hello, World!"` is a string literal enclosed in double quotes
- When executed, this will display "Hello, World!" to the console

## How to Run

### Method 1: Save to a file
1. Save the code to a file named `hello.py`
2. Open a terminal/command prompt
3. Navigate to the file's directory
4. Run: `python hello.py`

### Method 2: Interactive Python
1. Open a Python interpreter by typing `python` in terminal
2. Type the print statement directly and press Enter

## Expected Output

```
Hello, World!
```

## Variations

### Using Single Quotes
```python
print('Hello, World!')
```

### Using Variables
```python
message = "Hello, World!"
print(message)
```

### Using f-strings (Python 3.6+)
```python
greeting = "Hello"
target = "World"
print(f"{greeting}, {target}!")
```

## Why "Hello World"?

The tradition of using "Hello, World!" as a first program dates back to the 1970s and was popularized by the book "The C Programming Language" by Brian Kernighan and Dennis Ritchie. It serves several purposes:

- **Simple syntax**: Demonstrates basic output without complex logic
- **Immediate feedback**: Shows that your development environment is working
- **Universal tradition**: Creates a shared experience among programmers
- **Foundation building**: Introduces core concepts like functions and strings