FROM python:3.7
COPY .  /OS_check_list
WORKDIR /OS_check_list
RUN pip install -r requirements.txt
EXPOSE  8000
CMD ["python", "main.py"]