FROM python:3.12-alpine

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py mestari.py agent_engine.py sandbox_state.py .

EXPOSE 8080

CMD ["python", "-u", "app.py"]
