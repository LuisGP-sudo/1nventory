FROM python:3.12-slim AS build
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
COPY --from=build /install /usr/local
COPY app.py .
RUN useradd -r appuser && mkdir /data && chown appuser /data
USER appuser
EXPOSE 5001
CMD ["gunicorn", "-b", "0.0.0.0:5001", "app:app"]
