
# ACUNAO AI

Check out the [ACUNAO AI website](https://luquelab.github.io/ACUNAO-AI) for more information about the project.

## Description

An AI assistant as a domain expert of the lab’s documents that has the ability to answer users’ queries accurately. It assists users with organizing their projects and acts as a 'second brain'.

Due to the rapid growth of AI, especially since the launch of ChatGPT, there has been a drastic increase in AI products and services. These products and services have mostly been developed to appeal to the general public. There is a lack of AI solution to support interdisciplinary research labs whose documents could accumulate so quickly, which leads to misplaced or forgotten information. The nature of these documents also poses as a problem since they are generally complex and confidential. ACUNAO AI aims to bridge this gap.

**Note: The following instructions is for Mac-OS. If you are a Windows user, please follow the `windows-os` branch**

## Table of Contents

* [MacOS App](#macos-app)
* [Download LLM](#download-llm)
* [Installation](#installation)
   * [Conda-environment](#conda-environment)
   * [MacOS no conda](#macos-no-conda)
* [Documentation](#documentation)
* [Project History](#project-history)
* [Folder's descriptions](#folders-descriptions)
* [Maintainers](#maintainers)
    * [Contributors](#contributors)
* [License](#license)  
* [Star History](#star-history)

## MacOS App
We have a downloadable MacOS App prototype ready to use. Please contact us at mte42@miami.edu for access to the app.

## Download LLM
Please follow the following instructions prior to installing the AI Assistant.  

1. Navigate to the following link https://huggingface.co/bartowski/Phi-3.5-mini-instruct-GGUF/resolve/main/Phi-3.5-mini-instruct-Q8_0.gguf?download=true.

## Installation   
Follow the proper instructions based on your package manager, environment management system, and operating system. If you use Conda as your environment management system,follow the instructions found in [Conda-environment](#conda-environment). If you use MacOS without Conda, follow the instructions found in [MacOS no conda](#macos-no-conda).  

To set up ACUNAO AI locally, follow these steps in your terminal or VS Code terminal:  

### Conda-environment  

1. **Clone the repository** or **Download the repository**  
```bash
git clone https://github.com/luquelab/ACUNAO-AI.git
```  
2. **Navigate to project directory**  
```bash
cd ACUNAO-AI
```  
  or 
```bash
cd ACUNAO-AI-main
```
  Note: if you are new to the terminal, PowerShell or CommandPrompt, run `ls` to see the current directory and `cd` to navigate to the ACUNAO-AI folder.  

3. **Add the LLM**  
Move the downloaded LLM to the `ACUNAO-AI/utils/data/` folder, replacing the existing pointer file: `Phi-3.5-mini-instruct-Q8_0.gguf`.  

4. **Install dependencies**  

```
conda env create --name venv --file=environment.yml
```
```
conda activate venv
```  
```
sh ./post_install.sh
```

5. **Run the application**  

Run the Streamlit prototype:  
```bash
python run.py
```
Note: During first run, you will be prompted to add your email for marketing subscription from Streamlit. You have the option to add your email and press enter, or hit the enter key to skip adding your email to the marketing subscription. 

### MacOS No Conda  

1. **Clone the repository** or **Download the repository**  
```bash
git clone https://github.com/luquelab/ACUNAO-AI.git
```

2. **Navigate to project directory**  
```bash
cd ACUNAO-AI
```  
  or 
```bash
cd ACUNAO-AI-main
```
  Note: if you are new to the terminal, PowerShell or CommandPrompt, run `ls` to see the current directory and `cd` to navigate to the ACUNAO-AI folder.  

3. **Add the LLM**  
Move the downloaded LLM to the `ACUNAO-AI/utils/data/` folder.  

4. **Create a virtual environment**  
  Note: In MacOS, make sure that Xcode is installed. To do this, run this command in your terminal:  
```
xcode-select –-install
```
```bash
python3 -m venv venv
```

5. **Activate the virtual environment**  

```
source venv/bin/activate
```  

6. **Install dependencies**  

This project requires Tesseract to be installed on your system. You can install Tesseract using Homebrew with the following command:
```bash
brew install tesseract
```
Then:
```bash
pip install -r requirements.txt
```  
And then:  
```
sh ./post_install.sh
```

7. **Run the application**  

Run the Streamlit prototype:  
```bash
python run.py
```
Note: During first run, you will be prompted to add your email for marketing subscription from Streamlit. You have the option to add your email and press enter, or hit the enter key to skip adding your email to the marketing subscription. 


## Project History

This is an evolving repository  

Started: 2024-06-03

End: Ongoing

## Folder's descriptions

* `/data`: Files used for testing purposes.
* `/hooks`: This folder contains the hooks for creating the executable.
* `/utils`: Project's source codes.

## Maintainers

[@LuqueLab](https://github.com/luquelab)
[@TjanMichela](https://github.com/tjanmichela)

### Contributors

This project exists thanks to all the people who contribute.  
[@LuqueLab](https://github.com/luquelab)
[@TjanMichela](https://github.com/tjanmichela)

## License

This project is licensed under MIT license.

## Star History

<a href="https://www.star-history.com/#luquelab/ACUNAO-AI&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=luquelab/ACUNAO-AI&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=luquelab/ACUNAO-AI&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=luquelab/ACUNAO-AI&type=Date" />
 </picture>
</a>

------
The syntax of markdown files (.md) is CommonMark unless specified otherwise (https://commonmark.org/help/)