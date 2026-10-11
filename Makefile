PY ?= python3

.PHONY: help test check lint-trailing clean

help:
	@echo "make test    跑 adtlib 自测(含 dtc 交叉验证)"
	@echo "make check   语法检查 + 自测"
	@echo "make clean   清掉缓存"

test:
	$(PY) tests/test_adtlib.py

check: test
	@$(PY) -m py_compile tools/*.py tests/*.py && echo "语法 OK"

# 顺手查一下尾随空格(这类小毛病最容易混进提交)
lint-trailing:
	@! grep -rn " $$" --include="*.py" --include="*.md" tools tests docs *.md \
	    || (echo "^^^ 上面有尾随空格"; exit 1)

clean:
	rm -rf tools/__pycache__ tests/__pycache__
