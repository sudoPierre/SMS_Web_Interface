FROM python:3.10-slim

WORKDIR /usr/src/app

COPY requirements.txt ./

RUN python3 -m pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "-u", "./main.py" ]