serve:
	python -m http.server 8000

validate:
	python scripts/validate_graph.py

build:
	python scripts/build_graph.py

geocode:
	python scripts/geocode_places.py

apply-geocodes:
	python scripts/apply_geocoding_review.py
