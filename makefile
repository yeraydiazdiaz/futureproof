.PHONY: tests tests-coverage

tests:
	pytest -m 'not slow' && pytest -m slow

tests-coverage:
	coverage run -m pytest && coverage report
