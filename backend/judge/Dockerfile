FROM python:3.11-slim
COPY runner.py /opt/judge/runner.py
USER 65534:65534
WORKDIR /tmp
ENTRYPOINT ["timeout", "--signal=KILL", "5s", "python", "-I", "-B", "/opt/judge/runner.py"]
