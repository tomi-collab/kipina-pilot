FROM python:3.12-alpine

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py analyze.py image.py mock.py text_helper.py weather.py transit.py rate_limit.py .

EXPOSE 8080

CMD ["python", "-u", "app.py"]
