.PHONY: build drafts serve clean

build:
	python3 build.py

drafts:
	python3 build.py --drafts

serve: drafts
	python3 -m http.server --bind 127.0.0.1 --directory dist 8000

clean:
	rm -rf dist
