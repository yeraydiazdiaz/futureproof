.PHONY: install-dev tests tests-coverage release-test release-pypi

install-dev:
	pip install -U pip setuptools wheel
	pip install -r requirements-dev.txt

tests:
	pytest -x -m 'not slow' && pytest -x -m slow

tests-coverage:
	coverage run -m pytest && coverage report

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
