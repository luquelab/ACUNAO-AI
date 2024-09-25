# Project Source Code

This folder contains the source code for the project.

## Table of Contents

- [Structure](#structure)
- [Installation](#installation)
- [Running the Code](#running-the-code)
- [Testing](#testing)
- [Contributing](#contributing)

## Structure

The `src` folder is organized as follows:

```
src/
│
├── app.py            # Main entry point of the application
├── __init__.py
├── embeddings.py
├── llm.py
├── loader.py
├── pdfparser.py
└── requirements.txt
```

## Installation

Before running the code, ensure that you have set up the project as described in the main [README](../README.md) file in the root directory. This includes creating a virtual environment and installing dependencies.

### Running the Code

To run the main application, navigate to the `src` folder and execute the following command:

```bash
streamlit run app.py
```