FROM python:3.9
COPY requirements.txt /OS_check_list/requirements.txt
WORKDIR /OS_check_list
RUN pip install -r requirements.txt
COPY .  /OS_check_list
CMD ["python", "app.py"]