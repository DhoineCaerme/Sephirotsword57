@echo off
REM ─────────────────────────────────────────────────────────────────────────
REM Sephirotsword57 :: one-command runner for Windows
REM Usage:
REM   run.bat              -> launches the Streamlit UI
REM   run.bat demo         -> runs main.py --demo
REM   run.bat quick        -> runs the 4-sample quick demo
REM   run.bat validate     -> pre-flight setup validation
REM   run.bat test         -> runs the test suite
REM   run.bat eval         -> runs the full 100-sample evaluation
REM   run.bat eval-limit N -> runs the first N samples of the evaluation
REM   run.bat baselines    -> runs the 3 baselines comparison
REM ─────────────────────────────────────────────────────────────────────────

setlocal

REM Activate venv
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo [ERROR] venv not found. Run setup.bat first.
    exit /b 1
)

REM Dispatch on first argument
if "%~1"=="" goto :ui
if /I "%~1"=="ui" goto :ui
if /I "%~1"=="demo" goto :demo
if /I "%~1"=="quick" goto :quick
if /I "%~1"=="validate" goto :validate
if /I "%~1"=="test" goto :test
if /I "%~1"=="eval" goto :eval
if /I "%~1"=="eval-limit" goto :eval_limit
if /I "%~1"=="baselines" goto :baselines

echo Unknown command: %~1
echo.
echo Available commands:
echo   run.bat              ^- launch Streamlit UI
echo   run.bat demo         ^- run main.py --demo
echo   run.bat quick        ^- 4-sample quick demo (one per category)
echo   run.bat validate     ^- pre-flight setup check
echo   run.bat test         ^- run pytest test suite
echo   run.bat eval         ^- full 100-sample evaluation
echo   run.bat eval-limit N ^- first N samples
echo   run.bat baselines    ^- baseline comparison
exit /b 1

:ui
echo [SEPHIROT] launching web UI...
streamlit run ui\app.py
goto :end

:demo
echo [SEPHIROT] running demo...
python main.py --demo
goto :end

:quick
echo [SEPHIROT] running quick demo (4 samples)...
python scripts\quick_demo.py
goto :end

:validate
echo [SEPHIROT] validating setup...
python scripts\validate_setup.py
goto :end

:test
echo [SEPHIROT] running test suite...
python tests\test_metrics.py
python tests\test_baseline_regex.py
goto :end

:eval
echo [SEPHIROT] running full 100-sample evaluation...
python evaluation\runner.py
goto :end

:eval_limit
if "%~2"=="" (
    echo [ERROR] eval-limit requires a number, e.g. run.bat eval-limit 10
    exit /b 1
)
echo [SEPHIROT] running evaluation, first %~2 samples...
python evaluation\runner.py --limit %~2
goto :end

:baselines
echo [SEPHIROT] running baselines comparison...
python evaluation\runner.py --baselines
goto :end

:end
endlocal