FROM python:3.10.7
USER root

WORKDIR /app
COPY . /app

RUN pip install --upgrade -r /app/requirements.txt

RUN apt-get update
RUN apt-get install -y ffmpeg

CMD ["python", "discordbot.py"]