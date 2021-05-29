@echo OFF

rem Define here the path to your conda installation
set CONDAPATH=C:\Users\phili\miniconda3

rem Define here the name of the environment
set ENVNAME=esg_codebase

rem The following command activates the base environment.
if %ENVNAME%==base (set ENVPATH=%CONDAPATH%) else (set ENVPATH=%CONDAPATH%\envs\%ENVNAME%)

rem Activate the conda environment
call %CONDAPATH%\Scripts\activate.bat %ENVPATH%

rem Run a python script in that environment
streamlit run 0_ps_exploration.py


