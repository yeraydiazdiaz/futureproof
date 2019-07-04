.PHONY: tests tests-coverage

tests:
	pytest -m 'not slow' && pytest -m slow

tests-coverage:
	coverage run pytest && coverage report
