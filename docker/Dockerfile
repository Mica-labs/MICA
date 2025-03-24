FROM micalabs/micabase:v1

COPY /mica /mica
WORKDIR /mica
ENV PYTHONPATH=/

EXPOSE 5001
CMD ["python", "-u", "server.py"]