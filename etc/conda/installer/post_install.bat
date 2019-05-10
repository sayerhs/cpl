@echo off
REM Explicitly move noarch packages into `Lib/site-packages` as a workaround to
REM [this issue][i86] with lack of `constructor` support for `noarch` packages.
REM
REM [i86]: https://github.com/conda/constructor/issues/86#issuecomment-330863531
IF EXIST site-packages (
xcopy site-packages\* Lib\site-packages /e /y
rmdir /S/Q site-packages
)
