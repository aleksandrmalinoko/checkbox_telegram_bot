FROM python:3.9
COPY requirements.txt /OS_check_list/requirements.txt
WORKDIR /OS_check_list
RUN pip install -r requirements.txt
COPY config.ini  /OS_check_list/config.ini
COPY app.py  /OS_check_list/app.py
CMD ["python", "app.py"]