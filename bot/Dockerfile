FROM python:3.7
WORKDIR /usr/src/bot/
COPY . .
RUN pip install -r requirements.txt
ENV PYTHONPATH /usr/src/
CMD ["python", "/usr/src/bot/main.py"]