.PHONY: install-dev tests tests-coverage release-test release-pypi docs-server

install-dev:
	pip install -U pip setuptools wheel
	pip install -r requirements-dev.txt

tests:
	coverage run --parallel-mode -m pytest -x -m 'not slow' && \
	coverage run --parallel-mode -m pytest -x -m 'slow' && \
	EXECUTOR_TYPE=process coverage run --parallel-mode -m pytest -x -m 'not slow' && \
	EXECUTOR_TYPE=process coverage run --parallel-mode -m pytest -x -m 'slow' && \
	coverage combine && \
	coverage report

tests-process:
	EXECUTOR_TYPE=process pytest -x -m 'not slow' && \
	EXECUTOR_TYPE=process pytest -x -m 'slow'

package:
	rm -fr dist/*
	python setup.py sdist bdist_wheel

release-test: package
	@echo "Are you sure you want to release to test.pypi.org? [y/N]" && \
		read ans && \
		[ $${ans:-N} = y ] && \
		twine upload --repository-url https://test.pypi.org/legacy/ dist/*

release-pypi: package
	@echo "Are you sure you want to release to pypi.org? [y/N]" && \
		read ans && \
		[ $${ans:-N} = y ] && \
		twine upload dist/*

docs-server:
	sphinx-autobuild docs docs/_build/html
