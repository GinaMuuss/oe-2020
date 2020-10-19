FROM ubuntu:latest
RUN apt-get update -y
RUN apt-get install -y python3-pip python3-dev build-essential

COPY ./requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip3 install -r requirements.txt

COPY ./templates /app/templates
COPY ./app.py /app/app.py
ENTRYPOINT ["python3"]
CMD ["app.py"]