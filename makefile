.PHONY: tests tests-coverage

tests:
	pytest -x -m 'not slow' && pytest -x -m slow

tests-coverage:
	coverage run -m pytest && coverage report
