FROM python@sha256:44ff437bba879d4941b710a369a8f19266aea34b29002807f0c487fabc9eec9b
WORKDIR /artifact
COPY . .
RUN python -m pip install --require-hashes -r requirements-reproduction.lock
ENV PYTHONPATH=/artifact/src
CMD ["sh", "-c", "python -m unittest discover -s tests -q && python scripts/verify_evidence.py && python scripts/external_service_study.py --output /tmp/external_replay"]
