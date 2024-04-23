FROM python:3.9

ENV HOME /root
WORKDIR /root

COPY . .
RUN pip3 install -r requirements.txt

EXPOSE 8000

CMD python -u server.py


